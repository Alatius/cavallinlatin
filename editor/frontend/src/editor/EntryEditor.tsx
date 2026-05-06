import CodeMirror, { type ReactCodeMirrorRef } from '@uiw/react-codemirror';
import { xml as xmlLang } from '@codemirror/lang-xml';
import { EditorView } from '@codemirror/view';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { unstable_usePrompt as usePrompt, useLocation, useNavigate, useParams } from 'react-router-dom';

import { STATUS_LABEL_SV } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import Breadcrumb from '../components/Breadcrumb';
import type { ColumnHighlight } from '../components/ColumnImagePanel';
import { readEntryNavState } from '../components/entryNavState';
import EntryHtml from '../components/EntryHtml';
import EntryShell, { type MobileView } from '../components/EntryShell';
import { useDebounce } from '../components/useDebounce';
import { useHeadwords } from '../components/HeadwordsContext';
import { useHorizontalResize } from '../components/useHorizontalResize';
import CommentsPanel from './CommentsPanel';
import LockIndicator from './LockIndicator';
import SaveButton from './SaveButton';
import { closeTagOnSlash } from './closeTagOnSlash';
import EditorBottom from './EditorBottom';
import { TEI_ATTRS, TEI_ELEMENTS } from './teiSchema';
import { useEntry } from './useEntry';

const VIEW_TOGGLE: ReadonlyArray<{
  v: MobileView; icon: string; label: string; iconClass?: string;
}> = [
  { v: 'xml',      icon: '</>', label: 'XML', iconClass: 'entry-editor__view-icon--code' },
  { v: 'preview',  icon: '👁',  label: 'Förhandsvy' },
  { v: 'image',    icon: '🖼',  label: 'Bild' },
  { v: 'comments', icon: '💬',  label: 'Kommentarer' },
];

