import { syntaxTree } from '@codemirror/language';
import {
  EditorSelection, type ChangeSpec, type EditorState, type SelectionRange,
} from '@codemirror/state';
import type { EditorView } from '@codemirror/view';
import type { SyntaxNode } from '@lezer/common';

// XML editing operations for the lexicon. Tag-changing buttons all funnel
// through `tagOp`, which implements one rule set:
//
// 1. If the selection is contained inside a same-tag X element → unwrap.
// 2. Else if any same-tag X touches/spans the selection → merge zone (fold
//    everything in the expanded zone into one X).
// 3. Else for inline-format targets (b/u/i) → plain wrap.
// 4. Else (content-tag target) find the kept container C: foreign if any
//    ancestor is foreign, else the outermost content-tag ancestor. Peel
//    every other content-tag ancestor (corruptly nested), then split C
//    around the selection: wrap selection in X; wrap each side's content
//    back in C with inline-format children (b/u/i) staying inside the C
//    remnant and other elements (br, etc.) staying bare between wrappers;
//    edge-trim text segments at run-edges (push non-letter chars outside
//    C). Drop empty C remnants.
// 5. Else (no content ancestor) → plain wrap.
//
// "Content tags" = the inventory below; they don't nest with each other.
// Inline format (b/u/i) nests freely.

const CONTENT_TAGS: ReadonlySet<string> = new Set([
  'foreign', 'orth', 'ref', 'form',
  'pos', 'gen', 'subc', 'case', 'mood', 'tns', 'number',
  'iType', 'gram', 'lbl', 'hom',
]);

const INLINE_FORMAT_SET: ReadonlySet<string> = new Set(['b', 'u', 'i']);

// "Foreign letter" matches the script's _is_foreign_letter (any alpha except
// the ɔ used as an editorial reverse-c).
const LETTER_RE = /\p{L}/u;
const isLetter = (c: string) => c.length > 0 && c !== 'ɔ' && LETTER_RE.test(c);
const isLetterOrDigit = (c: string) => isLetter(c) || (c >= '0' && c <= '9');

function hasLetters(s: string): boolean {
  for (const c of s) if (isLetter(c)) return true;
  return false;
}

// Edge-trim helpers. Mirror the script's _trim_foreign_edges: keep word-
// bound `-`, `.`, balanced `()` adjacent to letters; push everything else
// out of the wrapper.
function hasMatchingClose(s: string, pos: number): boolean {
  let depth = 0;
  for (let i = pos; i < s.length; i++) {
    if (s[i] === '(') depth++;
    else if (s[i] === ')') { depth--; if (depth === 0) return true; }
  }
  return false;
}

function hasMatchingOpen(s: string, pos: number, minPos: number): boolean {
  let depth = 0;
  for (let i = pos; i >= minPos; i--) {
    if (s[i] === ')') depth++;
    else if (s[i] === '(') { depth--; if (depth === 0) return true; }
  }
  return false;
}

function leftTrim(s: string): number {
  let i = 0;
  while (i < s.length) {
    const c = s[i];
    if (isLetter(c)) break;
    if (c === '-' && i + 1 < s.length && isLetter(s[i + 1])) break;
    if (c === '(' && hasMatchingClose(s, i)) break;
    i++;
  }
  return i;
}

function rightTrim(s: string, minPos: number): number {
  let i = s.length;
  while (i > minPos) {
    const c = s[i - 1];
    if (isLetter(c) || (c >= '0' && c <= '9')) break;
    if (c === '-' && i - 2 >= minPos && isLetter(s[i - 2])) break;
    if (c === '.' && i - 2 >= minPos && isLetterOrDigit(s[i - 2])) break;
    if (c === ')' && hasMatchingOpen(s, i - 1, minPos)) break;
    i--;
  }
  return i;
}

type Enclosing = {
  name: string;
  outerFrom: number; outerTo: number;
  innerFrom: number; innerTo: number;
  node: SyntaxNode;
};

// Reads the tag name and inner/outer bounds off an `Element` syntax node.
// Returns null for self-closing or otherwise malformed elements.
function readElement(state: EditorState, node: SyntaxNode): Enclosing | null {
  if (node.name !== 'Element') return null;
  const openTag = node.firstChild;
  const closeTag = node.lastChild;
  const tagNameNode = openTag?.getChild('TagName');
  if (!openTag || !closeTag || !tagNameNode || closeTag.name !== 'CloseTag') return null;
  return {
    name: state.doc.sliceString(tagNameNode.from, tagNameNode.to),
    outerFrom: node.from, outerTo: node.to,
    innerFrom: openTag.to, innerTo: closeTag.from,
    node,
  };
}

