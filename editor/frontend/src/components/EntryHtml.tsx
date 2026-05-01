import { useEffect, useMemo, useRef } from 'react';

import { entryXmlToHtml } from '../render';
import type { ColumnHighlight } from './ColumnImagePanel';

interface Props {
  xml: string;
  initialColumn: string | null;
  onHighlight: (h: ColumnHighlight) => void;
  /** When this key changes, auto-highlight as if the user had clicked the
      appropriate target: the first <orth data-y> by default, or the sense/
      orth whose data-y is the largest value ≤ autoHighlightY when supplied. */
  autoHighlightKey?: string;
  /** If set (0–100), picks the sense/orth closest above this y on auto-highlight. */
  autoHighlightY?: number;
  /** When set, restricts auto-highlight candidates to this column. Required
      when an entry spans multiple columns: data-y is per-column, so without
      it the picker can land on a sense in a different column whose y happens
      to be ≤ autoHighlightY. */
  autoHighlightColumn?: string;
  /** Optional viewport Y in pixels (e.g. the user's clientY when they clicked
      the column image). When set, the auto-highlight scrolls the preview so
      the picked element's top lands at this viewport Y, aligning with where
      the click happened across panes. Falls back to scrollIntoView(nearest)
      when absent. */
  autoHighlightViewportY?: number;
  /** 'editor' (default) keeps the color-coded tag styling; 'public' switches
      to clean reading typography without per-tag colors. */
  variant?: 'editor' | 'public';
  /** Called with the XML source offset of the nearest [data-xml-start]
      ancestor and the viewport Y of that element's top edge, so the editor
      can scroll the matching XML line to the same vertical position.
      `focus` indicates whether the editor should grab focus — true on a
      direct click in the preview (the user wants to edit), false on
      auto-highlight (e.g. navigation, where stealing focus would break
      keyboard navigation in the index). */
  onXmlClick?: (offset: number, viewportY: number, focus: boolean) => void;
}

