import type { ReactCodeMirrorRef } from '@uiw/react-codemirror';
import { useCallback, useEffect, useRef, useState } from 'react';

import { api, errorMessage } from '../api/client';
import type { Entry, EntrySplitResult } from '../api/types';
import { useHeadwords } from '../components/HeadwordsContext';
import { snapToSplit, type SnapResult } from './splitOps';

type Props = {
  editorRef: React.RefObject<ReactCodeMirrorRef | null>;
  entry: Entry | null;
  dirty: boolean;
  // The caller should reload the current entry — split shortens the
  // source's body server-side and the editor needs the new content.
  onSplitDone: () => void;
  // Same shape for join: the absorbed entry's content has been spliced
  // into the current one; reload to see it.
  onJoinDone: () => void;
};

type ActionError = { title: string; message: string };

function snapErrorMessage(snap: Exclude<SnapResult, { kind: 'ok' }>): string {
  switch (snap.kind) {
    case 'nested':
      return 'Markören står inuti ett element. Flytta den till en plats mellan elementen i posten och försök igen.';
    case 'no-boundary':
      return 'Hittade ingen giltig delningspunkt vid eller före markören. Placera markören mellan två element i posten.';
    case 'no-orth-in-second':
      return 'Den andra delen skulle sakna <orth> och därmed sakna uppslagsord. Flytta markören så att åtminstone ett <orth> hamnar efter delningspunkten.';
    case 'no-entry':
      return 'Hittade inte <entry>-elementet i editorn.';
  }
}

function Modal({
  open, onCancel, className, children,
}: {
  open: boolean;
  onCancel: () => void;
  className?: string;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      className={className}
      onCancel={(e) => { e.preventDefault(); onCancel(); }}
    >
      {children}
    </dialog>
  );
}