// Walks innermost-first up the syntax tree from `from`, collecting every
// content-tag Element whose content range covers [from, to].
function findContentAncestors(
  state: EditorState, from: number, to: number,
): Enclosing[] {
  const result: Enclosing[] = [];
  let node: SyntaxNode | null = syntaxTree(state).resolveInner(from, 1);
  while (node) {
    const el = readElement(state, node);
    if (el && CONTENT_TAGS.has(el.name) && el.innerFrom <= from && to <= el.innerTo) {
      result.push(el);
    }
    node = node.parent;
  }
  return result;
}

// Every `name`-tagged Element whose outer range touches or overlaps [from, to].
// Touch: outerTo===from or outerFrom===to. Overlap: standard.
function findElementsByNameNear(
  state: EditorState, from: number, to: number, name: string,
): Enclosing[] {
  const result: Enclosing[] = [];
  // Iterate one char beyond each side so adjacent elements get visited.
  syntaxTree(state).iterate({
    from: Math.max(0, from - 1),
    to:   Math.min(state.doc.length, to + 1),
    enter(n) {
      if (n.from > to || n.to < from) return;
      const el = readElement(state, n.node);
      if (!el || el.name !== name) return;
      result.push(el);
    },
  });
  return result;
}

// Iteratively expand [fromInit, toInit] to cover every X element that
// touches or overlaps the current zone. Stops at a fixed point.
function expandMergeZone(
  state: EditorState, fromInit: number, toInit: number, X: string,
): { from: number; to: number } {
  let from = fromInit;
  let to = toInit;
  for (;;) {
    let changed = false;
    for (const e of findElementsByNameNear(state, from, to, X)) {
      if (e.outerFrom < from) { from = e.outerFrom; changed = true; }
      if (e.outerTo   > to)   { to   = e.outerTo;   changed = true; }
    }
    if (!changed) return { from, to };
  }
}

// Slice [from, to] with all <X>/</X> open and close tags stripped.
function stripTagsByName(
  state: EditorState, from: number, to: number, X: string,
): string {
  const ranges: Array<{ from: number; to: number }> = [];
  syntaxTree(state).iterate({
    from, to,
    enter(n) {
      if (n.from < from || n.to > to) return;
      const el = readElement(state, n.node);
      if (!el || el.name !== X) return;
      ranges.push({ from: el.outerFrom, to: el.innerFrom });
      ranges.push({ from: el.innerTo,   to: el.outerTo   });
    },
  });
  let out = '';
  let pos = from;
  for (const r of ranges) {
    out += state.doc.sliceString(pos, r.from);
    pos = r.to;
  }
  out += state.doc.sliceString(pos, to);
  return out;
}

// Refuse a merge that would smuggle a non-formatting tag into a content
// wrapper (e.g. cross-<sense> merge of two foreigns). Inline format
// targets (b/u/i) accept anything inside, so always safe.
function isMergeSafe(inner: string, X: string): boolean {
  if (INLINE_FORMAT_SET.has(X)) return true;
  const tagRe = /<\/?([a-zA-Z][a-zA-Z0-9_-]*)/g;
  let m: RegExpExecArray | null;
  while ((m = tagRe.exec(inner)) !== null) {
    if (!INLINE_FORMAT_SET.has(m[1])) return false;
  }
  return true;
}

type Wrap = { changes: ChangeSpec; selection: SelectionRange };

function plainWrap(from: number, to: number, tag: string): Wrap {
  const open = `<${tag}>`;
  const close = `</${tag}>`;
  return {
    changes: [
      { from, insert: open },
      { from: to, insert: close },
    ],
    selection: EditorSelection.range(from + open.length, to + open.length),
  };
}

function unwrapElement(state: EditorState, enc: Enclosing, range: SelectionRange): Wrap {
  const inner = state.doc.sliceString(enc.innerFrom, enc.innerTo);
  const shift = enc.outerFrom - enc.innerFrom;
  return {
    changes: { from: enc.outerFrom, to: enc.outerTo, insert: inner },
    selection: EditorSelection.range(range.from + shift, range.to + shift),
  };
}

