import { useState } from 'react';
import type { ReactCodeMirrorRef } from '@uiw/react-codemirror';
import type { EditorView } from '@codemirror/view';
import { applyForeign, applyInlineFormat, applyLatinOut } from './xmlOps';

type Props = { editorRef: React.RefObject<ReactCodeMirrorRef | null> };
type Panel = 'tags' | 'chars';

type TagItem = { tag: string; label: string; kind: 'inline' | 'latinOut' | 'foreign' };

// Each top-level array is one visual group, separated by a vertical divider.
const TAG_GROUPS: ReadonlyArray<ReadonlyArray<TagItem>> = [
  [
    { tag: 'orth',    label: 'Uppslagsord',       kind: 'latinOut' },
    { tag: 'form',    label: 'Form',              kind: 'latinOut' },
    { tag: 'ref',     label: 'Referens',          kind: 'latinOut' },
  ],
  [
    { tag: 'foreign', label: 'Latin',             kind: 'foreign'  },
  ],
  [
    { tag: 'b',       label: 'Fet',               kind: 'inline'   },
    { tag: 'u',       label: 'Understruken',      kind: 'inline'   },
    { tag: 'i',       label: 'Kursiv',            kind: 'inline'   },
  ],
  [
    { tag: 'pos',     label: 'Ordklass',          kind: 'latinOut' },
    { tag: 'gen',     label: 'Genus',             kind: 'latinOut' },
    { tag: 'subc',    label: 'Subkategorisering', kind: 'latinOut' },
    { tag: 'case',    label: 'Kasus',             kind: 'latinOut' },
    { tag: 'mood',    label: 'Modus',             kind: 'latinOut' },
    { tag: 'tns',     label: 'Tempus',            kind: 'latinOut' },
    { tag: 'number',  label: 'Numerus',           kind: 'latinOut' },
    { tag: 'iType',   label: 'Böjningstyp',       kind: 'latinOut' },
    { tag: 'lbl',     label: 'Etikett',           kind: 'latinOut' },
    { tag: 'hom',     label: 'Homograf',          kind: 'latinOut' },
    { tag: 'gram',    label: 'Grammatik',         kind: 'latinOut' },
  ],
];

// Char palette entries are either a plain string (insert == display) or an
// object distinguishing the two — needed for combining marks, where we
// insert just the combiner but show it on a dotted-circle base.
type CharEntry = string | { display: string; insert: string };
const charDisplay = (c: CharEntry) => typeof c === 'string' ? c : c.display;
const charInsert  = (c: CharEntry) => typeof c === 'string' ? c : c.insert;

// Char groups picked from the live corpus's most-used non-ASCII glyphs.
// Swedish ä ö å are on the keyboard so they're omitted.
const CHAR_GROUPS: ReadonlyArray<ReadonlyArray<CharEntry>> = [
  // Long Latin vowels (macron)
  ['Ā', 'ā', 'Ē', 'ē', 'Ī', 'ī', 'Ō', 'ō', 'Ū', 'ū', 'Ȳ', 'ȳ'],
  // Short Latin vowels (breve)
  ['Ă', 'ă', 'Ĕ', 'ĕ', 'Ĭ', 'ĭ', 'Ŏ', 'ŏ', 'Ŭ', 'ŭ'],
  // Ligatures & extras
  ['Æ', 'æ', 'Œ', 'œ', 'ß'],
  // Greek lowercase
  ['α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ',
   'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'ς', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω'],
  // Greek uppercase
  ['Α', 'Β', 'Γ', 'Δ', 'Ε', 'Ζ', 'Η', 'Θ', 'Ι', 'Κ', 'Λ', 'Μ',
   'Ν', 'Ξ', 'Ο', 'Π', 'Ρ', 'Σ', 'Τ', 'Υ', 'Φ', 'Χ', 'Ψ', 'Ω'],
  // Polytonic — lowercase breathings (smooth/rough alternated by vowel).
  // Initial υ always takes rough; smooth υ is omitted.
  ['ἀ', 'ἁ', 'ἐ', 'ἑ', 'ἠ', 'ἡ', 'ἰ', 'ἱ', 'ὀ', 'ὁ', 'ὑ', 'ὠ', 'ὡ'],
  // Polytonic — uppercase breathings.
  ['Ἀ', 'Ἁ', 'Ἐ', 'Ἑ', 'Ἠ', 'Ἡ', 'Ἰ', 'Ἱ', 'Ὀ', 'Ὁ', 'Ὑ', 'Ὠ', 'Ὡ'],
  // Polytonic — lowercase acute (bare / smooth+acute / rough+acute per vowel).
  ['ά', 'ἄ', 'ἅ', 'έ', 'ἔ', 'ἕ', 'ή', 'ἤ', 'ἥ',
   'ί', 'ἴ', 'ἵ', 'ό', 'ὄ', 'ὅ', 'ύ', 'ὕ', 'ώ', 'ὤ', 'ὥ'],
  // Polytonic — lowercase grave (used at end of word before another).
  ['ὰ', 'ὲ', 'ὴ', 'ὶ', 'ὸ', 'ὺ', 'ὼ'],
  // Polytonic — lowercase circumflex (bare / smooth / rough per vowel).
  ['ᾶ', 'ἆ', 'ἇ', 'ῆ', 'ἦ', 'ἧ', 'ῖ', 'ἶ', 'ἷ', 'ῦ', 'ὗ', 'ῶ', 'ὦ', 'ὧ'],
  // Polytonic — iota subscript.
  ['ᾳ', 'ῃ', 'ῳ'],
  // Editorial / punctuation. The breve is a combining mark — display on a
  // dotted-circle base so the button is legible; insert just the combiner.
  ['ɔ', { display: '◌̆', insert: '̆' }, '—', '–', '…'],
];

