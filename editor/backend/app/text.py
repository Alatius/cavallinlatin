"""Shared text helpers."""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lxml.etree import _Element


def fold(s: str) -> str:
    """Lowercase and strip combining marks, so 'Ăbăvus' folds to 'abavus'."""
    return ''.join(
        c for c in unicodedata.normalize('NFKD', s)
        if not unicodedata.combining(c)
    ).lower()


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
