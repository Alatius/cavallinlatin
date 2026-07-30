import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Virtuoso, type VirtuosoHandle } from 'react-virtuoso';

import type { Status } from '../api/types';
import { fold, useHeadwords, type FoldedEntry } from './HeadwordsContext';
import { plural } from './plural';
import StatusFilter from './StatusFilter';
import { useHorizontalResize } from './useHorizontalResize';

interface Props {
  basePath: string;
  showStatusFilter?: boolean;
}

// Each entry contributes one primary row and one alt row per secondary <orth>;
// all rows for an entry link to the same url_id. Alts are indented only in
// browse mode (in search mode they appear flush-left since their primary may
// not be shown next to them).
type Row =
  | { kind: 'primary'; entry: FoldedEntry }
  | { kind: 'alt'; entry: FoldedEntry; headword: string; index: number };

function rowKey(r: Row): string {
  return r.kind === 'primary' ? r.entry.url_id : `${r.entry.url_id}:${r.index}`;
}

export default function IndexPanel({ basePath, showStatusFilter = true }: Props) {
  const { urlId: currentUrlId } = useParams<{ urlId: string }>();
  const navigate = useNavigate();
  const { items: all, loaded, error } = useHeadwords();
  const { width, handleRef, onPointerDown } = useHorizontalResize({
    storageKey: 'index-panel-width',
    initial: 240,
    min: 150,
    max: 600,
    side: 'right',
  });

  const [q, setQ] = useState('');
  const [status, setStatus] = useState<Status | ''>('');
  const virtuosoRef = useRef<VirtuosoHandle>(null);

  const qFold = useMemo(() => fold(q.trim()), [q]);
  const hasTextQuery = qFold.length > 0;

  const filtered: Row[] = useMemo(() => {
    const rows: Row[] = [];
    for (const it of all) {
      if (status && it.status !== status) continue;

      if (!hasTextQuery) {
        rows.push({ kind: 'primary', entry: it });
        for (let i = 0; i < it.alt_headwords.length; i += 1) {
          rows.push({
            kind: 'alt',
            entry: it,
            headword: it.alt_headwords[i],
            index: i,
          });
        }
        continue;
      }

      const primaryMatch = it.fold.startsWith(qFold);
      const altMatchIdx: number[] = [];
      for (let i = 0; i < it.alt_folds.length; i += 1) {
        if (it.alt_folds[i].startsWith(qFold)) altMatchIdx.push(i);
      }
      if (!primaryMatch && altMatchIdx.length === 0) continue;

      if (primaryMatch) rows.push({ kind: 'primary', entry: it });
      for (const i of altMatchIdx) {
        rows.push({
          kind: 'alt',
          entry: it,
          headword: it.alt_headwords[i],
          index: i,
        });
      }
    }
    return rows;
  }, [all, qFold, hasTextQuery, status]);

  // Scroll current entry to the top whenever it or the filtered list changes.
  // 100 ms delay (vs requestAnimationFrame) handles the direct URL-load case:
  // on a fresh mount Virtuoso silently no-ops scrollIntoView until it has
  // measured at least its initial chunk of rows, which takes a few frames.
  useEffect(() => {
    if (!currentUrlId || filtered.length === 0) return;
    const idx = filtered.findIndex((r) => r.entry.url_id === currentUrlId);
    if (idx < 0) return;
    const t = setTimeout(() => {
      virtuosoRef.current?.scrollIntoView({ index: idx, align: 'start', behavior: 'auto' });
    }, 100);
    return () => clearTimeout(t);
  }, [currentUrlId, filtered]);

  function onPanelKeyDown(e: React.KeyboardEvent<HTMLElement>) {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    if (filtered.length === 0) return;
    // Navigate row-by-row; if multiple rows point at the current entry
    // (primary + alts), step to the next *entry* rather than repeating.
    const currentIdx = filtered.findIndex((r) => r.entry.url_id === currentUrlId);
    const step = e.key === 'ArrowDown' ? 1 : -1;
    let next: number;
    if (currentIdx < 0) {
      if (step !== 1) return;
      next = 0;
    } else {
      next = currentIdx + step;
      while (next >= 0 && next < filtered.length
             && filtered[next].entry.url_id === currentUrlId) {
        next += step;
      }
      if (next < 0 || next >= filtered.length) return;
    }
    e.preventDefault();
    const active = document.activeElement;
    if (!active || active.tagName !== 'INPUT') {
      e.currentTarget.focus();
    }
    navigate(`${basePath}/${filtered[next].entry.url_id}`);
  }

  return (
    <>
      <aside
        className="index-panel"
        style={{ width }}
        onKeyDown={onPanelKeyDown}
        tabIndex={-1}
      >
        <div className="index-panel__controls">
          <input
            type="search"
            className="index-panel__search"
            placeholder="Sök uppslagsord …"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {showStatusFilter && (
            <StatusFilter value={status} onChange={setStatus} />
          )}
        </div>
        <div className="index-panel__meta">
          {error
            ? `Kunde inte ladda registret: ${error}`
            : !loaded
            ? 'Laddar …'
            : (!hasTextQuery && !status)
              ? `${all.length} uppslagsord`
              : `${filtered.length} ${plural(filtered.length, 'träff', 'träffar')}`}
        </div>
        <div className="index-panel__list-wrap">
          <Virtuoso
            ref={virtuosoRef}
            data={filtered}
            computeItemKey={(_, r) => rowKey(r)}
            itemContent={(_, r) => {
              const { entry } = r;
              const display = r.kind === 'primary' ? entry.headword : r.headword;
              const cls =
                'index-panel__item' +
                (entry.url_id === currentUrlId ? ' index-panel__item--current' : '') +
                ` index-panel__item--${entry.status}` +
                ` index-panel__item--type-${entry.type}` +
                (r.kind === 'alt' ? ' index-panel__item--alt' : '') +
                (r.kind === 'alt' && !hasTextQuery ? ' index-panel__item--alt-indent' : '');
              // 💬 marker only on the primary row: alt rows route to the
              // same entry, so doubling the icon would just be noise.
              const showComments = r.kind === 'primary' && entry.comment_count > 0;
              return (
                <div className={cls}>
                  <Link to={`${basePath}/${entry.url_id}`} draggable={false}>
                    <span className="index-panel__label">{display}</span>
                    {showComments && (
                      <span
                        className="index-panel__comments"
                        title={`${entry.comment_count} ${plural(entry.comment_count, 'kommentar', 'kommentarer')}`}
                        aria-label={`${entry.comment_count} ${plural(entry.comment_count, 'kommentar', 'kommentarer')}`}
                      >
                        💬
                      </span>
                    )}
                  </Link>
                </div>
              );
            }}
          />
        </div>
      </aside>
      <div ref={handleRef} className="resize-handle" onPointerDown={onPointerDown} />
    </>
  );
}
