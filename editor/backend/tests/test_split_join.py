"""Split and join entry endpoints."""

from __future__ import annotations

import pytest


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _seed_entry(
    url_id: str, xml: str, *, sort_key: int,
    entry_type: str = 'primary', xml_id: str | None = None,
    xml_root: str | None = None,
) -> None:
    """Insert (or replace) a test entry. Routed around the save endpoint so
    we control xml_body byte-for-byte (the save endpoint canonicalises by
    re-extracting headword etc., which is fine but adds noise to tests
    that pin offsets into the body)."""
    from app import db, security
    now = security.now()
    eff_xml_id = xml_id if xml_id is not None else url_id
    with db.get_conn() as conn:
        # Delete any prior copy plus any test rows that would clash on the
        # UNIQUE sort_key — earlier tests may have left entries at the same
        # sort_key under different url_ids.
        conn.execute('DELETE FROM entries WHERE url_id = ?', (url_id,))
        conn.execute('DELETE FROM entries WHERE sort_key = ?', (sort_key,))
        conn.execute(
            'INSERT INTO entries (url_id, xml_id, xml_root, type, headword, '
            'headword_sort, alt_headwords, xml_body, plaintext, sort_key, '
            'created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (url_id, eff_xml_id, xml_root, entry_type, url_id, url_id, '[]',
             xml, url_id, sort_key, now, now),
        )


@pytest.fixture
def split_target(auth_client):
    """Seed a primary entry with two <orth>-bearing senses and return its
    url_id plus the offset that lands between the two senses."""
    body = (
        '<entry id="splitme" type="primary">'
        '<orth>splitme</orth>'
        '<sense n="a">first sense</sense>'
        '<sense n="b"><orth>splitb</orth>second sense</sense>'
        '</entry>'
    )
    _seed_entry('splitme', body, sort_key=10_000)
    # Offset between <sense n="a">…</sense> and <sense n="b">…</sense>.
    offset = body.index('<sense n="b"')
    return 'splitme', body, offset


# -----------------------------------------------------------------------------
# Split
# -----------------------------------------------------------------------------


def test_split_creates_new_entry(auth_client, split_target):
    url_id, body, offset = split_target
    r = auth_client.post(f'/api/entries/{url_id}/split', json={'offset': offset})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out['source_entry']['url_id'] == 'splitme'
    assert out['source_entry']['headword'] == 'splitme'
    new_url_id = out['new_entry']['url_id']
    assert new_url_id == 'splitb'
    assert out['new_entry']['type'] == 'derived'
    assert out['new_entry']['headword'] == 'splitb'

    # Source body should no longer contain the second sense.
    src = auth_client.get('/api/entries/splitme').json()
    assert '<sense n="a">' in src['xml_body']
    assert '<sense n="b">' not in src['xml_body']

    # New entry: type=derived, root=splitme (source was primary), contains
    # the second sense.
    new = auth_client.get(f'/api/entries/{new_url_id}').json()
    assert new['type'] == 'derived'
    assert new['xml_root'] == 'splitme'
    assert '<sense n="b">' in new['xml_body']
    assert new['xml_body'].startswith('<entry id="splitb" type="derived" root="splitme">')


def test_split_inherits_root_when_source_is_not_primary(auth_client):
    """If the source is itself derived (or plain/etym), the new entry's
    root copies the source's root rather than the source's own id."""
    body = (
        '<entry id="splitderived" type="derived" root="someroot">'
        '<orth>splitderived</orth>X'
        '<orth>splitsubb</orth>Y'
        '</entry>'
    )
    _seed_entry('splitderived', body, sort_key=11_000,
                entry_type='derived', xml_root='someroot')
    offset = body.index('<orth>splitsubb')
    r = auth_client.post('/api/entries/splitderived/split', json={'offset': offset})
    assert r.status_code == 200, r.text
    out = r.json()
    new_url_id = out['new_entry']['url_id']
    new = auth_client.get(f'/api/entries/{new_url_id}').json()
    assert new['xml_root'] == 'someroot'