export default function EntryEditor() {
  const { urlId = '' } = useParams<{ urlId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { targetY, clickY, targetColumn, openComments } = readEntryNavState(location.state);
  const ent = useEntry(urlId);
  const { patch: patchHeadword } = useHeadwords();
  const [highlight, setHighlight] = useState<ColumnHighlight | null>(null);
  const [commentsOpen, setCommentsOpen] = useState(false);
  // Phone-only pane selector (≤720px). At wider widths the CSS shows all
  // three panes side-by-side and ignores this. Defaults to XML each entry
  // load — predictable and matches how a desktop user lands.
  const [mobileView, setMobileView] = useState<MobileView>('xml');
  useEffect(() => { setMobileView('xml'); }, [urlId]);

  // Phone: picking the comments tab opens the panel (and any other view
  // closes it). Desktop never calls this — the toolbar's own toggle owns
  // commentsOpen there.
  function pickMobileView(v: MobileView) {
    setMobileView(v);
    setCommentsOpen(v === 'comments');
  }

  // Auto-open the comments panel when navigated to from the activity page.
  // Reset on entry change so a stale openComments from a previous nav
  // doesn't reopen the panel for a different entry.
  useEffect(() => {
    setCommentsOpen(!!openComments);
  }, [urlId, openComments]);
  // 100 ms debounce keeps the preview render off the critical path of
  // typing. Reset key = url_id so navigation flushes the new entry's xml
  // through immediately rather than rendering the previous entry for 100 ms.
  const previewXml = useDebounce(ent.xml, 100, ent.entry?.url_id);

  // Propagate saved scalars to the shared index so the sidebar updates
  // without a full reload. Deps are the scalars themselves (not the entry
  // object, which reshapes every render). alt_headwords is an array, so
  // compare via stringify to keep the effect stable.
  const entryUrlId = ent.entry?.url_id;
  const entryStatus = ent.entry?.status;
  const entryHeadword = ent.entry?.headword;
  const entryType = ent.entry?.type;
  const entryAltJson = JSON.stringify(ent.entry?.alt_headwords ?? []);
  useEffect(() => {
    if (!entryUrlId || entryStatus === undefined || entryHeadword === undefined || entryType === undefined) return;
    patchHeadword(entryUrlId, {
      status: entryStatus,
      headword: entryHeadword,
      type: entryType,
      alt_headwords: JSON.parse(entryAltJson),
    });
  }, [entryUrlId, entryStatus, entryHeadword, entryType, entryAltJson, patchHeadword]);

  // Push the comment count into the shared index so the 💬 marker in the
  // sidebar appears immediately after adding a comment, without refetching
  // the whole headwords list. Gated on loadingComments so we don't briefly
  // patch in `0` while the initial fetch is in-flight.
  const commentCount = ent.comments.length;
  const loadingComments = ent.loadingComments;
  useEffect(() => {
    if (!entryUrlId || loadingComments) return;
    patchHeadword(entryUrlId, { comment_count: commentCount });
  }, [entryUrlId, commentCount, loadingComments, patchHeadword]);

  // Read the EditorView via the @uiw/react-codemirror imperative handle.
  // It goes back to undefined when CodeMirror unmounts, so we never end up
  // dispatching on a stale (destroyed) view across an entry transition. On a
  // fresh mount there's a brief window where cmRef.current.view is still
  // undefined (useImperativeHandle's [view] dep hasn't propagated yet) — for
  // that case we buffer the click and replay from onCreateEditor.
  const cmRef = useRef<ReactCodeMirrorRef>(null);
  const pendingClickRef = useRef<{ offset: number; viewportY: number; focus: boolean } | null>(null);
  // autoCloseTags: false — we mark up *existing* text, so an inserted
  // `</tag>` after the cursor lands before the content the user wants to
  // wrap. The `</`-completion (a separate code path) stays on.
  const xmlExt = useMemo(() => [
    xmlLang({
      autoCloseTags: false,
      elements: TEI_ELEMENTS,
      attributes: TEI_ATTRS,
    }),
    closeTagOnSlash,
    EditorView.lineWrapping,
  ], []);

  const applyXmlClick = useCallback((view: EditorView, offset: number, viewportY: number, focus: boolean) => {
    const pos = Math.max(0, Math.min(offset, view.state.doc.length));
    // Use CodeMirror's own scrollIntoView effect rather than reading
    // lineBlockAt + setting scrollTop manually: on a freshly-mounted view,
    // lineBlockAt returns an *estimate* for unmeasured lines (off by the
    // average-vs-actual line height), which is why a first click could land
    // close-but-wrong while a second one was perfect. The effect measures
    // the target line as part of the transaction so the math is exact.
    const cmRect = view.scrollDOM.getBoundingClientRect();
    const yMargin = Math.max(0, viewportY - cmRect.top);
    view.dispatch({
      selection: { anchor: pos },
      effects: EditorView.scrollIntoView(pos, { y: 'start', yMargin }),
    });
    if (focus) view.contentDOM.focus({ preventScroll: true });
  }, []);

  const handleXmlClick = useCallback((offset: number, viewportY: number, focus: boolean) => {
    const view = cmRef.current?.view;
    if (view) applyXmlClick(view, offset, viewportY, focus);
    else pendingClickRef.current = { offset, viewportY, focus };
  }, [applyXmlClick]);

  const onEditorReady = useCallback((view: EditorView) => {
    const pending = pendingClickRef.current;
    if (pending) {
      pendingClickRef.current = null;
      applyXmlClick(view, pending.offset, pending.viewportY, pending.focus);
    }
  }, [applyXmlClick]);

  // Jump CodeMirror to the offending position on a "Malformed XML: …, line N,
  // column C" error from the backend (lxml uses 1-indexed line and column).
  useEffect(() => {
    if (!ent.error) return;
    const m = ent.error.match(/line (\d+), column (\d+)/);
    const view = cmRef.current?.view;
    if (!m || !view) return;
    const line = Number(m[1]);
    const col = Number(m[2]);
    if (line < 1 || line > view.state.doc.lines) return;
    const lineObj = view.state.doc.line(line);
    const pos = Math.min(
      lineObj.from + Math.max(0, col - 1),
      lineObj.to,
    );
    view.dispatch({
      selection: { anchor: pos },
      scrollIntoView: true,
    });
    view.focus();
  }, [ent.error]);

  const xmlPane = useHorizontalResize({
    storageKey: 'xml-pane-width', initial: 500, min: 200, side: 'right',
  });

  // Acquire the soft lock on FIRST edit (not on mere view) so that simply
  // clicking through entries in the index doesn't trip "Ditt lås" for everyone.
  const lockedForRef = useRef<string | null>(null);
  useEffect(() => { lockedForRef.current = null; }, [urlId]);
  useEffect(() => {
    if (!ent.dirty || !ent.entry) return;
    if (lockedForRef.current === ent.entry.url_id) return;
    if (ent.entry.lock && ent.entry.lock.user_id !== user?.id) return;
    lockedForRef.current = ent.entry.url_id;
    ent.acquireLock().catch(() => {});
  }, [ent.dirty, ent.entry, user?.id, ent.acquireLock]);

  // Tab close / external nav: browser shows its generic confirm dialog.
  useEffect(() => {
    if (!ent.dirty) return;
    const h = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener('beforeunload', h);
    return () => window.removeEventListener('beforeunload', h);
  }, [ent.dirty]);

  // SPA nav (clicking another headword, header links, browser back/forward).
  usePrompt({
    when: ent.dirty,
    message: 'Du har osparade ändringar. Vill du lämna sidan ändå?',
  });

  // Keyboard shortcuts: read the latest useEntry result via ref so the
  // listener registers once rather than re-attaching every render.
  const entRef = useRef(ent);
  entRef.current = ent;
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key === 's') {
        e.preventDefault();
        if (entRef.current.dirty && !entRef.current.saving) {
          entRef.current.save().catch(() => {});
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Only bail out on the very first load, before there is any entry to render
  // a shell around. Subsequent reloads keep EntryShell mounted so that
  // ColumnImagePanel retains its scroll position when we navigate to an
  // entry whose column differs from the one the user is currently viewing.
  if (!ent.entry) {
    return <div className="loading">Laddar {urlId} …</div>;
  }

  const commentsLabel = ent.comments.length > 0
    ? `Kommentarer (${ent.comments.length})`
    : 'Kommentarer';

  const saveStatus: 'saving' | 'dirty' | 'clean' =
    ent.saving ? 'saving' : ent.dirty ? 'dirty' : 'clean';
  const saveStatusLabel = {
    saving: 'Sparar …', dirty: 'Osparade ändringar', clean: 'Sparat',
  }[saveStatus];

  const toolbar = (
    <>
      <Breadcrumb
        head={ent.entry.root_headword}
        current={ent.entry.headword}
        headTo={ent.entry.root_url_id ? `/editor/entry/${ent.entry.root_url_id}` : null}
        currentTo={`/editor/entry/${ent.entry.url_id}`}
      />
      <span
        className={`status-badge status-badge--${ent.status}`}
        title="Aktuell status"
      >
        {STATUS_LABEL_SV[ent.status]}
      </span>
      <div
        className="entry-editor__view-toggle"
        role="radiogroup"
        aria-label="Visa"
      >
        {VIEW_TOGGLE.map(({ v, icon, label, iconClass }) => (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={mobileView === v}
            aria-label={label}
            title={label}
            className={
              'entry-editor__view-toggle-btn'
              + (mobileView === v ? ' entry-editor__view-toggle-btn--active' : '')
            }
            onClick={() => pickMobileView(v)}
          >
            <span className={iconClass} aria-hidden="true">{icon}</span>
          </button>
        ))}
      </div>
      <div className="entry-editor__save">
        <button
          type="button"
          className={
            'entry-editor__comments-toggle'
            + (commentsOpen ? ' entry-editor__comments-toggle--open' : '')
            + (ent.comments.length > 0 ? ' entry-editor__comments-toggle--has' : '')
          }
          onClick={() => setCommentsOpen((v) => !v)}
          aria-expanded={commentsOpen}
          aria-label={commentsLabel}
        >
          <span className="hide-on-mobile">{commentsLabel}</span>
          <span className="show-on-mobile" aria-hidden="true">💬</span>
        </button>
        <span
          className={
            'entry-editor__save-dot'
            + (saveStatus !== 'clean' ? ` entry-editor__save-dot--${saveStatus}` : '')
          }
          aria-hidden="true"
          title={saveStatusLabel}
        />
        <SaveButton
          dirty={ent.dirty}
          saving={ent.saving}
          currentStatus={ent.status}
          onSave={() => ent.save()}
          onSaveWithStatus={(s) => ent.saveWithStatus(s)}
        />
      </div>
    </>
  );

  const panes = (
    <div className="entry-editor__panes">
      <div className="entry-editor__code" style={{ width: xmlPane.width }}>
        <CodeMirror
          ref={cmRef}
          value={ent.xml}
          extensions={xmlExt}
          onChange={ent.setXml}
          onCreateEditor={onEditorReady}
          basicSetup={{ lineNumbers: true, foldGutter: true, closeBrackets: false }}
          height="100%"
        />
        <EditorBottom editorRef={cmRef} />
      </div>
      <div
        ref={xmlPane.handleRef}
        className="resize-handle"
        onPointerDown={xmlPane.onPointerDown}
      />
      <div className="entry-editor__preview">
        <EntryHtml
          // Debounce so the regex pass + innerHTML rebuild doesn't run on
          // every keystroke. Flush immediately on entry change so the
          // auto-highlight effect below sees the new entry's DOM, not
          // yesterday's preview lingering for 100 ms.
          xml={previewXml}
          initialColumn={ent.entry.starting_column}
          onHighlight={setHighlight}
          // Only auto-highlight once the entry actually matches the URL.
          // Otherwise we'd fire against the previous entry's DOM with the
          // new click's targetY, picking a wrong element and dispatching
          // its (irrelevant) offset onto the soon-to-be-destroyed view.
          autoHighlightKey={ent.entry.url_id === urlId ? location.key : undefined}
          autoHighlightY={targetY}
          autoHighlightColumn={targetColumn}
          autoHighlightViewportY={clickY}
          onXmlClick={handleXmlClick}
        />
      </div>
    </div>
  );

  return (
    <EntryShell
      toolbar={toolbar}
      initialColumn={ent.entry.starting_column}
      highlight={highlight}
      mobileView={mobileView}
      onNavigate={(id, col, y, cy) => navigate(`/editor/entry/${id}`, { state: { targetColumn: col, targetY: y, clickY: cy } })}
    >
      <LockIndicator
        lock={ent.entry.lock}
        selfUserId={user?.id ?? null}
      />
      {commentsOpen && (
        <CommentsPanel
          comments={ent.comments}
          loading={ent.loadingComments}
          error={ent.commentError}
          onAdd={ent.addComment}
          onClose={() => {
            setCommentsOpen(false);
            if (mobileView === 'comments') setMobileView('xml');
          }}
        />
      )}
      {ent.error && <div className="entry-editor__error">{ent.error}</div>}
      {ent.loading ? <div className="loading">Laddar {urlId} …</div> : panes}
    </EntryShell>
  );
}
