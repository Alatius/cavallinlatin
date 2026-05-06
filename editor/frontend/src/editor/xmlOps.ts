import { syntaxTree } from '@codemirror/language';
import {
  EditorSelection, type ChangeSpec, type EditorState, type SelectionRange,
} from '@codemirror/state';
import type { EditorView } from '@codemirror/view';
import type { SyntaxNode } from '@lezer/common';

// XML editing operations for the lexicon. Each operation is a `Command`-style
// function that mutates the current selection and returns a boolean. The
// content-tag operations (everything except b/u/i) try the rules in order:
//
//   0. Same-tag merge: if the selection touches or overlaps any <X>
//      element(s) of the target tag — and the chain contains no *other*
//      content-tag ancestor — fold them all into one <X>. Snug selection
//      inside a sole <X> still toggles off (unwrap). Adjacent siblings,
//      crossed boundaries, and chains of touching <X> all collapse here so
//      we never produce nested or neighbouring duplicates.
//   1. No content-tag ancestor      → plain wrap.
//   2. Outermost is the same tag,
//      snug to the selection,
//      no nested content tags       → unwrap (toggle off).
//   3. Outermost is the same tag,
//      no nested content tags,
//      not snug                     → noop.
//   4. <foreign> in the chain AND
//      target is a Latin-out tag    → split-and-trim foreign around selection,
//                                      peel any non-foreign ancestors.
//   5. Otherwise                    → replace outermost content ancestor with
//                                      the target tag, peel any nested
//                                      content tags inside it.
//
// "Latin-out" is everything in CONTENT_TAGS except `foreign`. The split-and-
// trim algorithm mirrors the script's _trim_foreign_edges (preserves word-
// bound `-`, `.`, balanced parens at the foreign edges).

// "Foreign letter" matches the script's _is_foreign_letter (any alpha except
// the ɔ used as an editorial reverse-c).
const LETTER_RE = /\p{L}/u;
const isLetter = (c: string) => c.length > 0 && c !== 'ɔ' && LETTER_RE.test(c);
const isLetterOrDigit = (c: string) => isLetter(c) || (c >= '0' && c <= '9');

function hasMatchingClose(s: string, pos: number): boolean {
  let depth = 0;
  for (let i = pos; i < s.length; i++) {
    const c = s[i];
    if (c === '(') depth++;
    else if (c === ')') {
      depth--;
      if (depth === 0) return true;
    }
  }
  return false;
}

function hasMatchingOpen(s: string, pos: number, minPos: number): boolean {
  let depth = 0;
  for (let i = pos; i >= minPos; i--) {
    const c = s[i];
    if (c === ')') depth++;
    else if (c === '(') {
      depth--;
      if (depth === 0) return true;
    }
  }
  return false;
}

// Cut points for trimming non-letter chars from the edges of a foreign
// fragment. Returns [left, right] such that s.slice(left, right) is the
// text that stays inside <foreign>; everything outside gets pushed out.
function trimEdges(s: string): [number, number] {
  let left = 0;
  while (left < s.length) {
    const c = s[left];
    if (isLetter(c)) break;
    if (c === '-' && left + 1 < s.length && isLetter(s[left + 1])) break;
    if (c === '(' && hasMatchingClose(s, left)) break;
    left++;
  }
  let right = s.length;
  while (right > left) {
    const c = s[right - 1];
    if (isLetter(c) || (c >= '0' && c <= '9')) break;
    if (c === '-' && right - 2 >= 0 && isLetter(s[right - 2])) break;
    if (c === '.' && right - 2 >= 0 && isLetterOrDigit(s[right - 2])) break;
    if (c === ')' && hasMatchingOpen(s, right - 1, left)) break;
    right--;
  }
  return [left, right];
}

function hasLetters(s: string): boolean {
  for (const c of s) if (isLetter(c)) return true;
  return false;
}

// The set of "content tags" that don't nest with each other. Inline format
// (b, u, i) is intentionally excluded — those nest freely.
const CONTENT_TAGS: ReadonlySet<string> = new Set([
  'foreign', 'orth', 'ref', 'form',
  'pos', 'gen', 'subc', 'case', 'mood', 'tns', 'number',
  'iType', 'gram', 'lbl', 'hom',
]);