export default function EntryActionsMenu({
  editorRef, entry, dirty, onSplitDone, onJoinDone,
}: Props) {
  const { items: headwords, insertAfter, remove, patch } = useHeadwords();
  const [open, setOpen] = useState(false);
  const [splitState, setSplitState] = useState<
    | { phase: 'idle' }
    | { phase: 'confirm'; snap: Extract<SnapResult, { kind: 'ok' }>; error: string | null; busy: boolean }
  >({ phase: 'idle' });
  const [joinState, setJoinState] = useState<
    | { phase: 'idle' }
    | { phase: 'confirm'; nextUrlId: string; nextHeadword: string; error: string | null; busy: boolean }
  >({ phase: 'idle' });
  const [actionError, setActionError] = useState<ActionError | null>(null);

  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDocMouseDown = (e: MouseEvent) => {
      if (!wrapperRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDocMouseDown);
    return () => document.removeEventListener('mousedown', onDocMouseDown);
  }, [open]);

  const onSplitClick = useCallback(() => {
    setOpen(false);
    if (!entry) return;
    if (dirty) {
      setActionError({ title: 'Kan inte dela', message: 'Spara först.' });
      return;
    }
    const view = editorRef.current?.view;
    if (!view) return;
    const snap = snapToSplit(view.state, view.state.selection.main.head);
    if (snap.kind !== 'ok') {
      setActionError({ title: 'Kan inte dela', message: snapErrorMessage(snap) });
      return;
    }
    setSplitState({ phase: 'confirm', snap, error: null, busy: false });
  }, [entry, dirty, editorRef]);

  const onJoinClick = useCallback(() => {
    setOpen(false);
    if (!entry) return;
    if (dirty) {
      setActionError({ title: 'Kan inte slå ihop', message: 'Spara först.' });
      return;
    }
    if (!entry.next_url_id) {
      setActionError({
        title: 'Kan inte slå ihop',
        message: 'Det finns ingen efterföljande post att slå ihop med.',
      });
      return;
    }
    // Fall back to the raw url_id if the index hasn't fetched yet; better
    // than blocking the action over a cosmetic label.
    const nextHeadword = headwords.find((h) => h.url_id === entry.next_url_id)?.headword
      ?? entry.next_url_id;
    setJoinState({
      phase: 'confirm', nextUrlId: entry.next_url_id, nextHeadword,
      error: null, busy: false,
    });
  }, [entry, dirty, headwords]);

  const performSplit = useCallback(async () => {
    if (splitState.phase !== 'confirm' || !entry) return;
    setSplitState({ ...splitState, busy: true, error: null });
    try {
      const out = await api.post<EntrySplitResult>(
        `/entries/${entry.url_id}/split`,
        {
          offset: splitState.snap.offset,
          // The offset indexes the body this component previewed. Tell the
          // server which version that was, so a body that changed underneath
          // us is refused rather than cut at a position nobody saw.
          expected_updated_at: entry.updated_at,
        },
      );
      // Skip comment_count: the backend can't cheaply provide it and we
      // mustn't clobber the existing count with a stale 0.
      patch(out.source_entry.url_id, {
        headword: out.source_entry.headword,
        alt_headwords: out.source_entry.alt_headwords,
      });
      insertAfter(out.source_entry.url_id, out.new_entry);
      setSplitState({ phase: 'idle' });
      onSplitDone();
    } catch (err) {
      setSplitState({ ...splitState, busy: false, error: errorMessage(err) });
    }
  }, [splitState, entry, insertAfter, patch, onSplitDone]);

  const performJoin = useCallback(async () => {
    if (joinState.phase !== 'confirm' || !entry) return;
    setJoinState({ ...joinState, busy: true, error: null });
    try {
      const merged = await api.post<Entry>(
        `/entries/${entry.url_id}/join-next`,
        {
          expected_updated_at: entry.updated_at,
          // The server resolves "next" itself, so name the entry this dialog
          // said it would delete — otherwise an entry inserted in between by
          // another editor gets absorbed instead.
          expected_next_url_id: joinState.nextUrlId,
        },
      );
      remove(joinState.nextUrlId);
      patch(merged.url_id, {
        headword: merged.headword,
        alt_headwords: merged.alt_headwords,
        status: merged.status,
        type: merged.type,
      });
      setJoinState({ phase: 'idle' });
      onJoinDone();
    } catch (err) {
      setJoinState({ ...joinState, busy: false, error: errorMessage(err) });
    }
  }, [joinState, entry, remove, patch, onJoinDone]);

  const cancelSplit = () => setSplitState({ phase: 'idle' });
  const cancelJoin = () => setJoinState({ phase: 'idle' });
  const dismissError = () => setActionError(null);

  return (
    <div className="entry-actions-menu" ref={wrapperRef}>
      <button
        type="button"
        className={'editor-bottom__toggle'
          + (open ? ' editor-bottom__toggle--active' : '')}
        aria-haspopup="menu"
        aria-expanded={open}
        onMouseDown={(e) => { e.preventDefault(); setOpen((v) => !v); }}
      >
        Mer ▴
      </button>
      {open && (
        <ul className="dropdown-menu entry-actions-menu__menu" role="menu">
          <li role="none">
            <button
              type="button"
              role="menuitem"
              className="dropdown-menu__item"
              onClick={onSplitClick}
            >
              Dela vid markör
            </button>
          </li>
          <li role="none">
            <button
              type="button"
              role="menuitem"
              className="dropdown-menu__item"
              onClick={onJoinClick}
            >
              Slå ihop med nästa post
            </button>
          </li>
        </ul>
      )}

      <Modal
        open={splitState.phase === 'confirm'}
        onCancel={cancelSplit}
        className="entry-actions-modal"
      >
        {splitState.phase === 'confirm' && (
          <>
            <h2 className="entry-actions-modal__title">
              Dela posten "{entry?.headword}"?
            </h2>
            <div className="entry-actions-modal__columns">
              <div>
                <div className="entry-actions-modal__col-label">Stannar kvar</div>
                <pre className="entry-actions-modal__preview">
                  {splitState.snap.firstInner.trim() || '(tomt)'}
                </pre>
              </div>
              <div>
                <div className="entry-actions-modal__col-label">Blir ny post</div>
                <pre className="entry-actions-modal__preview">
                  {splitState.snap.secondInner.trim() || '(tomt)'}
                </pre>
              </div>
            </div>
            {splitState.error && (
              <div className="entry-actions-modal__error">{splitState.error}</div>
            )}
            <div className="entry-actions-modal__buttons">
              <button type="button" onClick={cancelSplit} disabled={splitState.busy}>
                Avbryt
              </button>
              <button
                type="button"
                onClick={performSplit}
                disabled={splitState.busy}
                className="entry-actions-modal__primary"
                autoFocus
              >
                {splitState.busy ? 'Delar …' : 'Dela'}
              </button>
            </div>
          </>
        )}
      </Modal>

      <Modal
        open={joinState.phase === 'confirm'}
        onCancel={cancelJoin}
        className="entry-actions-modal"
      >
        {joinState.phase === 'confirm' && (
          <>
            <h2 className="entry-actions-modal__title">
              Slå ihop "{entry?.headword}" med "{joinState.nextHeadword}"?
            </h2>
            <p className="entry-actions-modal__hint">
              Innehållet i "{joinState.nextHeadword}" läggs sist i denna post,
              och "{joinState.nextHeadword}" raderas. Korsreferenser med
              {' '}<code>target="{joinState.nextUrlId}"</code> kommer att brytas.
              Kommentarer följer med hit, och den raderade postens text sparas
              i historiken så att sammanslagningen går att ångra.
            </p>
            {joinState.error && (
              <div className="entry-actions-modal__error">{joinState.error}</div>
            )}
            <div className="entry-actions-modal__buttons">
              <button type="button" onClick={cancelJoin} disabled={joinState.busy}>
                Avbryt
              </button>
              <button
                type="button"
                onClick={performJoin}
                disabled={joinState.busy}
                className="entry-actions-modal__primary"
                autoFocus
              >
                {joinState.busy ? 'Slår ihop …' : 'Slå ihop'}
              </button>
            </div>
          </>
        )}
      </Modal>

      <Modal
        open={!!actionError}
        onCancel={dismissError}
        className="entry-actions-modal entry-actions-modal--narrow"
      >
        {actionError && (
          <>
            <h2 className="entry-actions-modal__title">{actionError.title}</h2>
            <p className="entry-actions-modal__hint">{actionError.message}</p>
            <div className="entry-actions-modal__buttons">
              <button
                type="button"
                onClick={dismissError}
                className="entry-actions-modal__primary"
                autoFocus
              >
                Stäng
              </button>
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}
