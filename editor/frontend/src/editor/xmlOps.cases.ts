// Behaviour spec for the tag-change operations in xmlOps.ts.
//
// Each case shows an `input` snippet and an `expected` snippet, with the
// user's selection delimited by `[` ... `]` (an empty selection / bare
// cursor is `[]`). The `apply` field names the tag the user clicks; every
// tag dispatches to the same tagOp(state, range, tag) regardless of whether
// it's an inline format (b/u/i), foreign, or a Latin-out content tag
// (orth, ref, form, pos, gen, subc, case, mood, tns, number, iType, gram,
// lbl, hom).
//
// === Unified algorithm ===
//
// For an inline-format target X (b/u/i) — nests freely:
//   1. If selection is within a same-tag X → unwrap.
//   2. Else if multiple X touch / span → merge zone.
//   3. Else → plain wrap (no-op for empty selection).
//
// For a content-tag target X (foreign or Latin-out):
//   1. If selection is within a single same-tag X → unwrap.
//   2. Else if X tags touch / span the selection → merge zone.
//   3. Else find content-tag ancestors. Pick the *kept* container C:
//      foreign if any ancestor is foreign, else the outermost ancestor.
//      Peel every other content-tag ancestor. Then split C around the
//      selection: wrap selection in X; wrap each side's content back in C,
//      with inline-format children (b/u/i) staying inside the C remnant
//      and other elements (br, etc.) staying bare between wrappers; edge-
//      trim the text segment at the selection seam (push non-letter chars
//      outside C); drop empty C remnants.
//   4. If no content-tag ancestor → plain wrap.

export type Case = {
  name: string;
  input: string;
  apply: string;
  expected: string;
  notes?: string;
};