type Enclosing = {
  name: string;
  outerFrom: number; outerTo: number;
  innerFrom: number; innerTo: number;
};

// Reads the tag name and inner/outer bounds off an `Element` syntax node,
// or returns null for self-closing or otherwise malformed elements.
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
  };
}

// Walks innermost-first up the syntax tree from `from`, yielding every
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

// Open- and close-tag ranges of every content-tag Element strictly inside
// [innerFrom, innerTo] — i.e. the deletion ranges to peel them.
function findInnerContentTagRanges(
  state: EditorState, innerFrom: number, innerTo: number,
): Array<{ from: number; to: number }> {
  const ranges: Array<{ from: number; to: number }> = [];
  syntaxTree(state).iterate({
    from: innerFrom,
    to: innerTo,
    enter(n) {
      if (n.from < innerFrom || n.to > innerTo) return;
      const el = readElement(state, n.node);
      if (!el || !CONTENT_TAGS.has(el.name)) return;
      // openTag = [outerFrom, innerFrom); closeTag = [innerTo, outerTo).
      ranges.push({ from: el.outerFrom, to: el.innerFrom });
      ranges.push({ from: el.innerTo,   to: el.outerTo   });
    },
  });
  return ranges;
}

// Every `name`-tagged Element whose outer range touches or overlaps
// [from, to]. Touch: outerTo===from or outerFrom===to. Overlap: standard.
function findElementsByNameNear(
  state: EditorState, from: number, to: number, name: string,
): Enclosing[] {
  const result: Enclosing[] = [];
  // Iterate one char beyond each side so adjacent elements (whose extent
  // is just outside [from, to]) get visited.
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
// touches or overlaps the current zone. Stops at a fixed point. After
// each expansion the new boundary may itself be adjacent to *another*
// X element that wasn't visible from the original window (e.g. a chain
// of three adjacent <foreign> blocks where the outermost is reached only
// after the middle one has been included).
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
  ranges.sort((a, b) => a.from - b.from);
  let out = '';
  let pos = from;
  for (const r of ranges) {
    out += state.doc.sliceString(pos, r.from);
    pos = r.to;
  }
  out += state.doc.sliceString(pos, to);
  return out;
}

const INLINE_FORMAT_SET: ReadonlySet<string> = new Set(['b', 'u', 'i']);

// Refuse a merge that would smuggle a non-formatting tag into a content
// wrapper (e.g. a cross-<sense> merge of two foreigns). Inline format
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

