"""Entry list, fetch, save, split, and join."""

from __future__ import annotations

import json
import re
import sqlite3
from html import escape as html_escape

from fastapi import APIRouter, HTTPException, Query, status
from lxml import etree

from .. import config, db, security
from ..deps import Conn, CurrentUser, Editor
from ..models import (
    ENTRY_TYPES, EntryGroupItem, EntryGroupOut, EntryJoinIn, EntryList,
    EntryOut, EntrySaveIn, EntrySplitIn, EntrySplitOut, EntrySummary,
    LockInfo, RevisionContent, RevisionMeta,
)
from ..text import (
    DerivedFields, canonical_entry_xml, derive_entry_fields, derive_xml_id_base,
    fold, orth_texts,
)
from ..xml_parsing import SAFE_XML_PARSER


# Matches the opening tag of the root <entry> element in a saved xml_body.
# xml_body is always canonically serialized (see canonical_entry_xml), so an
# anchored regex is sufficient and lxml has escaped any '>' in an attribute
# value. The alternation skips over quoted values anyway, so this stays
# correct even if a body somehow predates that guarantee — a bare [^>]*
# stopped at the wrong '>' and made join splice markup into the text.
_ENTRY_OPEN_RE = re.compile(r'<entry\b(?:[^>"\']|"[^"]*"|\'[^\']*\')*>')
_ENTRY_CLOSE = '</entry>'


router = APIRouter()


def _like_prefix(s: str) -> str:
    """Build a LIKE prefix pattern that matches `s` literally.

    Used with ESCAPE '\\'; the backslash itself must be escaped first so it
    can't neutralise a following wildcard escape.
    """
    for ch in ('\\', '%', '_'):
        s = s.replace(ch, '\\' + ch)
    return s + '%'


def _parse_safe(xml: str, msg: str) -> 'etree._Element':
    try:
        return etree.fromstring(xml.encode('utf-8'), SAFE_XML_PARSER)
    except etree.XMLSyntaxError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f'{msg}: {e}') from None


def _ensure_lock_free_for(row: sqlite3.Row, user_id: int, now: int, msg: str) -> None:
    """409 if `row` is locked by someone other than `user_id`."""
    if (row['lock_user_id'] and row['lock_user_id'] != user_id
            and row['lock_expires_at'] and row['lock_expires_at'] > now):
        raise HTTPException(status.HTTP_409_CONFLICT, msg)


def _snapshot_entry(conn: sqlite3.Connection, entry_id: int, user_id: int, now: int) -> None:
    """Copy the current xml_body/status of an entry into entry_revisions,
    attributing the overwrite to `user_id`. Call this immediately before
    any UPDATE that replaces xml_body or status."""
    conn.execute(
        'INSERT INTO entry_revisions (entry_id, xml_body, status, user_id, created_at) '
        'SELECT id, xml_body, status, ?, ? FROM entries WHERE id = ?',
        (user_id, now, entry_id),
    )


def _ensure_unchanged(row: sqlite3.Row, expected_updated_at: int | None) -> None:
    """409 if the row moved on since the client last read it.

    Optional so admin tooling and tests can opt out, matching save_entry.
    """
    if expected_updated_at is not None and expected_updated_at != row['updated_at']:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            'Posten har ändrats sedan du laddade den; ladda om för att se '
            'den senaste versionen.',
        )


def _bump_status(current: str, requested: str) -> str:
    """An edit means the entry is no longer untouched.

    Only bumps when the caller isn't asking for something specific, so an
    explicit downgrade from approved back to untouched still works.
    """
    if current == 'untouched' and requested == 'untouched':
        return 'in_progress'
    return requested


