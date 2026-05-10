"""Revision history endpoints: list + single-snapshot fetch."""

from __future__ import annotations


def _reset(url_id: str, xml: str = None, status: str = 'untouched') -> None:
    """Clear revisions and reset the entry so a test starts from scratch."""
    from app import db, security
    if xml is None:
        xml = f'<entry id="{url_id}" type="primary"><orth>seed</orth></entry>'
    now = security.now()
    with db.get_conn() as conn:
        row = conn.execute(
            'SELECT id FROM entries WHERE url_id = ?', (url_id,),
        ).fetchone()
        conn.execute('DELETE FROM entry_revisions WHERE entry_id = ?', (row['id'],))
        conn.execute(
            'UPDATE entries SET xml_body = ?, status = ?, updated_at = ? WHERE id = ?',
            (xml, status, now, row['id']),
        )


def test_list_revisions_returns_only_current_when_never_saved(auth_client):
    _reset('testentry1')
    r = auth_client.get('/api/entries/testentry1/revisions')
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]['id'] == 'current'
    assert items[0]['is_current'] is True
    # No save event, but updated_at carries the import time so the UI can
    # still show *when* the current state has existed.
    assert items[0]['saved_at'] is not None
    # saved_by stays null to mark it as imported.
    assert items[0]['saved_by_id'] is None
    assert items[0]['saved_by'] is None


def test_list_revisions_after_one_save_has_two_items(auth_client):
    _reset('testentry1')
    new_xml = '<entry id="testentry1" type="primary"><orth>after-save</orth></entry>'
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': new_xml, 'status': 'in_progress',
    })
    assert r.status_code == 200, r.text

    r = auth_client.get('/api/entries/testentry1/revisions')
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2

    cur, prev = items
    assert cur['id'] == 'current'
    assert cur['is_current'] is True
    assert cur['saved_by'] == 'Test'  # the save we just did
    assert cur['saved_at'] is not None

    # The pre-save snapshot is the imported state — no save event produced
    # it, but we still report the import time so the UI has a timestamp.
    assert prev['is_current'] is False
    assert prev['saved_by_id'] is None
    assert prev['saved_at'] is not None


def test_list_revisions_after_multiple_saves(auth_client):
    _reset('testentry1')
    bodies = [
        '<entry id="testentry1" type="primary"><orth>v1</orth></entry>',
        '<entry id="testentry1" type="primary"><orth>v2</orth></entry>',
        '<entry id="testentry1" type="primary"><orth>v3</orth></entry>',
    ]
    for xml in bodies:
        r = auth_client.put('/api/entries/testentry1', json={
            'xml_body': xml, 'status': 'in_progress',
        })
        assert r.status_code == 200, r.text

    r = auth_client.get('/api/entries/testentry1/revisions')
    assert r.status_code == 200
    items = r.json()
    # 3 saves → imported + 3 = 4 snapshots.
    assert len(items) == 4
    # Newest first: current, then the three predecessors in reverse order,
    # ending with the imported state. Imported reports no saver but still
    # carries the import timestamp.
    assert items[0]['id'] == 'current'
    assert items[0]['is_current'] is True
    assert items[-1]['saved_by_id'] is None
    assert items[-1]['saved_at'] is not None
    # Save-produced items in between have a saver.
    for mid in items[1:-1]:
        assert mid['saved_by'] == 'Test'
        assert mid['saved_at'] is not None


def test_get_revision_current_returns_live_xml(auth_client):
    _reset('testentry1')
    new_xml = '<entry id="testentry1" type="primary"><orth>live</orth></entry>'
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': new_xml, 'status': 'in_progress',
    })
    assert r.status_code == 200

    r = auth_client.get('/api/entries/testentry1/revisions/current')
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['id'] == 'current'
    assert body['is_current'] is True
    assert body['xml_body'] == new_xml


def test_get_revision_historical_returns_old_xml(auth_client):
    _reset('testentry1', xml='<entry id="testentry1" type="primary"><orth>old</orth></entry>')
    new_xml = '<entry id="testentry1" type="primary"><orth>new</orth></entry>'
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': new_xml, 'status': 'in_progress',
    })
    assert r.status_code == 200

    r = auth_client.get('/api/entries/testentry1/revisions')
    items = r.json()
    historical = [it for it in items if not it['is_current']]
    assert len(historical) == 1
    rev_id = historical[0]['id']

    r = auth_client.get(f'/api/entries/testentry1/revisions/{rev_id}')
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['xml_body'] == '<entry id="testentry1" type="primary"><orth>old</orth></entry>'
    assert body['is_current'] is False


def test_get_revision_unknown_id_returns_404(auth_client):
    r = auth_client.get('/api/entries/testentry1/revisions/9999999')
    assert r.status_code == 404


def test_revisions_require_editor(client):
    r = client.get('/api/entries/testentry1/revisions')
    assert r.status_code == 401
    r = client.get('/api/entries/testentry1/revisions/current')
    assert r.status_code == 401


def test_revisions_unknown_entry_returns_404(auth_client):
    r = auth_client.get('/api/entries/does-not-exist/revisions')
    assert r.status_code == 404
    r = auth_client.get('/api/entries/does-not-exist/revisions/current')
    assert r.status_code == 404
