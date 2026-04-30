import { useEffect, useRef, useState } from 'react';

import type { Comment } from '../api/types';

interface Props {
  comments: Comment[];
  loading: boolean;
  error: string | null;
  onAdd(body: string): Promise<void>;
  onClose(): void;
}

function formatDate(unix: number): string {
  const d = new Date(unix * 1000);
  // Locale 'sv-SE' gives YYYY-MM-DD HH:MM, which matches the rest of the
  // Swedish UI without locale guesswork.
  return d.toLocaleString('sv-SE', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

export default function CommentsPanel({
  comments, loading, error, onAdd, onClose,
}: Props) {
  const [draft, setDraft] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Focus the textarea when the panel opens; useful especially when the
  // panel auto-opens from the activity page.
  useEffect(() => { taRef.current?.focus(); }, []);

  // Keep the most recent comment in view: jump to the bottom of the list
  // whenever its length changes (initial load, new addition). instant
  // behaviour avoids a smooth-scroll on first render that can land mid-list.
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [comments.length]);

  async function submit() {
    const trimmed = draft.trim();
    if (!trimmed || submitting) return;
    setSubmitting(true);
    try {
      await onAdd(trimmed);
      setDraft('');
    } catch {
      /* error surfaced via props.error */
    } finally {
      setSubmitting(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Cmd/Ctrl+Enter sends; plain Enter inserts a newline so multi-line
    // comments stay easy to write.
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="comments-panel">
      <div className="comments-panel__header">
        <span className="comments-panel__title">
          Kommentarer ({comments.length})
        </span>
        <button
          type="button"
          className="comments-panel__close"
          onClick={onClose}
          aria-label="Stäng kommentarspanelen"
        >
          ×
        </button>
      </div>
      {error && <div className="comments-panel__error">{error}</div>}
      <ul className="comments-panel__list" ref={listRef}>
        {loading && <li className="comments-panel__empty">Laddar …</li>}
        {!loading && comments.length === 0 && (
          <li className="comments-panel__empty">Inga kommentarer än.</li>
        )}
        {comments.map((c) => (
          <li key={c.id} className="comments-panel__item">
            <div className="comments-panel__meta">
              <span className="comments-panel__author">{c.display_name}</span>
              <span className="comments-panel__time">{formatDate(c.created_at)}</span>
            </div>
            <div className="comments-panel__body">{c.body}</div>
          </li>
        ))}
      </ul>
      <div className="comments-panel__compose">
        <textarea
          ref={taRef}
          className="comments-panel__textarea"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Skriv en kommentar … (Ctrl+Enter sparar)"
          rows={3}
          disabled={submitting}
        />
        <div className="comments-panel__compose-row">
          <button
            type="button"
            onClick={submit}
            disabled={submitting || !draft.trim()}
          >
            Lägg till
          </button>
        </div>
      </div>
    </div>
  );
}