def _write_entry_fields(
    conn: sqlite3.Connection, entry_id: int, *,
    xml_body: str, fields: DerivedFields, entry_type: str,
    xml_id: str | None, xml_root: str | None,
    starting_column: str | None, status: str,
    now: int, user_id: int,
) -> None:
    """Write an entry's body together with every column derived from it.

    Save, split and join each used to hand-write their own UPDATE over a
    different subset of these columns, and the differences were accidental
    rather than intended: join never touched type/xml_id/xml_root/
    starting_column/first_orth_y, split never touched type or status, and
    only save applied the untouched->in_progress bump — so an entry
    reorganised by split or join stayed "untouched" and the work was
    invisible to the status filter and the progress view. One writer keeps
    the three paths in sync by construction.

    Also refreshes the caller's lock: every path through here is an edit the
    user just made, so they should keep holding it.
    """
    conn.execute(
        'UPDATE entries SET xml_body = ?, plaintext = ?, headword = ?, '
        'headword_sort = ?, alt_headwords = ?, starting_column = ?, '
        'first_orth_y = ?, type = ?, xml_id = ?, xml_root = ?, status = ?, '
        'updated_at = ?, lock_user_id = ?, lock_expires_at = ? '
        'WHERE id = ?',
        (xml_body, fields.plaintext, fields.headword, fields.headword_sort,
         json.dumps(fields.alt_headwords, ensure_ascii=False),
         starting_column, fields.first_orth_y, entry_type, xml_id, xml_root,
         status, now, user_id, now + config.LOCK_TTL_SECONDS, entry_id),
    )


def _next_free_url_id(conn: sqlite3.Connection, base: str) -> str:
    """Pick a free id starting from `base`. If `base` itself is unused (as
    either url_id or xml_id), return it; otherwise bump base1, base2, …
    until one is free. We check both columns because import sets
    url_id == xml_id for entries with an id, and we want the same shape
    for newly-split entries."""
    candidate = base
    n = 1
    while conn.execute(
        'SELECT 1 FROM entries WHERE url_id = ? OR xml_id = ? LIMIT 1',
        (candidate, candidate),
    ).fetchone():
        candidate = f'{base}{n}'
        n += 1
    return candidate


def _entry_inner_bounds(xml_body: str) -> tuple[int, int]:
    """(start, end) char offsets of the entry's *inner* content within its
    serialized xml_body, i.e. just after `<entry …>` and just before
    `</entry>`. Assumes xml_body is tightly serialized (no leading
    whitespace or PIs), which lxml's tostring guarantees."""
    m = _ENTRY_OPEN_RE.match(xml_body)
    if not m:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            'Sparad XML saknar inledande <entry>-tagg',
        )
    if not xml_body.endswith(_ENTRY_CLOSE):
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            'Sparad XML saknar avslutande </entry>',
        )
    return m.end(), len(xml_body) - len(_ENTRY_CLOSE)


def _entry_response(url_id: str, conn: sqlite3.Connection, user: sqlite3.Row | None) -> EntryOut:
    # Correlated subqueries on the indexed sort_key give us prev/next in a
    # single round-trip; the planner still does index lookups, not scans.
    # root_headword's LIMIT 1 is defensive: xml_id has no UNIQUE constraint
    # so a duplicate (shouldn't happen) wouldn't blow up the row scalar.
    row = conn.execute(
        'SELECT e.*, u.display_name AS lock_display_name, '
        '       (SELECT url_id FROM entries '
        '        WHERE sort_key < e.sort_key '
        '        ORDER BY sort_key DESC LIMIT 1) AS prev_url_id, '
        '       (SELECT url_id FROM entries '
        '        WHERE sort_key > e.sort_key '
        '        ORDER BY sort_key ASC LIMIT 1) AS next_url_id, '
        '       (SELECT headword FROM entries '
        '        WHERE xml_id = e.xml_root LIMIT 1) AS root_headword, '
        '       (SELECT url_id FROM entries '
        '        WHERE xml_id = e.xml_root LIMIT 1) AS root_url_id '
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
        root_headword=row['root_headword'],
        root_url_id=row['root_url_id'],
    )