export default function EntryHtml({ xml, initialColumn, onHighlight, autoHighlightKey, autoHighlightY, autoHighlightColumn, autoHighlightViewportY, variant = 'editor', onXmlClick }: Props) {
  const html = useMemo(() => entryXmlToHtml(xml), [xml]);

  const rootRef = useRef<HTMLDivElement>(null);

  // Refs so the click listener and auto-highlight effect always see the
  // latest props without needing to reattach/re-run on every preview keystroke.
  const initialColumnRef = useRef(initialColumn);
  initialColumnRef.current = initialColumn;
  const onHighlightRef = useRef(onHighlight);
  onHighlightRef.current = onHighlight;
  const onXmlClickRef = useRef(onXmlClick);
  onXmlClickRef.current = onXmlClick;

  // Single sync point: given a target element, drive all three panes.
  //   1. Image marker — read column/y from the nearest [data-y] ancestor.
  //   2. HTML preview — scroll so the element lines up where the user clicked
  //      (when desiredViewportY is given) or fall back to scrollIntoView.
  //   3. XML cursor   — read offset from the element's own data-xml-start,
  //      hand off the now-stable viewport Y so CodeMirror aligns to the same
  //      vertical position.
  // The click handler and the auto-highlight effect both funnel through here
  // so the three panes never disagree about what's being focused.
  function focusOn(el: HTMLElement, desiredViewportY?: number, focusEditor = false, columnHint?: string | null) {
    const yEl = el.matches('[data-y]') ? el : el.closest<HTMLElement>('[data-y]');
    if (yEl) {
      const y = Number.parseFloat(yEl.getAttribute('data-y') ?? '0') || 0;
      const column = columnHint !== undefined ? columnHint : findPrecedingColumn(yEl, initialColumnRef.current);
      if (column) onHighlightRef.current({ column, y });
    }

    // Scroll first so the bounding rect we hand to the XML side reflects
    // where the element ends up; otherwise auto-highlight (which shifts the
    // element into view) would align CodeMirror against the pre-scroll rect.
    if (desiredViewportY !== undefined) {
      scrollAncestorToViewportY(el, desiredViewportY);
    } else {
      el.scrollIntoView({ block: 'nearest' });
    }

    const offsetAttr = el.getAttribute('data-xml-start');
    const cb = onXmlClickRef.current;
    if (offsetAttr !== null && cb) {
      const offset = Number.parseInt(offsetAttr, 10);
      if (Number.isFinite(offset)) cb(offset, el.getBoundingClientRect().top, focusEditor);
    }
  }

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const onClick = (e: MouseEvent) => {
      if (!(e.target instanceof HTMLElement)) return;
      const target = e.target.closest<HTMLElement>('[data-xml-start]');
      if (target) focusOn(target, undefined, true);
    };
    root.addEventListener('click', onClick);
    return () => root.removeEventListener('click', onClick);
  }, []);

  // The caller passes a fresh autoHighlightKey on every navigation (router
  // location key), so the deps alone gate when this re-runs — no manual
  // cache. html is intentionally not a dep: we don't want to re-focus on
  // every keystroke during XML editing. This is safe because useDebounce
  // flushes synchronously on entry change, so the rendered DOM matches the
  // entry by the time autoHighlightKey changes.
  useEffect(() => {
    if (!autoHighlightKey) return;
    const root = rootRef.current;
    if (!root) return;
    const picked = pickAutoHighlightTarget(root, initialColumnRef.current, autoHighlightColumn, autoHighlightY);
    if (!picked) return;
    focusOn(picked.el, autoHighlightViewportY, false, picked.column);
  }, [autoHighlightKey, autoHighlightY, autoHighlightColumn, autoHighlightViewportY]);

  return (
    <div
      className={variant === 'public' ? 'entry-render entry-render--public' : 'entry-render'}
      ref={rootRef}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

// Pick the orth/sense whose data-y is the largest value ≤ targetY so that
// clicking a column image lands on the containing sense, not always the
// entry's first headword. Falls back to the first marker when nothing sits
// above the click (e.g. target is above the first orth) or when targetY is
// unset (keyboard/sidebar navigation).
//
// When targetColumn is given, only candidates in that column are considered:
// data-y is a percentage *within each column*, so for entries that span
// multiple columns a candidate elsewhere can still satisfy y ≤ targetY and
// hijack the pick. Walking <cb> markers in document order keeps track of the
// current column.
function pickAutoHighlightTarget(
  root: HTMLElement,
  initialColumn: string | null,
  targetColumn: string | undefined,
  targetY?: number,
): { el: HTMLElement; column: string | null } | null {
  const nodes = Array.from(root.querySelectorAll<HTMLElement>('cb, orth[data-y], .sense[data-y]'));
  const candidates: { el: HTMLElement; column: string | null }[] = [];
  let column = initialColumn;
  for (const el of nodes) {
    if (el.tagName === 'CB') {
      column = el.getAttribute('n');
    } else if (!targetColumn || column === targetColumn) {
      candidates.push({ el, column });
    }
  }
  // No candidates in the requested column (e.g. backend pointed us at an
  // entry whose senses are all on other columns). Fall back to the unfiltered
  // first marker so we still highlight something rather than silently bailing.
  if (candidates.length === 0) {
    let firstColumn = initialColumn;
    for (const el of nodes) {
      if (el.tagName === 'CB') firstColumn = el.getAttribute('n');
      else return { el, column: firstColumn };
    }
    return null;
  }
  if (targetY === undefined) return candidates[0];
  let best: { el: HTMLElement; column: string | null } | null = null;
  let bestY = -Infinity;
  for (const c of candidates) {
    const y = Number.parseFloat(c.el.getAttribute('data-y') ?? '');
    if (!Number.isFinite(y)) continue;
    if (y <= targetY && y > bestY) { best = c; bestY = y; }
  }
  return best ?? candidates[0];
}

// Scroll the element's nearest scrollable ancestor so el's top edge lands at
// the given viewport Y. Both values are in the same viewport-Y coordinate
// space, so the scroll delta is just the difference. The browser clamps
// scrollTop to [0, max], so unreachable positions stop at the closest edge.
export function scrollAncestorToViewportY(el: HTMLElement, desiredViewportY: number) {
  const container = findScrollableAncestor(el);
  if (!container) return;
  container.scrollTop += el.getBoundingClientRect().top - desiredViewportY;
}

export function findScrollableAncestor(el: Element): HTMLElement | null {
  let p = el.parentElement;
  while (p) {
    const style = getComputedStyle(p);
    if (/auto|scroll/.test(style.overflowY) && p.scrollHeight > p.clientHeight) return p;
    p = p.parentElement;
  }
  return null;
}

function findPrecedingColumn(el: Element, fallback: string | null): string | null {
  const root = el.closest('.entry-render') ?? document.body;
  const cbs = Array.from(root.querySelectorAll<HTMLElement>('cb'));
  let last: string | null = null;
  for (const cb of cbs) {
    if (cb.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) {
      last = cb.getAttribute('n');
    } else {
      break;
    }
  }
  return last ?? fallback;
}