function sameTagMergeOrToggle(
  state: EditorState, range: SelectionRange, X: string, xTouching: Enclosing[],
): Wrap | null {
  // Selection fully inside a sole X: snug-unwrap or noop. Anything else
  // (multiple X, or selection extending past one) falls through to merge.
  if (xTouching.length === 1) {
    const sole = xTouching[0];
    if (sole.innerFrom <= range.from && range.to <= sole.innerTo) {
      return isSnug(sole, range) ? unwrapElement(state, sole, range) : null;
    }
  }
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

// --- Wrap construction ---

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

function isSnug(enc: Enclosing, range: SelectionRange): boolean {
  return enc.innerFrom === range.from && enc.innerTo === range.to;
}

function unwrapElement(state: EditorState, enc: Enclosing, range: SelectionRange): Wrap {
  const inner = state.doc.sliceString(enc.innerFrom, enc.innerTo);
  const shift = enc.outerFrom - enc.innerFrom;
  return {
    changes: { from: enc.outerFrom, to: enc.outerTo, insert: inner },
    selection: EditorSelection.range(range.from + shift, range.to + shift),
  };
}

// Replace the outermost content ancestor's tag with `<X>`, and remove the
// open/close tags of any content-tag elements nested inside it (peel). Their
// text content remains in place. Selection lands on the new inner content
// range — coarse but predictable; user can refine.
function replaceWithPeel(
  state: EditorState, X: string, outermost: Enclosing,
): Wrap {
  const innerTagRanges = findInnerContentTagRanges(
    state, outermost.innerFrom, outermost.innerTo,
  );
  // Build the new inner content by stitching slices around the removed tags.
  innerTagRanges.sort((a, b) => a.from - b.from);
  let newInner = '';
  let pos = outermost.innerFrom;
  for (const r of innerTagRanges) {
    newInner += state.doc.sliceString(pos, r.from);
    pos = r.to;
  }
  newInner += state.doc.sliceString(pos, outermost.innerTo);

  const open = `<${X}>`;
  const close = `</${X}>`;
  const replacement = open + newInner + close;
  const newInnerFrom = outermost.outerFrom + open.length;
  return {
    changes: { from: outermost.outerFrom, to: outermost.outerTo, insert: replacement },
    selection: EditorSelection.range(newInnerFrom, newInnerFrom + newInner.length),
  };
}

// Foreign-extract path: split-and-trim the (innermost) <foreign>, wrap the
// selection in <X>, and peel any non-foreign content ancestors that wrap it.
function foreignExtractWithPeel(
  state: EditorState, range: SelectionRange, X: string,
  ancestors: Enclosing[],
): Wrap | null {
  if (range.empty) return null;
  // Innermost foreign — closest to the selection.
  const foreign = ancestors.find((a) => a.name === 'foreign');
  if (!foreign) return null;

  // Compute the foreign-replacement string (replaces foreign.outer). Each
  // half (text before / after selection within the foreign) gets trimmed on
  // BOTH edges: chars at the foreign's outer edge are pushed out as plain
  // text just like chars next to the new <X>. Trace for
  // <foreign>(apple, orange)</foreign> select `apple`:
  //   beforeRaw = "(",          trim → outerLeft="(", keep="",     outerRight=""
  //   afterRaw  = ", orange)",  trim → outerLeft=", ", keep="orange", outerRight=")"
  // ⇒ "(<orth>apple</orth>, <foreign>orange</foreign>)"
  const beforeRaw = state.doc.sliceString(foreign.innerFrom, range.from);
  const middle    = state.doc.sliceString(range.from, range.to);
  const afterRaw  = state.doc.sliceString(range.to, foreign.innerTo);
  const [bLeft, bRight] = trimEdges(beforeRaw);
  const [aLeft, aRight] = trimEdges(afterRaw);
  const beforeOuterLeft  = beforeRaw.slice(0, bLeft);
  const beforeKeep       = beforeRaw.slice(bLeft, bRight);
  const beforeOuterRight = beforeRaw.slice(bRight);
  const afterOuterLeft   = afterRaw.slice(0, aLeft);
  const afterKeep        = afterRaw.slice(aLeft, aRight);
  const afterOuterRight  = afterRaw.slice(aRight);
  const leftFragment  = hasLetters(beforeKeep) ? `<foreign>${beforeKeep}</foreign>` : beforeKeep;
  const rightFragment = hasLetters(afterKeep)  ? `<foreign>${afterKeep}</foreign>`  : afterKeep;
  const wrappedOpen  = `<${X}>`;
  const wrappedClose = `</${X}>`;
  const foreignReplacement =
    beforeOuterLeft + leftFragment + beforeOuterRight
    + wrappedOpen + middle + wrappedClose
    + afterOuterLeft + rightFragment + afterOuterRight;

  // Position of the new <X> content within foreignReplacement, measured
  // from the start of the inserted string.
  const selOffset = beforeOuterLeft.length + leftFragment.length + beforeOuterRight.length + wrappedOpen.length;

  // Single foreign ancestor, no peeling — same as the simple split case.
  if (ancestors.length === 1) {
    const selStart = foreign.outerFrom + selOffset;
    return {
      changes: { from: foreign.outerFrom, to: foreign.outerTo, insert: foreignReplacement },
      selection: EditorSelection.range(selStart, selStart + middle.length),
    };
  }

  // Multiple ancestors: replace the chosen foreign with the extract result,
  // and peel every *other* content ancestor — including any outer
  // (corruptly-nested) <foreign> wrappers.
  const changes: ChangeSpec[] = [
    { from: foreign.outerFrom, to: foreign.outerTo, insert: foreignReplacement },
  ];
  for (const a of ancestors) {
    if (a === foreign) continue;
    changes.push({ from: a.outerFrom, to: a.innerFrom });   // open tag
    changes.push({ from: a.innerTo, to: a.outerTo });        // close tag
  }
  // Position the selection on the new <X> content. mapPos(foreign.outerFrom)
  // with default assoc (-1) lands at the LEFT side of the foreign-replace —
  // i.e. the position right where the inserted foreignReplacement begins.
  // (assoc=1 would land at the *end* of the insertion, which we don't want.)
  // Deletions of ancestor open tags before foreign.outerFrom shift this
  // value left automatically.
  const changeSet = state.changes(changes);
  const newForeignStart = changeSet.mapPos(foreign.outerFrom);
  const selStart = newForeignStart + selOffset;
  return {
    changes,
    selection: EditorSelection.range(selStart, selStart + middle.length),
  };
}

// Unified content-tag operation: foreign + every Latin-out tag.
function contentTagOp(
  state: EditorState, range: SelectionRange, X: string,
): Wrap | null {
  const ancestors = findContentAncestors(state, range.from, range.to);
  const xTouching = findElementsByNameNear(state, range.from, range.to, X);

  // Same-tag merge / toggle wins when the chain has no *other* content tag.
  // With another content tag in the chain (e.g. <orth><foreign>x</foreign></orth>
  // clicking foreign), fall through to replace-and-peel so the orth gets
  // properly unwrapped instead of leaving an orth around bare text.
  if (xTouching.length >= 1 && !ancestors.some((a) => a.name !== X)) {
    return sameTagMergeOrToggle(state, range, X, xTouching);
  }

  if (ancestors.length === 0) {
    if (range.empty) return null;
    return plainWrap(range.from, range.to, X);
  }

  const outermost = ancestors[ancestors.length - 1];

  // Defensive fallback for the same-tag-only chain — should already have
  // been handled by the merge branch above.
  if (ancestors.length === 1 && outermost.name === X) {
    return isSnug(outermost, range) ? unwrapElement(state, outermost, range) : null;
  }

  if (X !== 'foreign' && ancestors.some((a) => a.name === 'foreign')) {
    return foreignExtractWithPeel(state, range, X, ancestors);
  }
  return replaceWithPeel(state, X, outermost);
}

// Inline formatting (b, u, i): toggle on the same tag, no nesting rule.
// Uses the same merge logic as content tags so adjacent <b><b> get folded
// into one when the selection bridges them.
function inlineFormatOp(
  state: EditorState, range: SelectionRange, tag: string,
): Wrap | null {
  const xTouching = findElementsByNameNear(state, range.from, range.to, tag);
  if (xTouching.length >= 1) {
    return sameTagMergeOrToggle(state, range, tag, xTouching);
  }
  if (range.empty) return null;
  return plainWrap(range.from, range.to, tag);
}

// --- Public commands ---

function runOp(
  view: EditorView,
  op: (state: EditorState, range: SelectionRange) => Wrap | null,
): boolean {
  const { state } = view;
  const wraps: (Wrap | null)[] = state.selection.ranges.map((r) => op(state, r));
  if (wraps.every((w) => w === null)) return false;
  const allChanges: ChangeSpec[] = [];
  const newRanges: SelectionRange[] = [];
  for (let i = 0; i < wraps.length; i++) {
    const w = wraps[i];
    if (w) {
      allChanges.push(w.changes);
      newRanges.push(w.selection);
    } else {
      newRanges.push(state.selection.ranges[i]);
    }
  }
  view.dispatch({
    changes: allChanges,
    selection: EditorSelection.create(newRanges, state.selection.mainIndex),
    scrollIntoView: true,
  });
  view.focus();
  return true;
}

export const LATIN_OUT_TAGS = [
  'orth', 'ref', 'form',
  'pos', 'gen', 'subc', 'case', 'mood', 'tns', 'number',
  'iType', 'gram', 'lbl', 'hom',
] as const;

export const INLINE_FORMAT_TAGS = ['b', 'u', 'i'] as const;

export function applyLatinOut(view: EditorView, tag: string): boolean {
  return runOp(view, (state, range) => contentTagOp(state, range, tag));
}

export function applyInlineFormat(view: EditorView, tag: string): boolean {
  return runOp(view, (state, range) => inlineFormatOp(state, range, tag));
}

export function applyForeign(view: EditorView): boolean {
  return runOp(view, (state, range) => contentTagOp(state, range, 'foreign'));
}
