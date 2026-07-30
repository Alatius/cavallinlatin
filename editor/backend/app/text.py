"""Shared text helpers."""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING, NamedTuple

from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import _Element


class DerivedFields(NamedTuple):
    """Cached scalar columns recomputed from an <entry> element. Save,
    split and join all need the same set of values; centralizing them
    here keeps the three paths in sync."""
    headword: str
    alt_headwords: list[str]
    headword_sort: str
    plaintext: str
    first_orth_y: float | None
    leading_cb: str | None


def fold(s: str) -> str:
    """Canonicalize for search/sort. Mirrors the TS fold() in
    HeadwordsContext.tsx: drops macrons, breves, and ordinary diaereses
    (so 'coepi' matches 'coëpi') but keeps the Swedish vowels ä, ö, å
    distinct (so 'bar' doesn't match 'bär'). Then folds w↔v, ß↔ss,
    æ↔ae and œ↔oe — orthographic equivalents in the dictionary.
    The ä/ö/å stash trick mirrors the TS implementation: park them in
    PUA codepoints across the NFKD step, then restore."""
    pre = (
        unicodedata.normalize('NFC', s.lower())
        .replace('ä', '\uE000')
        .replace('ö', '\uE001')
        .replace('å', '\uE002')
    )
    stripped = ''.join(
        c for c in unicodedata.normalize('NFKD', pre)
        if not unicodedata.combining(c)
    )
    return (
        stripped
        .replace('\uE000', 'ä')
        .replace('\uE001', 'ö')
        .replace('\uE002', 'å')
        .replace('w', 'v')
        .replace('ß', 'ss')
        .replace('æ', 'ae')
        .replace('œ', 'oe')
    )


def orth_texts(entry: '_Element') -> list[str]:
    """Headword strings of every <orth> in an entry, in document order.

    Duplicates (exact string match) are collapsed, keeping the first — a
    handful of entries repeat the same headword in both boldface and
    unaccented forms, and the index shouldn't show them twice.
    """
    seen: set[str] = set()
    out: list[str] = []
    for o in entry.findall('.//orth'):
        t = ''.join(o.itertext()).strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def first_orth_y(entry: '_Element') -> float | None:
    """Vertical position of the first <orth> in the column (0–100), or None."""
    first = entry.find('.//orth')
    if first is None:
        return None
    y = first.get('y')
    try:
        return float(y) if y else None
    except ValueError:
        return None


def derive_xml_id_base(orth_text: str) -> str:
    """Normalize a headword (an <orth>'s text content) to xml-id form.

    Used when splitting an entry: the new entry's xml_id is derived from
    the first <orth> in its content, dropping diacritics and non-letter
    characters. Returns '' if there's nothing usable (caller refuses the
    split in that case).
    """
    return ''.join(c for c in fold(orth_text) if 'a' <= c <= 'z')


def canonical_entry_xml(el: '_Element') -> str:
    """Serialize an <entry> element to the one form the database stores.

    Save used to persist the client's string verbatim, which let stored bodies
    drift from the shape every other consumer assumes. Leading whitespace or an
    XML prologue made `_entry_inner_bounds` fail, so split/join answered 500
    forever after and `export_xml`'s concatenation stopped being re-importable;
    a raw '>' inside a root attribute (legal XML) made the open-tag regex stop
    early and join silently spliced markup into the text; single-quoted
    attributes were dropped by the renderer; a CDATA section carried raw markup
    through to the public page. Serializing from the parsed tree makes every
    one of those unrepresentable — lxml emits double-quoted attributes with
    '>' escaped, and folds CDATA into ordinary escaped text.

    Verified against the existing corpus: byte-identical for all but 2 of
    34,775 entries (jus1, jurisconsultus), which differ only by the trailing-
    whitespace squeeze below and get normalized on their next save. Adopting
    this does not otherwise rewrite stored entries.
    """
    xml = etree.tostring(el, encoding='unicode', with_tail=False)
    # Match import_xml, which squeezes whitespace before the close tag.
    return re.sub(r'\s+</entry>$', '</entry>', xml)


def derive_entry_fields(el: '_Element', *, headword_fallback: str) -> DerivedFields:
    orths = orth_texts(el)
    headword = orths[0] if orths else headword_fallback
    return DerivedFields(
        headword=headword,
        alt_headwords=orths[1:],
        headword_sort=fold(headword),
        plaintext=' '.join(''.join(el.itertext()).split()),
        first_orth_y=first_orth_y(el),
        leading_cb=column_markers(el)[0],
    )


def column_markers(entry: '_Element') -> tuple[str | None, str | None]:
    """(leading, trailing) column refs from <cb n="..."/> tags in an entry.

    - leading: the last <cb/> that appears *before* the first <orth>, which
      is what defines the entry's starting column. None if no <cb/> appears
      before the first orth.
    - trailing: the last <cb/> anywhere in the entry, which defines the
      running column state for the next entry during a bulk import.
    """
    leading: str | None = None
    trailing: str | None = None
    first_orth_seen = False
    for el in entry.iter():
        if el is entry:
            continue
        if el.tag == 'cb':
            n = el.get('n')
            if n:
                trailing = n
                if not first_orth_seen:
                    leading = n
        elif el.tag == 'orth':
            first_orth_seen = True
    return leading, trailing
