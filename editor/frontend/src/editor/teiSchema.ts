import type { ElementSpec, AttrSpec } from '@codemirror/lang-xml';

// Elements that hold inline content (formatting + grammar tags + cross-refs)
// and may appear inside `entry`, `sense`, `orth`, `foreign`, `ref`, etc.
// Listed once and reused so the schema stays in sync with itself.
// `cb` (column break) can fall anywhere in the flow, so it's allowed here too.
const INLINE: readonly string[] = [
  'b', 'u', 'i', 'foreign', 'ref', 'br', 'cb',
  'orth', 'form', 'pos', 'gen', 'subc', 'case', 'mood', 'tns',
  'number', 'iType', 'gram', 'lbl', 'hom',
];

// What can sit directly inside `entry` / `sense`. Adds `sense` itself
// (senses nest); `cb` is already in INLINE.
const BLOCK: readonly string[] = [...INLINE, 'sense'];

// Single-word grammar-label content suggestions. Mined from
// proofread/make_lexicon.py LABEL_TO_TEI by inverting the mapping. These are
// offered as plaintext completions when the cursor is at the start of an
// empty grammar element, e.g. typing inside `<pos>|</pos>` proposes `A.`,
// `Adj.`, … . Kept conservative — high-frequency, unambiguous values only.
const POS_VALUES = [
  'A.', 'Adj.', 'Adv.', 'Subst.', 'Præp.', 'Conj.', 'Interj.',
  'Pron.', 'Num.', 'Pron. indef.', 'Pron. relat.', 'Pron. interrog.',
  'Pron. demonstr.', 'V. impers.',
];
const GEN_VALUES   = ['m.', 'f.', 'n.', 'c.', 'comm.'];
const CASE_VALUES  = ['nom.', 'acc.', 'gen.', 'dat.', 'abl.', 'voc.', 'loc.'];
const MOOD_VALUES  = ['ind.', 'conj.', 'imper.', 'inf.', 'subj.', 'indic.'];
const TNS_VALUES   = ['pr.', 'præs.', 'pf.', 'perf.', 'impf.', 'fut.', 'plusqpf.', 'sup.'];
const NUMBER_VALUES = ['sing.', 'pl.', 'plur.'];
const SUBC_VALUES  = [
  'Dep.', 'Frequ.', 'Inch.', 'Intens.', 'Desid.', 'Dem.', 'Demin.',
  'trans.', 'intr.', 'pass.', 'act.', 'refl.', 'impers.',
];

const inline = (name: string, textContent?: readonly string[]): ElementSpec =>
  ({ name, children: INLINE, ...(textContent ? { textContent } : {}) });

export const TEI_ELEMENTS: readonly ElementSpec[] = [
  // Top-level entry
  {
    name: 'entry',
    top: true,
    children: BLOCK,
    attributes: [
      { name: 'id' },
      { name: 'root' },
      {
        name: 'type',
        values: ['primary', 'derived', 'reference', 'proper', 'plain'],
      },
    ],
  },

  // Block-ish containers
  {
    name: 'sense',
    children: BLOCK,
    attributes: [{ name: 'n' }, { name: 'y' }],
  },

  // Headword & inflection wrapper — primarily contains text + bold/underline.
  // Allows `cb` because column breaks occasionally fall mid-headword.
  {
    name: 'orth',
    children: ['b', 'u', 'i', 'cb'],
    attributes: [{ name: 'y' }],
  },

  // Self-closing structural marks (no children, but XML allows empty content)
  { name: 'cb', children: [], attributes: [{ name: 'n' }] },
  { name: 'br', children: [] },

  // Cross-reference: text + light formatting inside, `target` attribute
  {
    name: 'ref',
    children: ['b', 'u', 'i', 'cb'],
    attributes: [{ name: 'target' }],
  },

  // Etymology marker — single attribute with one known value
  {
    name: 'gram',
    children: INLINE,
    attributes: [{ name: 'type', values: ['etym'] }],
  },

  // Inline formatting
  inline('foreign'),
  inline('b'),
  inline('u'),
  inline('i'),

  // Inline grammar labels — suggest typical contents
  inline('pos',    POS_VALUES),
  inline('gen',    GEN_VALUES),
  inline('case',   CASE_VALUES),
  inline('mood',   MOOD_VALUES),
  inline('tns',    TNS_VALUES),
  inline('number', NUMBER_VALUES),
  inline('subc',   SUBC_VALUES),
  inline('iType'),
  inline('lbl'),
  inline('hom'),
  inline('form'),
];

export const TEI_ATTRS: readonly AttrSpec[] = [];