def test_split_bumps_homograph_number_on_collision(auth_client):
    """When the derived id would collide with an existing url_id, append 1, 2,
    … until a free slot is found."""
    # Pre-seed an entry that will collide with the natural id 'collide'.
    _seed_entry(
        'collide',
        '<entry id="collide" type="primary"><orth>collide</orth>x</entry>',
        sort_key=12_000,
    )
    # And one with 'collide1' so the bumper has to go to '2'.
    _seed_entry(
        'collide1',
        '<entry id="collide1" type="primary"><orth>collide</orth>x</entry>',
        sort_key=12_100,
    )

    body = (
        '<entry id="src" type="primary">'
        '<orth>src</orth>before'
        '<orth>collide</orth>after'
        '</entry>'
    )
    _seed_entry('src', body, sort_key=13_000)
    offset = body.index('<orth>collide')
    r = auth_client.post('/api/entries/src/split', json={'offset': offset})
    assert r.status_code == 200, r.text
    assert r.json()['new_entry']['url_id'] == 'collide2'


def test_split_refuses_no_orth_in_second_half(auth_client):
    body = (
        '<entry id="onlyone" type="primary">'
        '<orth>onlyone</orth>'
        '<sense n="a">just one orth</sense>'
        '</entry>'
    )
    _seed_entry('onlyone', body, sort_key=14_000)
    offset = body.index('<sense n="a">')
    r = auth_client.post('/api/entries/onlyone/split', json={'offset': offset})
    assert r.status_code == 400
    assert 'orth' in r.json()['detail'].lower()


def test_split_refuses_offset_inside_tag(auth_client, split_target):
    url_id, body, _ = split_target
    # Pick an offset that lands mid-tag — inside `<sense n="b"`.
    bad = body.index('<sense n="b"') + 5
    r = auth_client.post(f'/api/entries/{url_id}/split', json={'offset': bad})
    assert r.status_code == 400


def test_split_refuses_offset_outside_inner(auth_client, split_target):
    url_id, body, _ = split_target
    # Offset 0 lands inside the opening <entry …> tag.
    r = auth_client.post(f'/api/entries/{url_id}/split', json={'offset': 0})
    assert r.status_code == 400
    # Offset == end-of-body lands at/after </entry>.
    r = auth_client.post(
        f'/api/entries/{url_id}/split', json={'offset': len(body)},
    )
    assert r.status_code == 400


def test_split_refuses_when_locked_by_other(client, auth_client, split_target):
    """If a different user holds the lock, the split must 409 — the lock
    check matches save_entry's, which is the source of truth."""
    from app import db, security
    url_id, body, offset = split_target
    # Forge a lock by a different user on the entry.
    with db.get_conn() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO users (email, display_name, password_hash, '
            'is_admin, created_at) VALUES (?, ?, ?, 0, ?)',
            ('other@example.com', 'Other', 'x', security.now()),
        )
        other_id = conn.execute(
            'SELECT id FROM users WHERE email = ?', ('other@example.com',)
        ).fetchone()['id']
        conn.execute(
            'UPDATE entries SET lock_user_id = ?, lock_expires_at = ? '
            'WHERE url_id = ?',
            (other_id, security.now() + 600, url_id),
        )
    r = auth_client.post(f'/api/entries/{url_id}/split', json={'offset': offset})
    assert r.status_code == 409


def test_split_refuses_unauthenticated(client, split_target):
    url_id, _, offset = split_target
    r = client.post(f'/api/entries/{url_id}/split', json={'offset': offset})
    assert r.status_code == 401


def test_split_creates_revision_of_pre_split_body(auth_client, split_target):
    """Splitting should snapshot the source's pre-split body into entry_revisions
    so the editor can revert via history."""
    from app import db
    url_id, _, offset = split_target
    with db.get_conn() as conn:
        before = conn.execute(
            'SELECT COUNT(*) AS n FROM entry_revisions r '
            'JOIN entries e ON e.id = r.entry_id WHERE e.url_id = ?',
            (url_id,),
        ).fetchone()['n']
    r = auth_client.post(f'/api/entries/{url_id}/split', json={'offset': offset})
    assert r.status_code == 200, r.text
    with db.get_conn() as conn:
        after = conn.execute(
            'SELECT COUNT(*) AS n FROM entry_revisions r '
            'JOIN entries e ON e.id = r.entry_id WHERE e.url_id = ?',
            (url_id,),
        ).fetchone()['n']
    assert after - before == 1


