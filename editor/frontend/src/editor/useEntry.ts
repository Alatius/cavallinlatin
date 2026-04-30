import { useCallback, useEffect, useRef, useState } from 'react';

import { api, ApiError } from '../api/client';
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

  const dirty = xml !== baseXml || status !== baseStatus;

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
        if (active) setError(err instanceof ApiError ? err.message : String(err));
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
      setError(err instanceof ApiError ? err.message : String(err));
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

  // Release the lock on navigate-away when it's ours and the entry is clean,
  // so other editors don't see a stale "X redigerar" for 15 min after we move
  // on. Dirty entries keep the lock — the user still has an unsaved draft.
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
    setSaving(true);
    setError(null);
    try {
      const e = await api.put<Entry>(`/entries/${urlId}`, {
        xml_body: xml,
        status: nextStatus,
        // Optimistic concurrency: server 409s if the row's updated_at has
        // moved on, so a stale draft can't silently overwrite a newer save.
        expected_updated_at: entry?.updated_at ?? null,
      });
      setEntry(e);
      setXml(e.xml_body);
      setStatus(e.status);
      setBaseXml(e.xml_body);
      setBaseStatus(e.status);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }, [urlId, xml, entry?.updated_at]);

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
        if (active) setCommentError(err instanceof ApiError ? err.message : String(err));
      })
      .finally(() => { if (active) setLoadingComments(false); });
    return () => { active = false; };
  }, [urlId]);

  const addComment = useCallback(async (body: string) => {
    const trimmed = body.trim();
    if (!trimmed) return;
    setCommentError(null);
    try {
      const c = await api.post<Comment>(`/entries/${urlId}/comments`, { body: trimmed });
      // Comments are listed oldest → newest; the new one goes at the end.
      setComments((prev) => [...prev, c]);
    } catch (err) {
      setCommentError(err instanceof ApiError ? err.message : String(err));
      throw err;
    }
  }, [urlId]);

  const acquireLock = useCallback(async () => {
    try {
      const lock = await api.post<LockInfo>(`/entries/${urlId}/lock`);
      // Optimistic local update — don't reload() because that would clobber
      // the user's uncommitted XML edits.
      setEntry((prev) => prev ? { ...prev, lock } : prev);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) await reload();
      throw err;
    }
  }, [urlId, reload]);

  return {
    entry, error, loading, dirty, saving, xml, status,
    comments, loadingComments, commentError,
    setXml, save, saveWithStatus, addComment,
    reload, acquireLock,
  };
}
