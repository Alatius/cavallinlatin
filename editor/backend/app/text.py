"""Shared text helpers."""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lxml.etree import _Element


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
