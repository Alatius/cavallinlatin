"""Entry list, fetch, and save."""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, HTTPException, Query, status
from lxml import etree

from .. import config, db, security
from ..deps import Conn, CurrentUser, Editor
from ..models import (
    ENTRY_TYPES, EntryList, EntryOut, EntrySaveIn, EntrySummary, LockInfo,
)
from ..text import column_markers, first_orth_y, fold, orth_texts
from ..xml_parsing import SAFE_XML_PARSER


router = APIRouter()


def _entry_response(url_id: str, conn: sqlite3.Connection, user: sqlite3.Row | None) -> EntryOut:
    # Correlated subqueries on the indexed sort_key give us prev/next in a
    # single round-trip; the planner still does index lookups, not scans.
    row = conn.execute(
        'SELECT e.*, u.display_name AS lock_display_name, '
        '       (SELECT url_id FROM entries '
        '        WHERE sort_key < e.sort_key '
        '        ORDER BY sort_key DESC LIMIT 1) AS prev_url_id, '
        '       (SELECT url_id FROM entries '
        '        WHERE sort_key > e.sort_key '
        '        ORDER BY sort_key ASC LIMIT 1) AS next_url_id '
        'FROM entries e LEFT JOIN users u ON u.id = e.lock_user_id '
        'WHERE e.url_id = ?',
        (url_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    lock = None
    if (user and row['lock_user_id'] and row['lock_expires_at']
            and row['lock_expires_at'] > security.now()):
        lock = LockInfo(
            user_id=row['lock_user_id'],
            display_name=row['lock_display_name'] or '',
            expires_at=row['lock_expires_at'],
        )

    return EntryOut(
        url_id=row['url_id'], xml_id=row['xml_id'], xml_root=row['xml_root'],
        type=row['type'], headword=row['headword'],
        alt_headwords=json.loads(row['alt_headwords'] or '[]'),
        status=row['status'], xml_body=row['xml_body'],
        starting_column=row['starting_column'],
        prev_url_id=row['prev_url_id'],
        next_url_id=row['next_url_id'],
        updated_at=row['updated_at'], lock=lock,
    )


@router.get('', response_model=EntryList)
def list_entries(
    conn: Conn,
    q: str = Query(default=''),
    status_filter: str | None = Query(default=None, alias='status'),
    order: str = Query(default='document', pattern='^(document|alpha)$'),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    clauses: list[str] = []
    params: list = []
    if q:
        clauses.append('headword_sort LIKE ?')
        params.append(f'{fold(q)}%')
    if status_filter:
        clauses.append('status = ?')
        params.append(status_filter)
    where = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
    order_sql = 'sort_key' if order == 'document' else 'headword_sort, sort_key'

    total = conn.execute(
        f'SELECT COUNT(*) AS n FROM entries {where}', params
    ).fetchone()['n']
    rows = conn.execute(
        f'SELECT url_id, headword, alt_headwords, type, status FROM entries {where} '
        f'ORDER BY {order_sql} LIMIT ? OFFSET ?',
        (*params, limit, offset),
    ).fetchall()
    return EntryList(
        total=total, offset=offset, limit=limit,
        items=[EntrySummary.from_row(r) for r in rows],
    )


@router.get('/{url_id}', response_model=EntryOut)
def get_entry(url_id: str, conn: Conn, user: CurrentUser):
    return _entry_response(url_id, conn, user)


@router.put('/{url_id}', response_model=EntryOut)
def save_entry(url_id: str, data: EntrySaveIn, conn: Conn, user: Editor):
    # Validate the XML body up front so a malformed payload doesn't hold the
    # write lock that the transaction below acquires.
    try:
        el = etree.fromstring(data.xml_body.encode('utf-8'), SAFE_XML_PARSER)
    except etree.XMLSyntaxError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f'Felaktig XML: {e}') from None
    if el.tag != 'entry':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Rotelementet måste vara <entry>')
    entry_type = el.get('type') or 'plain'
    if entry_type not in ENTRY_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f'Okänd posttyp {entry_type!r}; väntade en av {sorted(ENTRY_TYPES)}',
        )
    # Import skips entries without <orth>, so the editor shouldn't be able
    # to save into that state either — without an orth there's no headword,
    # no sort key derivation, and no FTS index target.
    if el.find('.//orth') is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'Posten måste innehålla minst ett <orth>-element',
        )

    orths = orth_texts(el)
    headword = orths[0] if orths else url_id
    alt_headwords_json = json.dumps(orths[1:], ensure_ascii=False)
    headword_sort = fold(headword)
    first_y = first_orth_y(el)
    leading_cb, _ = column_markers(el)
    plaintext = ' '.join(''.join(el.itertext()).split())
    xml_root = el.get('root')
    xml_id = el.get('id')

    now = security.now()

    # Read-check-write under a single write transaction so concurrent saves
    # can't race past the lock check or interleave the revision insert with
    # the entry update.
    with db.transaction(conn):
        row = conn.execute(
            'SELECT id, lock_user_id, lock_expires_at, starting_column, '
            'xml_body, status, updated_at FROM entries WHERE url_id = ?',
            (url_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        if (row['lock_user_id'] and row['lock_user_id'] != user['user_id']
                and row['lock_expires_at'] and row['lock_expires_at'] > now):
            raise HTTPException(status.HTTP_409_CONFLICT, 'Låst av en annan redigerare')

        # Optimistic concurrency: if the client supplied the updated_at it
        # last saw and the row has moved on, refuse the save so a stale draft
        # can't silently clobber a newer version. This is the failsafe for
        # the case where both editors' soft locks lapsed between saves.
        if (data.expected_updated_at is not None
                and data.expected_updated_at != row['updated_at']):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                'Posten har ändrats sedan du laddade den; ladda om för att se '
                'den senaste versionen.',
            )

        # Auto-advance from untouched on first save: the editor opened and
        # saved this entry, so by definition it's no longer untouched. Keep
        # the rule on the server so the UI doesn't have to know about it.
        new_status = data.status
        if row['status'] == 'untouched' and new_status == 'untouched':
            new_status = 'in_progress'

        # No-op save (no XML/status change): return current state unchanged.
        if data.xml_body == row['xml_body'] and new_status == row['status']:
            pass
        else:
            # If no <cb/> precedes the first <orth>, keep the stored
            # starting_column — it was set during import from the running-
            # column state, which we can't recompute from a single entry.
            starting_column = leading_cb or row['starting_column']

            conn.execute(
                'INSERT INTO entry_revisions (entry_id, xml_body, status, user_id, created_at) '
                'SELECT id, xml_body, status, ?, ? FROM entries WHERE id = ?',
                (user['user_id'], now, row['id']),
            )
            conn.execute(
                'UPDATE entries SET xml_body = ?, plaintext = ?, headword = ?, '
                'headword_sort = ?, alt_headwords = ?, starting_column = ?, '
                'first_orth_y = ?, type = ?, xml_id = ?, xml_root = ?, status = ?, '
                'updated_at = ?, lock_user_id = ?, lock_expires_at = ? '
                'WHERE id = ?',
                (data.xml_body, plaintext, headword, headword_sort, alt_headwords_json,
                 starting_column, first_y, entry_type, xml_id, xml_root, new_status,
                 now, user['user_id'], now + config.LOCK_TTL_SECONDS, row['id']),
            )

    return _entry_response(url_id, conn, user)