@router.get('', response_model=EntryList)
def list_entries(
    conn: Conn,
    q: str = Query(default='', max_length=100),
    status_filter: str | None = Query(default=None, alias='status'),
    order: str = Query(default='document', pattern='^(document|alpha)$'),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    clauses: list[str] = []
    params: list = []
    if q:
        # ESCAPE so a literal % or _ in the query is matched as itself rather
        # than as a LIKE wildcard (?q=% would otherwise return every entry).
        clauses.append("headword_sort LIKE ? ESCAPE '\\'")
        params.append(_like_prefix(fold(q)))
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


@router.get('/{url_id}/group', response_model=EntryGroupOut)
def get_entry_group(url_id: str, conn: Conn):
    """Return the etymological group containing url_id: the head (primary or
    proper) plus all entries with the same xml_root, in document order. For
    entries that don't belong to a group (references, isolated plain entries,
    primaries with no derivatives) returns just the focus entry.
    """
    focus = conn.execute(
        'SELECT type, xml_id, xml_root FROM entries WHERE url_id = ?',
        (url_id,),
    ).fetchone()
    if not focus:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    if focus['type'] in ('primary', 'proper') and focus['xml_id']:
        root_xml_id = focus['xml_id']
    elif focus['xml_root']:
        root_xml_id = focus['xml_root']
    else:
        root_xml_id = None

    if root_xml_id is None:
        rows = conn.execute(
            'SELECT url_id, xml_id, xml_root, type, headword, alt_headwords, '
            'status, xml_body, starting_column FROM entries WHERE url_id = ?',
            (url_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT url_id, xml_id, xml_root, type, headword, alt_headwords, '
            'status, xml_body, starting_column FROM entries '
            'WHERE xml_id = ? OR xml_root = ? '
            'ORDER BY sort_key',
            (root_xml_id, root_xml_id),
        ).fetchall()

    items = [EntryGroupItem.from_row(r) for r in rows]

    # The head is items[0] iff it's a primary/proper. For orphan derivatives
    # (root pointing to a missing entry) and pure singletons (reference, plain
    # without root) head_url_id stays None — the breadcrumb suppresses itself.
    head_url_id = (
        items[0].url_id
        if items and items[0].type in ('primary', 'proper')
        else None
    )

    return EntryGroupOut(
        focus_url_id=url_id, head_url_id=head_url_id, items=items,
    )


def _build_snapshots(
    conn: sqlite3.Connection, url_id: str, *, with_body: bool,
) -> list[dict]:
    """Snapshots in ASC order, current last. Authorship of snapshot k comes
    from the row created by save k+1 — entry_revisions stores overwritten
    content alongside the user who did the overwriting, not the author of
    the content itself."""
    body_e = ', xml_body' if with_body else ''
    entry = conn.execute(
        f'SELECT id, status, updated_at, created_at{body_e} '
        'FROM entries WHERE url_id = ?',
        (url_id,),
    ).fetchone()
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    body_r = ', r.xml_body' if with_body else ''
    rows = conn.execute(
        f'SELECT r.id, r.status, r.user_id, r.created_at, u.display_name{body_r} '
        'FROM entry_revisions r LEFT JOIN users u ON u.id = r.user_id '
        'WHERE r.entry_id = ? ORDER BY r.created_at ASC, r.id ASC',
        (entry['id'],),
    ).fetchall()

    snaps: list[dict] = []
    for i, row in enumerate(rows):
        if i == 0:
            saved_at: int = entry['created_at']
            saved_by_id: int | None = None
            saved_by: str | None = None
        else:
            prev = rows[i - 1]
            saved_at = prev['created_at']
            saved_by_id = prev['user_id']
            saved_by = prev['display_name']
        snap = {
            'id': str(row['id']), 'is_current': False,
            'status': row['status'],
            'saved_at': saved_at, 'saved_by_id': saved_by_id,
            'saved_by': saved_by,
        }
        if with_body:
            snap['xml_body'] = row['xml_body']
        snaps.append(snap)

    if rows:
        last = rows[-1]
        cur_saved_at: int = last['created_at']
        cur_saved_by_id: int | None = last['user_id']
        cur_saved_by: str | None = last['display_name']
    else:
        cur_saved_at = entry['updated_at']
        cur_saved_by_id = None
        cur_saved_by = None
    cur = {
        'id': 'current', 'is_current': True,
        'status': entry['status'],
        'saved_at': cur_saved_at, 'saved_by_id': cur_saved_by_id,
        'saved_by': cur_saved_by,
    }
    if with_body:
        cur['xml_body'] = entry['xml_body']
    snaps.append(cur)
    return snaps


@router.get('/{url_id}/revisions', response_model=list[RevisionMeta])
def list_revisions(url_id: str, conn: Conn, _: Editor):
    snaps = _build_snapshots(conn, url_id, with_body=False)
    snaps.reverse()
    return [RevisionMeta(**s) for s in snaps]


@router.get('/{url_id}/revisions/{rev_id}', response_model=RevisionContent)
def get_revision(url_id: str, rev_id: str, conn: Conn, _: Editor):
    snaps = _build_snapshots(conn, url_id, with_body=True)
    for s in snaps:
        if s['id'] == rev_id:
            return RevisionContent(**s)
    raise HTTPException(status.HTTP_404_NOT_FOUND)


@router.get('/{url_id}', response_model=EntryOut)
def get_entry(url_id: str, conn: Conn, user: CurrentUser):
    return _entry_response(url_id, conn, user)


@router.put('/{url_id}', response_model=EntryOut)
def save_entry(url_id: str, data: EntrySaveIn, conn: Conn, user: Editor):
    # Validate the XML body up front so a malformed payload doesn't hold the
    # write lock that the transaction below acquires.
    el = _parse_safe(data.xml_body, 'Felaktig XML')
    if el.tag != 'entry':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Rotelementet måste vara <entry>')
    entry_type = el.get('type') or 'plain'
    if entry_type not in ENTRY_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f'Okänd posttyp {entry_type!r}; väntade en av {sorted(ENTRY_TYPES)}',
        )
    # Import skips entries without <orth>, so the editor shouldn't be able
    # to save into that state either: no orth means no headword, no sort
    # key, and no FTS index target. Checked via orth_texts rather than
    # find('.//orth') because a blank <orth> yields no headword either, and
    # would silently fall back to using the internal url_id as the headword.
    if not orth_texts(el):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'Posten måste innehålla minst ett <orth>-element med text',
        )

    fields = derive_entry_fields(el, headword_fallback=url_id)
    xml_root = el.get('root')
    xml_id = el.get('id')
    # Store the serialization of what we just parsed, never the client's
    # string: see canonical_entry_xml for the shape invariants that depend
    # on it.
    xml_body = canonical_entry_xml(el)

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
        _ensure_lock_free_for(row, user['user_id'], now, 'Låst av en annan redigerare')

        # `id` is how every other entry's `root` addresses this one, and
        # import derives url_id from it, so a duplicate makes group membership
        # ambiguous (the root lookups are LIMIT 1 with no ORDER BY) and makes
        # the next export unimportable on the url_id UNIQUE constraint. split
        # already guards this via _next_free_url_id; save didn't.
        if xml_id is not None:
            clash = conn.execute(
                'SELECT url_id FROM entries '
                'WHERE (xml_id = ? OR url_id = ?) AND id <> ? LIMIT 1',
                (xml_id, xml_id, row['id']),
            ).fetchone()
            if clash:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f'id="{xml_id}" används redan av posten {clash["url_id"]}',
                )

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
        new_status = _bump_status(row['status'], data.status)

        if xml_body == row['xml_body'] and new_status == row['status']:
            # Nothing to write, but the user is demonstrably still working on
            # this entry, so keep their lock alive. Letting it lapse here made
            # the response report no lock, which stopped the frontend
            # keepalive and left the entry grabbable mid-edit.
            conn.execute(
                'UPDATE entries SET lock_user_id = ?, lock_expires_at = ? WHERE id = ?',
                (user['user_id'], now + config.LOCK_TTL_SECONDS, row['id']),
            )
        else:
            # If no <cb/> precedes the first <orth>, keep the stored
            # starting_column — set during import from running-column state
            # we can't recompute from a single entry.
            starting_column = fields.leading_cb or row['starting_column']

            _snapshot_entry(conn, row['id'], user['user_id'], now)
            _write_entry_fields(
                conn, row['id'], xml_body=xml_body, fields=fields,
                entry_type=entry_type, xml_id=xml_id, xml_root=xml_root,
                starting_column=starting_column, status=new_status,
                now=now, user_id=user['user_id'],
            )

    return _entry_response(url_id, conn, user)


