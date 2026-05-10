// Smart-default and live-autocomplete logic for `<ref target="#xxx">`.
// Both consult the in-memory headwords index loaded by HeadwordsContext;
// the editor never hits the network for these.

import { syntaxTree } from '@codemirror/language';
import type { CompletionContext, CompletionResult, CompletionSource } from '@codemirror/autocomplete';
import type { SyntaxNode } from '@lezer/common';

import { fold, type FoldedEntry } from '../components/HeadwordsContext';

// Roman numeral table — homographs in this lexicon don't go beyond a
// handful, so a flat lookup is simpler than a real numeral parser.
const ROMAN: Readonly<Record<string, number>> = {
  I: 1, II: 2, III: 3, IV: 4, V: 5, VI: 6, VII: 7, VIII: 8, IX: 9, X: 10,
};

const HOMOGRAPH_RE = /^([IVX]+)\.\s+(.+)$/;

// Splits "I. Hostus" into stem="Hostus", index=1. Returns index=null when
// the input has no Roman-numeral prefix (the common case).
function parseHomograph(text: string): { stem: string; index: number | null } {
  const trimmed = text.trim();
  const m = trimmed.match(HOMOGRAPH_RE);
  if (!m) return { stem: trimmed, index: null };
  const idx = ROMAN[m[1]];
  if (idx === undefined) return { stem: trimmed, index: null };
  return { stem: m[2], index: idx };
}

// `ref-NNNNN` slugs are auto-assigned to entries that lack an XML id (the
// "see X" redirects). They have no xml id to point at, so they can never
// be a valid <ref target>.
const isLinkable = (h: FoldedEntry) => !h.url_id.startsWith('ref-');

// Returns "#url_id" when the selection unambiguously points at a single
// entry, else "". With a Roman-numeral prefix we require an exact homograph
// match (e.g. "II. Hostus" → must find url_id="hostus2"). Without one we
// only resolve when there's a single matching entry — homographs left
// ambiguous deliberately fall through to the autocomplete.
export function resolveRefTarget(
  selection: string,
  headwords: readonly FoldedEntry[],
): string {
  const { stem, index } = parseHomograph(selection);
  const folded = fold(stem);
  if (folded.length === 0) return '';

  if (index !== null) {
    const expected = `${folded}${index}`;
    return headwords.some((h) => h.url_id === expected) ? `#${expected}` : '';
  }

  const matches = headwords.filter((h) =>
    isLinkable(h) && (h.fold === folded || h.alt_folds.includes(folded)),
  );
  return matches.length === 1 ? `#${matches[0].url_id}` : '';
}

// Walks up from `node` looking for an AttributeValue whose Attribute is
// `target` on a `<ref>` open tag. Returns the value-content range (the
// span between the surrounding quotes) or null.
function refTargetRange(
  node: SyntaxNode | null,
  read: (from: number, to: number) => string,
): { from: number; to: number } | null {
  let n: SyntaxNode | null = node;
  while (n && n.name !== 'AttributeValue') n = n.parent;
  if (!n) return null;
  const attr = n.parent;
  if (!attr || attr.name !== 'Attribute') return null;
  const nameNode = attr.getChild('AttributeName');
  if (!nameNode || read(nameNode.from, nameNode.to) !== 'target') return null;
  const opener = attr.parent;
  if (!opener || (opener.name !== 'OpenTag' && opener.name !== 'SelfClosingTag')) return null;
  const tagNameNode = opener.getChild('TagName');
  if (!tagNameNode || read(tagNameNode.from, tagNameNode.to) !== 'ref') return null;
  // Strip surrounding quotes when present. Lezer-XML usually produces a
  // quoted value; treat unquoted as the whole node range.
  const first = read(n.from, n.from + 1);
  const last  = read(n.to - 1, n.to);
  const quoted = (first === '"' || first === "'") && first === last;
  return quoted
    ? { from: n.from + 1, to: n.to - 1 }
    : { from: n.from,     to: n.to };
}

const MAX_OPTIONS = 50;

export function refTargetCompletion(
  getHeadwords: () => readonly FoldedEntry[],
): CompletionSource {
  return (context: CompletionContext): CompletionResult | null => {
    const tree = syntaxTree(context.state);
    const node = tree.resolveInner(context.pos, -1);
    const read = (from: number, to: number) => context.state.sliceDoc(from, to);
    const range = refTargetRange(node, read);
    if (!range) return null;
    if (context.pos < range.from || context.pos > range.to) return null;

    const raw = read(range.from, range.to);
    const query = raw.startsWith('#') ? raw.slice(1) : raw;
    const folded = fold(query);

    // No query → only volunteer when explicitly asked (Ctrl/Cmd-Space),
    // otherwise opening a ref would dump the whole headword list.
    if (folded.length === 0 && !context.explicit) return null;

    const headwords = getHeadwords();
    const options = [];
    for (const h of headwords) {
      if (!isLinkable(h)) continue;
      const primary = h.fold.startsWith(folded);
      const altIdx = primary ? -1 : h.alt_folds.findIndex((f) => f.startsWith(folded));
      if (!primary && altIdx < 0) continue;
      const display = primary ? h.headword : h.alt_headwords[altIdx];
      options.push({
        label: `#${h.url_id}`,
        detail: display,
        apply: `#${h.url_id}`,
        // Custom type — picked up by the .cm-completionIcon-tei-ref CSS
        // rule to hide the otherwise-empty icon column for these options.
        type: 'tei-ref',
        boost: primary ? 1 : 0,
      });
      if (options.length >= MAX_OPTIONS) break;
    }
    if (options.length === 0) return null;

    return {
      from: range.from,
      to: range.to,
      options,
      filter: false,
    };
  };
}