export const cases: Case[] = [
  // ==========================================================================
  // A. Plain wrap — no content-tag ancestor wraps the selection.
  // ==========================================================================
  {
    name: 'A1. wrap a word in form',
    input: 'See [Apple] for details.',
    apply: 'form',
    expected: 'See <form>[Apple]</form> for details.',
  },
  {
    name: 'A2. wrap a word in foreign',
    input: 'see [apple] for details.',
    apply: 'foreign',
    expected: 'see <foreign>[apple]</foreign> for details.',
  },
  {
    name: 'A3. empty cursor, no ancestor → no-op',
    input: 'hello[] world',
    apply: 'form',
    expected: 'hello[] world',
  },
  {
    name: 'A4. wrap selection that touches an unrelated tag',
    input: '<b>bold</b> [tail]',
    apply: 'form',
    expected: '<b>bold</b> <form>[tail]</form>',
  },

  // ==========================================================================
  // B. Toggle off — snug selection inside the same tag.
  // ==========================================================================
  {
    name: 'B1. snug selection inside same tag → unwrap',
    input: '<form>[hello]</form>',
    apply: 'form',
    expected: '[hello]',
  },
  {
    name: 'B2. partial selection inside same tag → unwrap',
    input: '<form>he[ll]o</form>',
    apply: 'form',
    expected: 'he[ll]o',
    notes: 'unified rule: any selection contained within a same-tag X unwraps that X (snug or partial).',
  },
  {
    name: 'B3. empty cursor inside same tag → unwrap',
    input: '<form>he[]llo</form>',
    apply: 'form',
    expected: 'he[]llo',
    notes: 'same rule as B2 — empty cursor inside same-tag X also unwraps.',
  },

  // ==========================================================================
  // C. Same-tag merge — selection bridges adjacent same tags.
  // ==========================================================================
  {
    name: 'C1. selection spans two adjacent forms → merge into one',
    input: '<form>a[a</form><form>b]b</form>',
    apply: 'form',
    expected: '<form>[aabb]</form>',
  },
  {
    name: 'C2. empty cursor between two adjacent forms → merge',
    input: '<form>aa</form>[]<form>bb</form>',
    apply: 'form',
    expected: '<form>[aabb]</form>',
    notes: 'an empty cursor between adjacent same tags currently merges them. Keep, or no-op? Answer: either is okay. Keep merge is probably best.',
  },
  {
    name: 'C3. selection extends past one form into bare text',
    input: '<form>a[a</form> bb]',
    apply: 'form',
    expected: '<form>[aa bb]</form>',
    notes: 'merge zone expands to absorb the bare text into one form. OK? Answer: Perfect!',
  },
  {
    name: 'C4. three adjacent forms, selection snug in middle',
    input: '<form>a</form><form>[b]</form><form>c</form>',
    apply: 'form',
    expected: '<form>a</form>[b]<form>c</form>',
    notes: 'snug-unwrap (rule 1) wins over merge expansion (rule 2). Only the middle form unwraps; the adjacent ones survive.',
  },

  // ==========================================================================
  // D. Replace outermost — selection inside a different content tag.
  // ==========================================================================
  {
    name: 'D1. snug selection inside orth, click form → replace',
    input: '<orth>[hello]</orth>',
    apply: 'form',
    expected: '<form>[hello]</form>',
  },
  {
    name: 'D2. partial selection inside orth → extract',
    input: '<orth>he[ll]o</orth>',
    apply: 'form',
    expected: '<orth>he</orth><form>[ll]</form><orth>o</orth>',
    notes: 'CHANGED from current. Unified extract: orth splits into two remnants around the form, just as foreign does in F2. Previously this case replaced the whole orth (`<form>[hello]</form>`). The unified output keeps the orth fragments instead. If you prefer whole-orth replace for non-foreign content tags, we keep the foreign-vs-Latin-out asymmetry.',
  },
  {
    name: 'D3. selection inside orth with an inline-format sibling → extract',
    input: '<orth>he[ll]o <u>noun</u></orth>',
    apply: 'form',
    expected: '<orth>he</orth><form>[ll]</form><orth>o <u>noun</u></orth>',
    notes: 'changed example to <u> per your note (<pos> inside <orth> would be invalid). Inline-format <u> stays inside the trailing orth remnant. With selection literally `ll`, the surrounding text "o " stays inside the orth too (no edge-trim because `o` is a letter). If selection had been the whole word `hello`, the extract would yield `<form>[hello]</form> <orth><u>noun</u></orth>` — which matches what you wrote.',
  },

  // ==========================================================================
  // E. Inline format (b, u, i) — nests freely inside content tags.
  // ==========================================================================
  {
    name: 'E1. wrap selection in <b> inside a content tag (no peel)',
    input: '<form>al[ph]a</form>',
    apply: 'b',
    expected: '<form>al<b>[ph]</b>a</form>',
  },
  {
    name: 'E2. snug selection inside <b> → unwrap',
    input: 'a<b>[bold]</b>b',
    apply: 'b',
    expected: 'a[bold]b',
  },
  {
    name: 'E3. selection bridges adjacent <b><b> → merge',
    input: '<b>a[a</b><b>b]b</b>',
    apply: 'b',
    expected: '<b>[aabb]</b>',
  },
  {
    name: 'E4. inline format on empty cursor → no-op',
    input: 'al[]pha',
    apply: 'b',
    expected: 'al[]pha',
  },

  // ==========================================================================
  // F. Foreign extract — basic (no edge punctuation, no children).
  // ==========================================================================
  {
    name: 'F1. snug select inside foreign, apply form → foreign disappears',
    input: '<foreign>[apple]</foreign>',
    apply: 'form',
    expected: '<form>[apple]</form>',
  },
  {
    name: 'F2. select first word, rest stays foreign',
    input: '<foreign>[cat] dog</foreign>',
    apply: 'form',
    expected: '<form>[cat]</form> <foreign>dog</foreign>',
  },
  {
    name: 'F3. select last word',
    input: '<foreign>cat [dog]</foreign>',
    apply: 'form',
    expected: '<foreign>cat</foreign> <form>[dog]</form>',
  },
  {
    name: 'F4. select middle word',
    input: '<foreign>a [b] c</foreign>',
    apply: 'form',
    expected: '<foreign>a</foreign> <form>[b]</form> <foreign>c</foreign>',
  },

  // ==========================================================================
  // G. Foreign extract — punctuation edges (paren / hyphen / period).
  // ==========================================================================
  {
    name: 'G1. select word inside foreign with comma + space',
    input: '<foreign>([apple], orange)</foreign>',
    apply: 'form',
    expected: '(<form>[apple]</form>, <foreign>orange</foreign>)',
    notes: 'parens stay outside the foreign because each side trims its outer non-letters.',
  },
  {
    name: 'G2. select word with trailing period',
    input: '<foreign>[Aulus].</foreign>',
    apply: 'form',
    expected: '<form>[Aulus]</form>.',
    notes: 'trailing period after a single letter+letters word: pushed out. Or should the period stay inside form?',
  },
  {
    name: 'G3. select word with hyphen prefix',
    input: '<foreign>pre [-fix]</foreign>',
    apply: 'form',
    expected: '<foreign>pre</foreign> <form>[-fix]</form>',
    notes: 'hyphen sticks to letters on either side. Selecting "-fix" keeps the hyphen with form.',
  },
  {
    name: 'G4. select word with hyphenated continuation',
    input: '<foreign>[ab-]</foreign>',
    apply: 'form',
    expected: '<form>[ab-]</form>',
    notes: 'standalone foreign with trailing hyphen: hyphen stays with the new form.',
  },
  {
    name: 'G5. select balanced parenthesised word',
    input: '<foreign>x [(y)]</foreign>',
    apply: 'form',
    expected: '<foreign>x</foreign> <form>[(y)]</form>',
    notes: 'when selection itself contains balanced parens, no edge trimming needed.',
  },

  // ==========================================================================
  // H. Foreign extract — with child elements (the recently fixed bug).
  // ==========================================================================
  {
    name: 'H1. <foreign>a<br/>b</foreign> select a → br stays outside',
    input: '<foreign>[a]<br/>b</foreign>',
    apply: 'form',
    expected: '<form>[a]</form><br/><foreign>b</foreign>',
  },
  {
    name: 'H2. <foreign>a<br/>b</foreign> select b → br stays outside',
    input: '<foreign>a<br/>[b]</foreign>',
    apply: 'form',
    expected: '<foreign>a</foreign><br/><form>[b]</form>',
  },
  {
    name: 'H3. selection spans the <br/>',
    input: '<foreign>x [a<br/>b] y</foreign>',
    apply: 'form',
    expected: '<foreign>x</foreign> <form>[a<br/>b]</form> <foreign>y</foreign>',
    notes: 'middle wrap contains the br as-is. Or should br be excluded from the form?',
  },
  {
    name: 'H4. <foreign>x<u>y</u>z</foreign> select x → u stays inside remnant foreign',
    input: '<foreign>[x]<u>y</u>z</foreign>',
    apply: 'form',
    expected: '<form>[x]</form><foreign><u>y</u>z</foreign>',
    notes: 'inline-format children stay inside the C remnant. Confirmed in data: <foreign><u>...</u></foreign> is a real pattern.',
  },
  {
    name: 'H5. <foreign><ref>x</ref></foreign> select x → peel through corrupt nesting',
    input: '<foreign><ref>[x]</ref></foreign>',
    apply: 'form',
    expected: '<form>[x]</form>',
    notes: 'corruptly nested content tags both get resolved. Foreign is the kept C, ref is peeled, then the snug selection drops the empty foreign remnant.',
  },

  // ==========================================================================
  // I. Foreign nested in another content tag (corruptly nested).
  // ==========================================================================
  {
    name: 'I1. <orth><foreign>x</foreign></orth> select x, apply form → peel orth',
    input: '<orth><foreign>[x]</foreign></orth>',
    apply: 'form',
    expected: '<form>[x]</form>',
    notes: 'orth is peeled because it wraps the foreign-extract result.',
  },
  {
    name: 'I2. <orth><foreign>cat dog</foreign></orth> select cat → form replaces, foreign survives, orth peels',
    input: '<orth><foreign>[cat] dog</foreign></orth>',
    apply: 'form',
    expected: '<form>[cat]</form> <foreign>dog</foreign>',
  },

  // ==========================================================================
  // J. Edge cases.
  // ==========================================================================
  {
    name: 'J1. apply foreign on selection already inside foreign and snug → unwrap',
    input: '<foreign>[hello]</foreign>',
    apply: 'foreign',
    expected: '[hello]',
  },
  {
    name: 'J2. apply foreign on selection inside foreign but not snug → unwrap',
    input: '<foreign>he[ll]o</foreign>',
    apply: 'foreign',
    expected: 'he[ll]o',
    notes: 'same as B2 — any selection inside a same-tag X unwraps that X.',
  },
  {
    name: 'J3. selection at exact tag boundary (just outside)',
    input: '<form>a</form>[bb]',
    apply: 'form',
    expected: '<form>[abb]</form>',
    notes: 'merge zone absorbs the adjacent bare selection into the existing form.',
  },
  {
    name: 'J4. selection across two non-adjacent foreigns with text between',
    input: '<foreign>a[a</foreign> mid <foreign>b]b</foreign>',
    apply: 'foreign',
    expected: '<foreign>[aa mid bb]</foreign>',
    notes: 'merge across non-adjacent same tags absorbs the text in the middle. Desired? Answer: Of course!',
  },
];