@router.post('/{url_id}/split', response_model=EntrySplitOut)
def split_entry(url_id: str, data: EntrySplitIn, conn: Conn, user: Editor):
    """Split an entry at `offset` (a character position in the saved
    xml_body). The first half retains the original url_id (so inbound
    refs remain valid); the second half becomes a new entry with
    type='derived', root set per the source's type (own id if primary,
    else inherited), and an id derived from its first <orth>."""
    now = security.now()
    with db.transaction(conn):
        row = conn.execute(
            'SELECT id, lock_user_id, lock_expires_at, xml_body, xml_id, '
            'xml_root, type, sort_key, status, starting_column, updated_at '
            'FROM entries WHERE url_id = ?',
            (url_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        _ensure_lock_free_for(row, user['user_id'], now, 'Låst av en annan redigerare')
        # `offset` is a character position the browser computed against its
        # own copy of the body. If the body has moved on since (a lapsed lock
        # plus another editor's save), an offset that happens to land on an
        # element boundary in the new text splits it somewhere the user never
        # previewed — silently, with 200.
        _ensure_unchanged(row, data.expected_updated_at)

        xml_body: str = row['xml_body']
        inner_from, inner_to = _entry_inner_bounds(xml_body)
        if not (inner_from < data.offset < inner_to):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                'Delningspositionen ligger utanför entryns innehåll',
            )

        first_inner = xml_body[inner_from:data.offset]
        second_inner = xml_body[data.offset:inner_to]
        source_open_tag = xml_body[:inner_from]
        first_xml = source_open_tag + first_inner + _ENTRY_CLOSE

        # Parsing both halves doubles as a sanity check that the offset
        # falls between top-level children (not mid-tag or mid-element).
        first_el = _parse_safe(first_xml, 'Ogiltig delningspunkt (första delen)')
        # The second half is parsed under a bare <entry> wrapper; we'll
        # rewrap below with the real opening tag once the id is derived.
        second_el = _parse_safe(
            '<entry>' + second_inner + _ENTRY_CLOSE,
            'Ogiltig delningspunkt (andra delen)',
        )

        if first_el.find('.//orth') is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                'Första delen saknar <orth> – flytta delningspunkten',
            )
        first_orth_in_second = second_el.find('.//orth')
        if first_orth_in_second is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                'Andra delen saknar <orth> – flytta delningspunkten',
            )

        orth_text = ''.join(first_orth_in_second.itertext()).strip()
        base_id = derive_xml_id_base(orth_text)
        if not base_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                'Kan inte härleda id från <orth>-texten i andra delen',
            )
        new_id = _next_free_url_id(conn, base_id)

        # type=derived; root follows the user's rule: own id if the source
        # heads its own group, else inherit the source's root, falling back to
        # the source's own id so the halves stay linked.
        #
        # get_entry_group treats 'proper' as a head exactly like 'primary', so
        # excluding it here left the split-off half of a proper noun with
        # root=None: a group of one, unreachable from the entry it was split
        # out of, and with no breadcrumb.
        new_root = (
            row['xml_id'] if row['type'] in ('primary', 'proper')
            else (row['xml_root'] or row['xml_id'])
        )
        root_attr = f' root="{html_escape(new_root, quote=True)}"' if new_root else ''
        new_xml = (
            f'<entry id="{html_escape(new_id, quote=True)}"'
            f' type="derived"{root_attr}>{second_inner}{_ENTRY_CLOSE}'
        )

        # Slot the new entry's sort_key strictly between source and its
        # current successor. Multiples of 100 at import give 99 slots of
        # headroom; in the unlikely event we've splintered an entry that
        # much, refuse with a hint so an admin can renumber.
        next_row = conn.execute(
            'SELECT sort_key FROM entries WHERE sort_key > ? '
            'ORDER BY sort_key ASC LIMIT 1',
            (row['sort_key'],),
        ).fetchone()
        if next_row is None:
            new_sort_key = row['sort_key'] + 100
        else:
            gap = next_row['sort_key'] - row['sort_key']
            if gap < 2:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    'Inget utrymme kvar i sorteringsordningen för en ny post här '
                    '– kontakta administratören för att numrera om.',
                )
            new_sort_key = row['sort_key'] + gap // 2

        first_fields = derive_entry_fields(first_el, headword_fallback=url_id)
        # The new half's element under the real opening tag has the same
        # content as second_el, so all <orth>-derived fields match; we only
        # reparse to validate the composed attribute string (which we built
        # from html_escape, so it can't actually be malformed, but the
        # cheap paranoia covers a future where we accept user-supplied attrs).
        new_fields = derive_entry_fields(second_el, headword_fallback=new_id)
        first_starting_col = first_fields.leading_cb or row['starting_column']
        # When the new half has no leading <cb/>, it continues in the source's
        # starting column; we don't carry running-column state per-entry.
        new_starting_col = new_fields.leading_cb or row['starting_column']

        # Splitting an entry is editorial work, so it advances the status the
        # same way a save does. Both halves get the result.
        new_status = _bump_status(row['status'], row['status'])

        _snapshot_entry(conn, row['id'], user['user_id'], now)
        _write_entry_fields(
            conn, row['id'], xml_body=first_xml, fields=first_fields,
            entry_type=row['type'], xml_id=row['xml_id'], xml_root=row['xml_root'],
            starting_column=first_starting_col, status=new_status,
            now=now, user_id=user['user_id'],
        )
        # The new entry inherits status from the source (the user has been
        # editing it; treating the split-off half as untouched would be
        # misleading) and the splitter's lock (so they can keep editing
        # without a separate acquire round-trip).
        conn.execute(
            'INSERT INTO entries (url_id, xml_id, xml_root, type, headword, '
            'headword_sort, alt_headwords, starting_column, first_orth_y, '
            'status, xml_body, plaintext, sort_key, lock_user_id, '
            'lock_expires_at, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (new_id, new_id, new_root, 'derived', new_fields.headword,
             new_fields.headword_sort,
             json.dumps(new_fields.alt_headwords, ensure_ascii=False),
             new_starting_col, new_fields.first_orth_y,
             new_status, new_xml, new_fields.plaintext, new_sort_key,
             user['user_id'], now + config.LOCK_TTL_SECONDS, now, now),
        )

    return EntrySplitOut(
        source_entry=EntrySummary(
            url_id=url_id, headword=first_fields.headword,
            alt_headwords=first_fields.alt_headwords,
            type=row['type'], status=new_status, comment_count=0,
        ),
        new_entry=EntrySummary(
            url_id=new_id, headword=new_fields.headword,
            alt_headwords=new_fields.alt_headwords,
            type='derived', status=new_status, comment_count=0,
        ),
    )


