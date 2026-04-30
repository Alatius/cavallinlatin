"""Per-entry comments and the activity feed endpoints."""

from __future__ import annotations


def test_list_comments_requires_auth(client):
    r = client.get('/api/entries/testentry1/comments')
    assert r.status_code == 401


def test_create_then_list_comment(auth_client):
    r = auth_client.post('/api/entries/testentry1/comments', json={'body': 'hello'})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body['body'] == 'hello'
    assert body['display_name'] == 'Test'

    r = auth_client.get('/api/entries/testentry1/comments')
    assert r.status_code == 200
    items = r.json()
    assert any(c['body'] == 'hello' for c in items)


def test_create_comment_rejects_blank(auth_client):
    r = auth_client.post('/api/entries/testentry1/comments', json={'body': '   '})
    assert r.status_code == 400


def test_create_comment_404_for_missing_entry(auth_client):
    r = auth_client.post('/api/entries/no_such_entry/comments', json={'body': 'x'})
    assert r.status_code == 404


def test_activity_comments_returns_latest_per_entry(auth_client):
    """The /activity/comments endpoint returns one row per entry (the most
    recent comment), not one row per comment — so multiple comments on the
    same entry collapse to a single, latest-snippet row."""
    auth_client.post('/api/entries/testentry1/comments', json={'body': 'first'})
    auth_client.post('/api/entries/testentry1/comments', json={'body': 'second'})
    auth_client.post('/api/entries/testentry2/comments', json={'body': 'other'})

    r = auth_client.get('/api/activity/comments')
    assert r.status_code == 200
    rows = r.json()
    by_url = {r['url_id']: r for r in rows}
    assert by_url['testentry1']['snippet'] == 'second'
    assert by_url['testentry1']['count'] >= 2
    assert by_url['testentry2']['snippet'] == 'other'


def test_activity_edits_returns_edited_entries(auth_client):
    """Saving any entry must surface it in /activity/edits with the right
    revision count."""
    # Keep the headword stable: other tests assert testentry1's headword,
    # and the shared seed DB persists across tests in this session.
    auth_client.put('/api/entries/testentry1', json={
        'xml_body': '<entry id="testentry1" type="primary"><orth>word0</orth></entry>',
        'status': 'in_progress',
    })
    r = auth_client.get('/api/activity/edits')
    assert r.status_code == 200
    rows = r.json()
    assert any(r['url_id'] == 'testentry1' and r['count'] >= 1 for r in rows)
