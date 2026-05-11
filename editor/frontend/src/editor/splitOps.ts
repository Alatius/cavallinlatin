import { syntaxTree } from '@codemirror/language';
import type { EditorState } from '@codemirror/state';
import type { SyntaxNode } from '@lezer/common';

import { readElement } from './xmlOps';

// Result of trying to compute a split point at or before the cursor.
// - 'ok': we found a structural boundary; the modal can show a preview.
// - 'nested': cursor sits inside a descendant element (the user has to move
//   the caret outside of e.g. a <sense> before splitting).
// - 'no-boundary': the cursor is before the first child or somehow yields no
//   valid boundary — splitting at the very start would leave an empty half.
// - 'no-orth-in-second': the second half wouldn't contain any <orth>; without
//   one the new entry has no headword and the backend would refuse anyway.
// - 'no-entry': the document has no parseable <entry> root (unsaved or
//   malformed buffer).
export type SnapResult =
  | { kind: 'ok'; offset: number; firstInner: string; secondInner: string }
  | { kind: 'nested' }
  | { kind: 'no-boundary' }
  | { kind: 'no-orth-in-second' }
  | { kind: 'no-entry' };

function rangeContainsOrth(state: EditorState, from: number, to: number): boolean {
  let found = false;
  syntaxTree(state).iterate({
    from, to,
    enter(n) {
      if (found) return false;
      if (n.name !== 'Element') return undefined;
      if (readElement(state, n.node)?.name === 'orth') {
        found = true;
        return false;
      }
      return undefined;
    },
  });
  return found;
}

function findEntryElement(state: EditorState): SyntaxNode | null {
  const top = syntaxTree(state).topNode;
  for (let c = top.firstChild; c; c = c.nextSibling) {
    if (readElement(state, c)?.name === 'entry') return c;
  }
  return null;
}

// Walks the syntax tree to find a valid split point at or before `cursor`.
// "Valid" = a position directly between top-level children of the root
// <entry> element. The matching backend endpoint re-validates by parsing
// both halves, so this is purely a UX affordance (refuse early, show a
// preview).
export function snapToSplit(state: EditorState, cursor: number): SnapResult {
  const entry = findEntryElement(state);
  if (!entry) return { kind: 'no-entry' };
  const entryEl = readElement(state, entry);
  if (!entryEl) return { kind: 'no-entry' };
  const { innerFrom, innerTo } = entryEl;

  // Boundaries live at the *end* of each direct child (excluding the entry's
  // own OpenTag/CloseTag). innerFrom is implicitly the "before all children"
  // boundary but it's excluded: splitting there leaves the first half empty.
  const boundaries: number[] = [];
  for (let c = entry.firstChild; c; c = c.nextSibling) {
    if (c.name === 'OpenTag' || c.name === 'CloseTag') continue;
    // Cursor inside an Element or SelfClosingTag means the caret is inside a
    // nested structure; bail before scanning further.
    if ((c.name === 'Element' || c.name === 'SelfClosingTag')
        && c.from < cursor && cursor < c.to) {
      return { kind: 'nested' };
    }
    boundaries.push(c.to);
  }

  // Largest boundary strictly inside (innerFrom, innerTo] that's at-or-before
  // the cursor. innerTo itself is excluded because it'd leave an empty second
  // half. Equivalently, the boundary must be < innerTo, which is enforced by
  // skipping the entry's CloseTag above.
  let snap = -1;
  for (const b of boundaries) {
    if (b > innerFrom && b < innerTo && b <= cursor && b > snap) snap = b;
  }
  if (snap < 0) return { kind: 'no-boundary' };

  // Refuse early when the new entry would have no headword. The backend
  // would 400 anyway; doing it client-side keeps the user out of the
  // confirmation modal for a guaranteed-failure split.
  if (!rangeContainsOrth(state, snap, innerTo)) {
    return { kind: 'no-orth-in-second' };
  }

  return {
    kind: 'ok',
    offset: snap,
    firstInner: state.doc.sliceString(innerFrom, snap),
    secondInner: state.doc.sliceString(snap, innerTo),
  };
}