const TAG_CHIP_MOD: Record<string, string> = { b: 'bold', u: 'ul', i: 'it' };
const chipClass = (tag: string) => {
  const mod = TAG_CHIP_MOD[tag];
  return mod ? `editor-chip editor-chip--${mod}` : 'editor-chip';
};

const toggleClass = (active: boolean) =>
  `editor-bottom__toggle${active ? ' editor-bottom__toggle--active' : ''}`;

function applyTag(view: EditorView, item: TagItem) {
  if      (item.kind === 'inline')  applyInlineFormat(view, item.tag);
  else if (item.kind === 'foreign') applyForeign(view);
  else                              applyLatinOut(view, item.tag);
}

function insertChar(view: EditorView, ch: string) {
  view.dispatch(view.state.replaceSelection(ch));
  view.focus();
}

// Interleave a thin vertical separator between groups.
function renderGroups<T>(
  groups: ReadonlyArray<ReadonlyArray<T>>,
  render: (item: T) => React.ReactNode,
): React.ReactNode {
  return groups.flatMap((group, gi) => [
    gi > 0 ? <span key={`sep-${gi}`} className="editor-bottom__panel-sep" role="separator" /> : null,
    ...group.map(render),
  ]);
}

export default function EditorBottom({ editorRef }: Props) {
  const [active, setActive] = useState<Panel | null>(null);

  // onMouseDown(preventDefault) keeps focus in the editor — without it the
  // button steals focus and the selection is lost before the dispatch.
  const click = (fn: () => void) => (e: React.MouseEvent) => {
    e.preventDefault();
    fn();
  };
  const withView = (fn: (v: EditorView) => void) => click(() => {
    const v = editorRef.current?.view;
    if (v) fn(v);
  });
  const toggle = (panel: Panel) => () => setActive((p) => (p === panel ? null : panel));

  return (
    <div className="editor-bottom">
      {active === 'tags' && (
        <div className="editor-bottom__panel">
          {renderGroups(TAG_GROUPS, (item) => (
            <button
              key={item.tag}
              type="button"
              className={chipClass(item.tag)}
              title={item.label}
              onMouseDown={withView((v) => applyTag(v, item))}
            >
              {item.tag}
            </button>
          ))}
        </div>
      )}
      {active === 'chars' && (
        <div className="editor-bottom__panel">
          {renderGroups(CHAR_GROUPS, (c) => (
            <button
              key={charInsert(c)}
              type="button"
              className="editor-chip editor-chip--char"
              onMouseDown={withView((v) => insertChar(v, charInsert(c)))}
            >
              {charDisplay(c)}
            </button>
          ))}
        </div>
      )}
      <div className="editor-bottom__bar" role="toolbar" aria-label="Verktygspanel">
        <button
          type="button"
          className={toggleClass(active === 'tags')}
          aria-pressed={active === 'tags'}
          onMouseDown={click(toggle('tags'))}
        >
          Taggar
        </button>
        <button
          type="button"
          className={toggleClass(active === 'chars')}
          aria-pressed={active === 'chars'}
          onMouseDown={click(toggle('chars'))}
        >
          Tecken
        </button>
      </div>
    </div>
  );
}