@router.post('/{url_id}/join-next', response_model=EntryOut)
def join_with_next(
    url_id: str, conn: Conn, user: Editor, data: EntryJoinIn | None = None,
):
    """Absorb the entry immediately following `url_id` (by sort_key) into
    this one. The next entry's inner content — including its <orth>, which
    becomes a secondary headword — is appended to this entry's body, and
    the next entry's row is hard-deleted. Cross-refs pointing at the
    absorbed entry are not rewritten; broken refs are accepted as the cost
    of a rare operation."""
    # Body stays optional so a bare POST still works for admin/curl use; the
    # editor sends both expectations.
    opts = data or EntryJoinIn()
    now = security.now()
    with db.transaction(conn):
        row = conn.execute(
            'SELECT id, lock_user_id, lock_expires_at, xml_body, sort_key, '
            'status, starting_column, type, xml_id, xml_root, updated_at '
            'FROM entries WHERE url_id = ?',
            (url_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        _ensure_lock_free_for(row, user['user_id'], now, 'Låst av en annan redigerare')
        _ensure_unchanged(row, opts.expected_updated_at)

        next_row = conn.execute(
            'SELECT id, url_id, headword, lock_user_id, lock_expires_at, '
            'xml_body, xml_id FROM entries WHERE sort_key > ? '
            'ORDER BY sort_key ASC LIMIT 1',
            (row['sort_key'],),
        ).fetchone()
        if not next_row:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                'Det finns ingen efterföljande post att slå ihop med',
            )
        # Which entry is "next" is resolved here, not by the client, so the
        # entry actually deleted can differ from the one the confirmation
        # dialog named — another editor splitting or creating an entry in
        # between is enough. Make the client state which one it meant.
        if (opts.expected_next_url_id is not None
                and opts.expected_next_url_id != next_row['url_id']):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f'Nästa post är nu {next_row["url_id"]}, inte '
                f'{opts.expected_next_url_id}; ladda om och försök igen.',
            )
        _ensure_lock_free_for(
            next_row, user['user_id'], now,
            f'Nästa post ({next_row["headword"]}) är låst av en annan redigerare',
        )
        # Deleting an entry that heads derivatives would strand them: their
        # `root` would point at an id that no longer resolves, so they'd drop
        # out of their group with no breadcrumb.
        if next_row['xml_id']:
            dependants = conn.execute(
                'SELECT url_id FROM entries WHERE xml_root = ? AND id <> ? LIMIT 1',
                (next_row['xml_id'], next_row['id']),
            ).fetchone()
            if dependants:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f'Nästa post ({next_row["headword"]}) har avledningar som '
                    f'pekar på den (t.ex. {dependants["url_id"]}); flytta dem '
                    f'först.',
                )

        cur_body: str = row['xml_body']
        next_body: str = next_row['xml_body']
        _, cur_inner_to = _entry_inner_bounds(cur_body)
        next_inner_from, next_inner_to = _entry_inner_bounds(next_body)
        merged_xml = (
            cur_body[:cur_inner_to]
            + next_body[next_inner_from:next_inner_to]
            + _ENTRY_CLOSE
        )

        merged_el = _parse_safe(merged_xml, 'Sammanslagningen gav ogiltig XML')
        if merged_el.find('.//orth') is None:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                'Sammanslagningen gav en post utan <orth>',
            )

        merged = derive_entry_fields(merged_el, headword_fallback=url_id)
        merged_status = _bump_status(row['status'], row['status'])

        _snapshot_entry(conn, row['id'], user['user_id'], now)
        # Keep the absorbed entry's final body as a revision of the survivor,
        # so its text survives the DELETE below (which cascades away the row
        # and its whole revision history) and can be recovered by hand. There
        # is no automated revert, and the row is a wart in the survivor's
        # timeline — the history view diffs it against the preceding snapshot
        # as a whole-article replacement — but that beats losing the text.
        conn.execute(
            'INSERT INTO entry_revisions (entry_id, xml_body, status, user_id, created_at) '
            'VALUES (?, ?, ?, ?, ?)',
            (row['id'], next_row['xml_body'], row['status'], user['user_id'], now),
        )
        # Discussion about the absorbed text belongs with the text, which now
        # lives here. Otherwise ON DELETE CASCADE silently threw it away.
        conn.execute(
            'UPDATE entry_comments SET entry_id = ? WHERE entry_id = ?',
            (row['id'], next_row['id']),
        )
        _write_entry_fields(
            conn, row['id'], xml_body=merged_xml, fields=merged,
            entry_type=row['type'], xml_id=row['xml_id'], xml_root=row['xml_root'],
            # The merged entry still begins where it began; a <cb/> arriving
            # from the absorbed half doesn't move its start.
            starting_column=row['starting_column'], status=merged_status,
            now=now, user_id=user['user_id'],
        )
        # ON DELETE CASCADE drops the absorbed entry's remaining revisions.
        conn.execute('DELETE FROM entries WHERE id = ?', (next_row['id'],))

    return _entry_response(url_id, conn, user)