// One side of an extract is a list of these. 'text' segments get edge-
// trimmed at run boundaries; 'inline' segments stay inside the C remnant;
// 'opaque' segments are bare between C remnants (i.e. they split a side
// into multiple runs).
type Segment = { kind: 'text' | 'inline' | 'opaque'; text: string };

// Walk `parentNode`'s direct children within [sliceFrom, sliceTo], producing
// segments. Inner content-tag children are peeled (recursively flattened
// into their own children's segments). Returns null if the slice cuts
// through an inline/opaque child — that case is unsupported.
function collectSegments(
  state: EditorState, parentNode: SyntaxNode, sliceFrom: number, sliceTo: number,
): Segment[] | null {
  if (sliceFrom >= sliceTo) return [];
  const segs: Segment[] = [];
  let cursor = sliceFrom;
  for (let child = parentNode.firstChild; child; child = child.nextSibling) {
    // The parent's own tag wrappers — outside [innerFrom, innerTo] anyway.
    if (child.name === 'OpenTag' || child.name === 'CloseTag' || child.name === 'SelfClosingTag') continue;
    if (child.to <= sliceFrom) continue;
    if (child.from >= sliceTo) break;
    const isTextLike = child.name === 'Text'
      || child.name === 'EntityReference'
      || child.name === 'CharacterReference';
    if (isTextLike) {
      const a = Math.max(child.from, sliceFrom);
      const b = Math.min(child.to, sliceTo);
      if (cursor < a) segs.push({ kind: 'text', text: state.doc.sliceString(cursor, a) });
      segs.push({ kind: 'text', text: state.doc.sliceString(a, b) });
      cursor = b;
      continue;
    }
    const childEl = readElement(state, child);
    if (childEl !== null && CONTENT_TAGS.has(childEl.name)) {
      // Sibling content tag (wholly inside slice) — preserve verbatim so
      // we don't rip apart unrelated structure.
      if (child.from >= sliceFrom && child.to <= sliceTo) {
        if (cursor < child.from) segs.push({ kind: 'text', text: state.doc.sliceString(cursor, child.from) });
        segs.push({ kind: 'opaque', text: state.doc.sliceString(child.from, child.to) });
        cursor = child.to;
        continue;
      }
      // Slice cuts through a content-tag ancestor (e.g.
      // `<foreign><ref>[x]</ref></foreign>`) — peel by recursing into it.
      const childFrom = Math.max(child.from, sliceFrom);
      if (cursor < childFrom) segs.push({ kind: 'text', text: state.doc.sliceString(cursor, childFrom) });
      const innerFrom = Math.max(childEl.innerFrom, sliceFrom);
      const innerTo   = Math.min(childEl.innerTo,   sliceTo);
      const inner = collectSegments(state, child, innerFrom, innerTo);
      if (inner === null) return null;
      segs.push(...inner);
      cursor = Math.min(child.to, sliceTo);
      continue;
    }
    // Inline format / other element / self-closing — must sit wholly in slice.
    if (child.from < sliceFrom || child.to > sliceTo) return null;
    if (cursor < child.from) segs.push({ kind: 'text', text: state.doc.sliceString(cursor, child.from) });
    const isInline = childEl !== null && INLINE_FORMAT_SET.has(childEl.name);
    segs.push({
      kind: isInline ? 'inline' : 'opaque',
      text: state.doc.sliceString(child.from, child.to),
    });
    cursor = child.to;
  }
  if (cursor < sliceTo) segs.push({ kind: 'text', text: state.doc.sliceString(cursor, sliceTo) });
  // Coalesce adjacent text segments and drop empties.
  const out: Segment[] = [];
  for (const s of segs) {
    if (s.text === '') continue;
    const last = out[out.length - 1];
    if (last && last.kind === 'text' && s.kind === 'text') last.text += s.text;
    else out.push(s);
  }
  return out;
}

// A "run" is a maximal stretch of text+inline segments. Opaque segments
// split a side into multiple runs. Each run gets wrapped in <C>...</C> if
// its body has letters; non-letter chars at the run's leading/trailing
// edges are pushed outside the wrapper.
function renderRun(run: Segment[], C: string): string {
  if (run.length === 0) return '';
  let outerLeft = '';
  let outerRight = '';
  let body = '';
  for (let i = 0; i < run.length; i++) {
    const seg = run[i];
    if (seg.kind !== 'text') { body += seg.text; continue; }
    const isFirst = i === 0;
    const isLast  = i === run.length - 1;
    const s = seg.text;
    let l = 0;
    let r = s.length;
    if (isFirst) {
      l = leftTrim(s);
      outerLeft = s.slice(0, l);
    }
    if (isLast) {
      r = rightTrim(s, l);
      outerRight = s.slice(r);
    }
    body += s.slice(l, r);
  }
  if (!hasLetters(body)) return outerLeft + body + outerRight;
  return `${outerLeft}<${C}>${body}</${C}>${outerRight}`;
}