# -----------------------------------------------------------------------------
# Join
# -----------------------------------------------------------------------------


def test_join_absorbs_next_entry(auth_client):
    _seed_entry(
        'joinleft',
        '<entry id="joinleft" type="primary">'
        '<orth>joinleft</orth>left content'
        '</entry>',
        sort_key=20_000,
    )
    _seed_entry(
        'joinright',
        '<entry id="joinright" type="primary">'
        '<orth>joinright</orth>right content'
        '</entry>',
        sort_key=20_100,
    )

    r = auth_client.post('/api/entries/joinleft/join-next')
    assert r.status_code == 200, r.text
    out = r.json()
    # The merged entry retains joinleft's identity.
    assert out['url_id'] == 'joinleft'
    assert out['headword'] == 'joinleft'
    assert 'joinright' in out['alt_headwords']
    assert 'left content' in out['xml_body']
    assert 'right content' in out['xml_body']
    # Absorbed entry is hard-deleted.
    r = auth_client.get('/api/entries/joinright')
    assert r.status_code == 404


def test_join_refuses_when_no_next_entry(auth_client):
    # Use a very high sort_key so this row is the last one in the DB.
    _seed_entry(
        'joinlast',
        '<entry id="joinlast" type="primary"><orth>joinlast</orth>x</entry>',
        sort_key=999_000,
    )
    r = auth_client.post('/api/entries/joinlast/join-next')
    assert r.status_code == 400
    assert 'efterföljande' in r.json()['detail']


def test_join_refuses_when_next_is_locked_by_other(auth_client):
    from app import db, security
    _seed_entry(
        'jL', '<entry id="jL" type="primary"><orth>jL</orth>x</entry>',
        sort_key=21_000,
    )
    _seed_entry(
        'jR', '<entry id="jR" type="primary"><orth>jR</orth>y</entry>',
        sort_key=21_100,
    )
    with db.get_conn() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO users (email, display_name, password_hash, '
            'is_admin, created_at) VALUES (?, ?, ?, 0, ?)',
            ('other2@example.com', 'Other2', 'x', security.now()),
        )
        other_id = conn.execute(
            'SELECT id FROM users WHERE email = ?', ('other2@example.com',)
        ).fetchone()['id']
        conn.execute(
            'UPDATE entries SET lock_user_id = ?, lock_expires_at = ? '
            'WHERE url_id = ?',
            (other_id, security.now() + 600, 'jR'),
        )
    r = auth_client.post('/api/entries/jL/join-next')
    assert r.status_code == 409


def test_join_creates_revision(auth_client):
    from app import db
    _seed_entry(
        'jRevL',
        '<entry id="jRevL" type="primary"><orth>jRevL</orth>L</entry>',
        sort_key=22_000,
    )
    _seed_entry(
        'jRevR',
        '<entry id="jRevR" type="primary"><orth>jRevR</orth>R</entry>',
        sort_key=22_100,
    )
    with db.get_conn() as conn:
        before = conn.execute(
            'SELECT COUNT(*) AS n FROM entry_revisions r '
            'JOIN entries e ON e.id = r.entry_id WHERE e.url_id = ?',
            ('jRevL',),
        ).fetchone()['n']
    r = auth_client.post('/api/entries/jRevL/join-next')
    assert r.status_code == 200, r.text
    with db.get_conn() as conn:
        after = conn.execute(
            'SELECT COUNT(*) AS n FROM entry_revisions r '
            'JOIN entries e ON e.id = r.entry_id WHERE e.url_id = ?',
            ('jRevL',),
        ).fetchone()['n']
    assert after - before == 1


def test_join_unauthenticated(client):
    _seed_entry(
        'jAuthL',
        '<entry id="jAuthL" type="primary"><orth>jAuthL</orth>x</entry>',
        sort_key=23_000,
    )
    _seed_entry(
        'jAuthR',
        '<entry id="jAuthR" type="primary"><orth>jAuthR</orth>y</entry>',
        sort_key=23_100,
    )
    r = client.post('/api/entries/jAuthL/join-next')
    assert r.status_code == 401
