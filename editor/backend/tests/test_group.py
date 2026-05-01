"""Etymological-group endpoint and root_headword on EntryOut."""

from __future__ import annotations

import pytest


@pytest.fixture(scope='module', autouse=True)
def seed_group():
    """Seed a head + two derivatives + a reference for the group tests."""
    from app import db, security
    now = security.now()
    members = [
        # (url_id, xml_id, xml_root, type, headword, sort_key)
        ('grp_head', 'cano',     None,   'primary',   'cano',   1000),
        ('grp_d1',   'cantor',   'cano', 'derived',   'cantor', 1010),
        ('grp_d2',   'canto',    'cano', 'derived',   'canto',  1020),
        ('grp_ref',  None,       None,   'reference', 'rufus',  1030),
        ('grp_orph', 'orfanus',  'gone', 'derived',   'orfanus', 1040),
    ]
    with db.get_conn() as conn:
        for url_id, xml_id, xml_root, t, hw, sk in members:
            xml = (f'<entry id="{xml_id}" type="{t}" '
                   f'root="{xml_root}"><orth>{hw}</orth></entry>'
                   if xml_id else
                   f'<entry type="{t}"><orth>{hw}</orth></entry>')
            conn.execute(
                'INSERT OR REPLACE INTO entries '
                '(url_id, xml_id, xml_root, type, headword, headword_sort, '
                ' xml_body, plaintext, sort_key, created_at, updated_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (url_id, xml_id, xml_root, t, hw, hw, xml, hw, sk, now, now),
            )
    yield
    with db.get_conn() as conn:
        conn.execute(
            "DELETE FROM entries WHERE url_id IN "
            "('grp_head','grp_d1','grp_d2','grp_ref','grp_orph')"
        )


def test_group_from_derivative_returns_head_and_siblings(client):
    r = client.get('/api/entries/grp_d1/group')
    assert r.status_code == 200
    body = r.json()
    assert body['focus_url_id'] == 'grp_d1'
    assert body['head_url_id'] == 'grp_head'
    urls = [i['url_id'] for i in body['items']]
    assert urls == ['grp_head', 'grp_d1', 'grp_d2']


def test_group_from_head_returns_self_and_children(client):
    r = client.get('/api/entries/grp_head/group')
    body = r.json()
    assert body['focus_url_id'] == 'grp_head'
    assert body['head_url_id'] == 'grp_head'
    assert [i['url_id'] for i in body['items']] == ['grp_head', 'grp_d1', 'grp_d2']


def test_group_singleton_for_reference(client):
    r = client.get('/api/entries/grp_ref/group')
    body = r.json()
    assert len(body['items']) == 1
    assert body['items'][0]['url_id'] == 'grp_ref'
    # Reference isn't primary/proper, so no head.
    assert body['head_url_id'] is None


def test_group_orphan_derivative_has_no_head(client):
    """root='gone' points at no real entry, so head_url_id stays None and the
    derivative is its own (lonely) group member."""
    r = client.get('/api/entries/grp_orph/group')
    body = r.json()
    assert body['head_url_id'] is None
    assert [i['url_id'] for i in body['items']] == ['grp_orph']


def test_group_singleton_for_isolated_primary(client):
    """testentry1 is a primary with xml_id NULL — the query falls through to
    the singleton path, but a primary is still its own head."""
    r = client.get('/api/entries/testentry1/group')
    body = r.json()
    assert body['focus_url_id'] == 'testentry1'
    assert len(body['items']) == 1
    assert body['head_url_id'] == 'testentry1'


def test_group_404_for_unknown(client):
    r = client.get('/api/entries/nonexistent/group')
    assert r.status_code == 404


def test_get_entry_includes_root_headword_for_derivative(client):
    r = client.get('/api/entries/grp_d1')
    assert r.status_code == 200
    assert r.json()['root_headword'] == 'cano'


def test_get_entry_root_headword_null_for_isolated(client):
    r = client.get('/api/entries/testentry1')
    assert r.json()['root_headword'] is None
