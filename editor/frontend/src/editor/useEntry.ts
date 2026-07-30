import { useCallback, useEffect, useRef, useState } from 'react';

import { api, ApiError, errorMessage } from '../api/client';
import type { Comment, Entry, LockInfo, Status } from '../api/types';
import { useAuth } from '../auth/AuthContext';

export interface UseEntryResult {
  entry: Entry | null;
  error: string | null;
  loading: boolean;
  dirty: boolean;
  saving: boolean;
  xml: string;
  status: Status;
  comments: Comment[];
  loadingComments: boolean;
  commentError: string | null;
  setXml(next: string): void;
  save(): Promise<void>;
  saveWithStatus(next: Status): Promise<void>;
  addComment(body: string): Promise<void>;
  reload(): Promise<void>;
  acquireLock(): Promise<void>;
}

export function useEntry(urlId: string): UseEntryResult {
  const { user } = useAuth();
  const [entry, setEntry] = useState<Entry | null>(null);
  const [xml, setXml] = useState('');
  const [status, setStatus] = useState<Status>('untouched');
  const [baseXml, setBaseXml] = useState('');
  const [baseStatus, setBaseStatus] = useState<Status>('untouched');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loadingComments, setLoadingComments] = useState(false);
  const [commentError, setCommentError] = useState<string | null>(null);

  // Does the loaded buffer actually belong to the entry in the URL? On A→B
  // navigation the component stays mounted and `entry` keeps holding A until
  // B's fetch resolves — deliberately, so EntryShell (and the column image's
  // scroll position) survive the transition. But nothing may *act* on the
  // buffer while it belongs to a different entry than the URL addresses:
  // that turned a failed fetch into "edit A, save it over B", and made
  // navigating away from a dirty entry take out a lock on the destination.
  const ready = entry !== null && entry.url_id === urlId;

  // Deliberately false while stale, which gates the save button, the
  // leave-page prompt and the acquire-lock-on-first-edit effect in one place.
  const dirty = ready && (xml !== baseXml || status !== baseStatus);

  // Read inside async callbacks to detect navigation that happened while a
  // request was in flight.
  const urlIdRef = useRef(urlId);
  useEffect(() => { urlIdRef.current = urlId; }, [urlId]);

  const apply = useCallback((e: Entry) => {
    setEntry(e);
    setXml(e.xml_body);
    setStatus(e.status);
    setBaseXml(e.xml_body);
    setBaseStatus(e.status);
  }, []);

  // Initial / urlId-change fetch. The active flag guards against the race
  // where fast A→B→A navigation lets an older response land on top of a
  // newer one (each effect run owns its own `active`, so only the latest
  // run's response is applied).
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    api.get<Entry>(`/entries/${urlId}`)
      .then((e) => { if (active) apply(e); })
      .catch((err) => {
        if (!active) return;
        // Drop the previous entry. Holding on to it would leave the editor
        // rendering A's XML, breadcrumb, history link and column image under
        // B's URL, with only a one-line error to say otherwise. Only `entry`
        // is cleared: it alone decides what renders, and touching `xml` here
        // would trip the clear-error-on-edit effect below and wipe the error
        // we're setting.
        setEntry(null);
        setError(errorMessage(err));
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [urlId, apply]);

  // User-initiated refetch (e.g., after a 409 from acquireLock). Not racing
  // with navigation, so the sequential pattern is fine.
  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const e = await api.get<Entry>(`/entries/${urlId}`);
      apply(e);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [urlId, apply]);

  // Clear stale error as soon as the user edits: a malformed-XML error from
  // a previous autosave is meaningless after the next keystroke.
  useEffect(() => { setError(null); }, [xml, status]);

  // Keepalive only when WE hold the lock; otherwise there's nothing to refresh
  // (and the backend would 409).
  const ownsLock = entry?.lock?.user_id === user?.id && !!user;
  useEffect(() => {
    if (!ownsLock) return;
    const iv = setInterval(() => {
      api.put(`/entries/${urlId}/lock`, {}).catch(() => {});
    }, 10 * 60 * 1000);
    return () => clearInterval(iv);
  }, [ownsLock, urlId]);

  // Release the lock on navigate-away when it's ours, so other editors don't
  // see a stale "X redigerar" for 15 min after we move on.
  //
  // This now fires for a dirty entry too. `dirty` is gated on `ready`, and on
  // navigation the render for the new urlId sees the old `entry`, so dirty is
  // already false by the time the cleanup runs. That's the right outcome: the
  // buffer is replaced as soon as the new entry's fetch resolves, so the
  // draft the retained lock was supposedly protecting no longer exists —
  // keeping it just blocked other editors for 15 minutes.
  const ownsLockRef = useRef(false);
  const dirtyRef = useRef(false);
  ownsLockRef.current = ownsLock;
  dirtyRef.current = dirty;
  useEffect(() => {
    const id = urlId;
    return () => {
      if (ownsLockRef.current && !dirtyRef.current) {
        api.del(`/entries/${id}/lock`).catch(() => {});
      }
    };
  }, [urlId]);

  const performSave = useCallback(async (nextStatus: Status) => {
    // Never PUT a buffer that belongs to a different entry than the URL
    // addresses. The expected_updated_at failsafe cannot catch that case:
    // import stamped every entry with the same updated_at, so the check
    // passes between any two never-yet-edited entries.
    if (!ready) return;
    const sentUrlId = urlId;
    const sent = xml;
    setSaving(true);
    setError(null);
    try {
      const e = await api.put<Entry>(`/entries/${sentUrlId}`, {
        xml_body: sent,
        status: nextStatus,
        // Optimistic concurrency: server 409s if the row's updated_at has
        // moved on, so a stale draft can't silently overwrite a newer save.
        expected_updated_at: entry?.updated_at ?? null,
      });
      // Navigated away mid-save: the response describes the entry we left,
      // so applying it here would drop it into the new entry's editor.
      if (urlIdRef.current !== sentUrlId) return;
      setEntry(e);
      setStatus(e.status);
      setBaseXml(e.xml_body);
      setBaseStatus(e.status);
      // Keep anything typed while the request was in flight. CodeMirror is
      // controlled, so overwriting `xml` unconditionally reverted those
      // keystrokes the moment the user paused — and because baseXml was set
      // to the same string, the indicator claimed "Sparat" while doing it.
      setXml((cur) => (cur === sent ? e.xml_body : cur));
    } catch (err) {
      if (urlIdRef.current !== sentUrlId) return;
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }, [ready, urlId, xml, entry?.updated_at]);

  const save = useCallback(() => performSave(status), [performSave, status]);

  // saveWithStatus drives the split-save menu items. We don't pre-set the
  // local status: performSave applies it from the response on success, and
  // on failure the badge must continue to reflect the entry's actual saved
  // state, not the attempted target.
  const saveWithStatus = useCallback(
    (next: Status) => performSave(next),
    [performSave],
  );

  // Comments: fetch on entry change. Reset state in the same effect so a
  // stale list from the previous entry never flashes through.
  useEffect(() => {
    let active = true;
    setComments([]);
    setCommentError(null);
    setLoadingComments(true);
    api.get<Comment[]>(`/entries/${urlId}/comments`)
      .then((cs) => { if (active) setComments(cs); })
      .catch((err) => {
        if (active) setCommentError(errorMessage(err));
      })
      .finally(() => { if (active) setLoadingComments(false); });
    return () => { active = false; };
  }, [urlId]);

  const addComment = useCallback(async (body: string) => {
    const trimmed = body.trim();
    if (!trimmed) return;
    const sentUrlId = urlId;
    setCommentError(null);
    try {
      const c = await api.post<Comment>(`/entries/${sentUrlId}/comments`, { body: trimmed });
      // Comments are listed oldest → newest; the new one goes at the end.
      // Skip if we've navigated: the list on screen is another entry's now.
      if (urlIdRef.current !== sentUrlId) return;
      setComments((prev) => [...prev, c]);
    } catch (err) {
      setCommentError(errorMessage(err));
      throw err;
    }
  }, [urlId]);

  const acquireLock = useCallback(async () => {
    if (!ready) return;
    const sentUrlId = urlId;
    try {
      const lock = await api.post<LockInfo>(`/entries/${sentUrlId}/lock`);
      // Optimistic local update — don't reload() because that would clobber
      // the user's uncommitted XML edits.
      if (urlIdRef.current !== sentUrlId) return;
      setEntry((prev) => prev ? { ...prev, lock } : prev);
    } catch (err) {
      // 409 means someone else holds it, and the response says who. Adopt
      // that directly: reload() would refetch the body and wipe the very
      // edits this lock was being taken out to protect.
      if (err instanceof ApiError && err.status === 409
          && urlIdRef.current === sentUrlId) {
        const held = (err.detail as { detail?: LockInfo } | undefined)?.detail;
        if (held && typeof held.user_id === 'number') {
          setEntry((prev) => prev ? { ...prev, lock: held } : prev);
        }
      }
      throw err;
    }
  }, [ready, urlId]);

  return {
    entry, error, loading, dirty, saving, xml, status,
    comments, loadingComments, commentError,
    setXml, save, saveWithStatus, addComment,
    reload, acquireLock,
  };
}
