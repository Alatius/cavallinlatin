"""Stored xml_body has exactly one shape.

Save used to persist the client's string verbatim. Split, join, export and the
renderer all assume a tighter serialization than "parses as XML", so a body
that merely parsed could permanently break them.
"""

from __future__ import annotations

import pytest

from app import db


@pytest.fixture(scope='module', autouse=True)
def _leave_no_trace():
    """Drop every row this module adds.

    The DB is shared for the whole session, and this module sorts before
    test_entries, whose prev/next assertions depend on the seeded entries
    being the only ones present. Rows created indirectly (by a split) are
    caught too, since we diff the url_id set rather than a fixed list.
    """
    with db.get_conn() as conn:
        before = {r['url_id'] for r in conn.execute('SELECT url_id FROM entries')}
    yield
    with db.get_conn() as conn:
        after = {r['url_id'] for r in conn.execute('SELECT url_id FROM entries')}
        for url_id in after - before:
            conn.execute('DELETE FROM entries WHERE url_id = ?', (url_id,))


def _seed(url_id: str, body: str, sort_key: int) -> None:
    from app import security
    now = security.now()
    with db.get_conn() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO entries (url_id, xml_id, type, headword, '
            'headword_sort, xml_body, plaintext, sort_key, created_at, updated_at) '
            'VALUES (?,?,?,?,?,?,?,?,?,?)',
            (url_id, url_id, 'primary', url_id, url_id, body, url_id, sort_key, now, now),
        )


def _stored(url_id: str) -> str:
    with db.get_conn() as conn:
        return conn.execute(
            'SELECT xml_body FROM entries WHERE url_id = ?', (url_id,)
        ).fetchone()['xml_body']


@pytest.mark.parametrize('sent,reason', [
    ('\n<entry id="canon" type="primary"><orth>a</orth>x</entry>\n',
     'leading/trailing whitespace'),
    ('<?xml version="1.0"?><entry id="canon" type="primary"><orth>a</orth>x</entry>',
     'XML prologue'),
    ("<entry id='canon' type='primary'><orth>a</orth>x</entry>",
     'single-quoted attributes'),
    ('<entry id="canon" type="primary"><orth>a</orth><![CDATA[ <img src=x> ]]></entry>',
     'CDATA section carrying raw markup'),
])
def test_save_stores_a_canonical_serialization(auth_client, sent, reason):
    _seed('canon', '<entry id="canon" type="primary"><orth>a</orth>x</entry>', 4100)
    r = auth_client.put('/api/entries/canon', json={
        'xml_body': sent, 'status': 'in_progress',
    })
    assert r.status_code == 200, r.text

    stored = _stored('canon')
    assert stored.startswith('<entry'), f'{reason}: {stored!r}'
    assert stored.endswith('</entry>'), f'{reason}: {stored!r}'
    assert "'" not in stored.split('>')[0], f'{reason}: attributes not normalized'
    assert '<![CDATA[' not in stored, f'{reason}: CDATA survived'
    # The response hands the client the same string, so the editor buffer and
    # the stored body can't drift (split offsets are computed against it).
    assert r.json()['xml_body'] == stored


def test_canonical_body_keeps_split_working(auth_client):
    """A body with a prologue used to save fine and then 500 on every split
    for the rest of that entry's life."""
    _seed('canonsplit',
          '<entry id="canonsplit" type="primary"><orth>a</orth>x<orth>b</orth>y</entry>', 4200)
    sent = ('<?xml version="1.0"?>'
            '<entry id="canonsplit" type="primary"><orth>a</orth>x<orth>b</orth>y</entry>')
    assert auth_client.put('/api/entries/canonsplit', json={
        'xml_body': sent, 'status': 'in_progress',
    }).status_code == 200

    stored = _stored('canonsplit')
    r = auth_client.post('/api/entries/canonsplit/split',
                         json={'offset': stored.index('<orth>b</orth>')})
    assert r.status_code == 200, r.text


def test_raw_gt_in_root_attribute_does_not_corrupt_join(auth_client):
    """`root="a>b"` is legal XML. The open-tag regex used to stop at that '>',
    and join spliced the leftover attribute text into the entry body."""
    _seed('jgtl', '<entry id="jgtl" type="primary"><orth>left</orth>LEFT</entry>', 4300)
    _seed('jgtr', '<entry id="jgtr" type="primary"><orth>right</orth>RIGHT</entry>', 4400)
    assert auth_client.put('/api/entries/jgtr', json={
        'xml_body': '<entry id="jgtr" type="primary" n="a &gt; b">'
                    '<orth>right</orth>RIGHT</entry>',
        'status': 'in_progress',
    }).status_code == 200

    assert auth_client.post('/api/entries/jgtl/join-next', json={}).status_code == 200
    merged = _stored('jgtl')
    assert 'b&gt;' not in merged and 'b">' not in merged, merged
    assert merged == ('<entry id="jgtl" type="primary"><orth>left</orth>LEFT'
                      '<orth>right</orth>RIGHT</entry>')


def test_save_rejects_blank_orth(auth_client):
    """`<orth> </orth>` passed the "must have an <orth>" guard but yields no
    headword, so the entry's internal url_id leaked into the index as one."""
    _seed('blankorth', '<entry id="blankorth" type="primary"><orth>a</orth>x</entry>', 4500)
    r = auth_client.put('/api/entries/blankorth', json={
        'xml_body': '<entry id="blankorth" type="primary"><orth>  </orth>text</entry>',
        'status': 'in_progress',
    })
    assert r.status_code == 400


def test_save_rejects_id_already_used_by_another_entry(auth_client):
    """Duplicate xml_id makes group membership ambiguous and makes the next
    export fail to re-import on the url_id UNIQUE constraint."""
    _seed('dupa', '<entry id="dupa" type="primary"><orth>a</orth>x</entry>', 4600)
    _seed('dupb', '<entry id="dupb" type="primary"><orth>b</orth>y</entry>', 4700)
    r = auth_client.put('/api/entries/dupb', json={
        'xml_body': '<entry id="dupa" type="primary"><orth>b</orth>y</entry>',
        'status': 'in_progress',
    })
    assert r.status_code == 409
    with db.get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM entries WHERE xml_id = 'dupa'").fetchone()['n']
    assert n == 1


def test_save_keeps_own_id(auth_client):
    """The clash check must not trip on the entry's own row."""
    _seed('ownid', '<entry id="ownid" type="primary"><orth>a</orth>x</entry>', 4800)
    r = auth_client.put('/api/entries/ownid', json={
        'xml_body': '<entry id="ownid" type="primary"><orth>a</orth>changed</entry>',
        'status': 'in_progress',
    })
    assert r.status_code == 200
