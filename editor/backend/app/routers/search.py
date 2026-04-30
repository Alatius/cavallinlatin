"""Full-text search and exact lookup."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from ..deps import Conn
from ..models import EntrySummary, SearchHit, SearchOut, UrlIdOut
from ..text import fold


router = APIRouter()


# Markers wrapped around each match in FTS5 snippets. Control chars never
# appear in legitimate dictionary text, so the frontend can split on them
# without false positives. Using non-HTML markers means the snippet payload
# is plain text and the React layer can render <mark> via JSX rather than
# dangerouslySetInnerHTML.
_MARK_OPEN = '\x01'
_MARK_CLOSE = '\x02'


@router.get('/headwords', response_model=list[EntrySummary])
def all_headwords(conn: Conn):
    """Return every entry's url_id + headword + alt_headwords + type + status,
    in document order.

    Used by the virtualized index panel in the frontend. Keeping this compact:
    34,778 rows at ~80 bytes each gzip to ~400-600 KB, fetched once per session.
    """
    # LEFT JOIN against an aggregate so entries with zero comments still
    # appear (with comment_count=0). Group-by-rowid + indexed entry_id keeps
    # this a single index scan even with 35k entries.
    rows = conn.execute(
        'SELECT e.url_id, e.headword, e.alt_headwords, e.type, e.status, '
        '       COALESCE(c.n, 0) AS comment_count '
        'FROM entries e '
        'LEFT JOIN (SELECT entry_id, COUNT(*) AS n '
        '           FROM entry_comments GROUP BY entry_id) c '
        '       ON c.entry_id = e.id '
        'ORDER BY e.sort_key'
    ).fetchall()
    return [EntrySummary.from_row(r) for r in rows]


def _sanitize(q: str) -> str:
    # FTS5 query: treat user input as a simple prefix phrase; quote to escape.
    safe = q.replace('"', '').strip()
    if not safe:
        return ''
    return f'"{safe}"*'


@router.get('/search', response_model=SearchOut)
def search(
    conn: Conn,
    q: str = Query(default='', max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
):
    term = _sanitize(q)
    if not term:
        return SearchOut(query=q, total=0, items=[])

    rows = conn.execute(
        'SELECT e.url_id, e.headword, '
        '       snippet(entries_fts, 1, ?, ?, ?, 12) AS snippet '
        'FROM entries_fts '
        'JOIN entries e ON e.id = entries_fts.rowid '
        'WHERE entries_fts MATCH ? '
        'ORDER BY bm25(entries_fts, 10.0, 1.0) LIMIT ?',
        (_MARK_OPEN, _MARK_CLOSE, '…', term, limit),
    ).fetchall()

    total = conn.execute(
        'SELECT COUNT(*) AS n FROM entries_fts WHERE entries_fts MATCH ?',
        (term,),
    ).fetchone()['n']

    return SearchOut(
        query=q, total=total,
        items=[SearchHit(**dict(r)) for r in rows],
    )


@router.get('/lookup', response_model=UrlIdOut)
def lookup(conn: Conn, q: str = Query(min_length=1)):
    row = conn.execute(
        'SELECT url_id FROM entries WHERE headword_sort = ? '
        'ORDER BY sort_key LIMIT 1',
        (fold(q.strip()),),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return UrlIdOut(url_id=row['url_id'])


@router.get('/entry-at', response_model=UrlIdOut)
def entry_at(
    conn: Conn,
    # Four-digit zero-padding is required so lexicographic comparisons (used
    # in the SQL below to find the entry covering a column position) match
    # numeric ordering — '1-99' would otherwise sort > '1-100'. The frontend
    # always pads to 4 digits; this just enforces it on the wire.
    column: str = Query(pattern=r'^[12]-\d{4}$'),
    y: float = Query(ge=0, le=100),
):
    """Return the entry whose starting position is at or just before the
    given (column, y) — i.e., the entry visually covering that spot."""
    row = conn.execute(
        'SELECT url_id FROM entries '
        'WHERE starting_column IS NOT NULL '
        '  AND ('
        '    starting_column < ? '
        '    OR (starting_column = ? '
        '        AND (first_orth_y IS NULL OR first_orth_y <= ?))'
        '  ) '
        'ORDER BY sort_key DESC LIMIT 1',
        (column, column, y),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return UrlIdOut(url_id=row['url_id'])