function renderSide(segs: Segment[], C: string): string {
  let out = '';
  let run: Segment[] = [];
  for (const seg of segs) {
    if (seg.kind === 'opaque') {
      out += renderRun(run, C);
      out += seg.text;
      run = [];
    } else {
      run.push(seg);
    }
  }
  out += renderRun(run, C);
  return out;
}

export function tagOp(
  state: EditorState, range: SelectionRange, X: string,
): Wrap | null {
  // 1. If the selection is contained in a single same-tag X → unwrap.
  const xTouching = findElementsByNameNear(state, range.from, range.to, X);
  for (const x of xTouching) {
    if (x.innerFrom <= range.from && range.to <= x.innerTo) {
      return unwrapElement(state, x, range);
    }
  }

  // 2. Any same-tag X touching → merge zone.
  if (xTouching.length > 0) {
    const { from, to } = expandMergeZone(state, range.from, range.to, X);
    const inner = stripTagsByName(state, from, to, X);
    if (!isMergeSafe(inner, X)) return null;
    const open = `<${X}>`;
    const close = `</${X}>`;
    return {
      changes: { from, to, insert: open + inner + close },
      selection: EditorSelection.range(from + open.length, from + open.length + inner.length),
    };
  }

  // 3. Inline-format target → plain wrap (inline format nests freely).
  if (INLINE_FORMAT_SET.has(X)) {
    if (range.empty) return null;
    return plainWrap(range.from, range.to, X);
  }

  // 4. Content-tag target with an ancestor → extract.
  const ancestors = findContentAncestors(state, range.from, range.to);
  if (ancestors.length === 0) {
    if (range.empty) return null;
    return plainWrap(range.from, range.to, X);
  }

  const foreign = ancestors.find((a) => a.name === 'foreign');
  const C = foreign ?? ancestors[ancestors.length - 1];

  const beforeSegs = collectSegments(state, C.node, C.innerFrom, range.from);
  const afterSegs  = collectSegments(state, C.node, range.to, C.innerTo);
  if (beforeSegs === null || afterSegs === null) return null;

  const middle = state.doc.sliceString(range.from, range.to);
  const beforeRendered = renderSide(beforeSegs, C.name);
  const afterRendered  = renderSide(afterSegs,  C.name);
  const wrappedOpen  = `<${X}>`;
  const wrappedClose = `</${X}>`;
  const replacement = beforeRendered + wrappedOpen + middle + wrappedClose + afterRendered;
  const selOffset = beforeRendered.length + wrappedOpen.length;

  // Build changes: replace C, plus peel any outside-C content-tag ancestors.
  // Inside-C ancestors are already peeled by collectSegments via recursion.
  const changes: ChangeSpec[] = [
    { from: C.outerFrom, to: C.outerTo, insert: replacement },
  ];
  for (const a of ancestors) {
    if (a === C) continue;
    if (a.outerFrom < C.outerFrom || a.outerTo > C.outerTo) {
      changes.push({ from: a.outerFrom, to: a.innerFrom });
      changes.push({ from: a.innerTo,   to: a.outerTo   });
    }
  }

  const selStart = state.changes(changes).mapPos(C.outerFrom) + selOffset;
  return {
    changes,
    selection: EditorSelection.range(selStart, selStart + middle.length),
  };
}

export function applyTag(view: EditorView, tag: string): boolean {
  const { state } = view;
  const ranges = state.selection.ranges;
  const wraps = ranges.map((r) => tagOp(state, r, tag));
  if (wraps.every((w) => w === null)) return false;
  view.dispatch({
    changes: wraps.flatMap((w) => w ? [w.changes] : []),
    selection: EditorSelection.create(
      wraps.map((w, i) => w?.selection ?? ranges[i]),
      state.selection.mainIndex,
    ),
    scrollIntoView: true,
  });
  view.focus();
  return true;
}
