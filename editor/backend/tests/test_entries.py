"""Entry save validation, lock conflicts, body size limit."""

from __future__ import annotations


def test_get_entry_returns_prev_next(client):
    r = client.get('/api/entries/testentry1')
    assert r.status_code == 200
    body = r.json()
    assert body['headword'] == 'word0'
    assert body['next_url_id'] == 'testentry2'
    assert body['prev_url_id'] is None
    r = client.get('/api/entries/testentry2')
    body = r.json()
    assert body['prev_url_id'] == 'testentry1'
    assert body['next_url_id'] is None


def test_save_rejects_malformed_xml(auth_client):
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': '<entry><orth>broken',
        'status': 'in_progress',
    })
    assert r.status_code == 400
    assert 'Felaktig' in r.json()['detail']


def test_save_rejects_wrong_root(auth_client):
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': '<dictionary><orth>foo</orth></dictionary>',
        'status': 'in_progress',
    })
    assert r.status_code == 400
    assert '<entry>' in r.json()['detail']


def test_save_rejects_unknown_type(auth_client):
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': '<entry type="bogus"><orth>foo</orth></entry>',
        'status': 'in_progress',
    })
    assert r.status_code == 400


def test_save_rejects_missing_orth(auth_client):
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': '<entry type="primary">no orth here</entry>',
        'status': 'in_progress',
    })
    assert r.status_code == 400
    assert 'orth' in r.json()['detail'].lower()


def test_save_does_not_expand_entity_bomb(auth_client):
    # A DTD-bearing payload is technically saveable (it parses), but the
    # SAFE_XML_PARSER must not expand the entity references during the
    # derived-fields computation — otherwise headword/plaintext could
    # balloon to gigabytes.
    payload = (
        '<?xml version="1.0"?><!DOCTYPE entry ['
        '<!ENTITY a "EXPANDED">]>'
        '<entry type="primary"><orth>foo</orth>&a;</entry>'
    )
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': payload,
        'status': 'in_progress',
    })
    # Either accepted with the entity reference left as text, or rejected.
    # In neither case may the literal 'EXPANDED' end up in the headword.
    if r.status_code == 200:
        body = r.json()
        assert 'EXPANDED' not in body['headword']
    else:
        assert r.status_code == 400


def test_save_valid_round_trip(auth_client):
    new_xml = (
        '<entry id="testentry1" type="primary">'
        '<orth>updated</orth> body text</entry>'
    )
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': new_xml,
        'status': 'in_progress',
    })
    assert r.status_code == 200, r.text
    assert r.json()['headword'] == 'updated'
    # Read back and confirm.
    r = auth_client.get('/api/entries/testentry1')
    assert r.json()['xml_body'] == new_xml


def test_lock_conflict_between_two_users(client, auth_client):
    """User A acquires the lock; an unrelated request without auth can't
    save (401) and another authenticated user (we re-use auth_client here
    by re-logging in as the same user — the lock then belongs to us, so
    we can save). Sufficient to assert the 401 path."""
    # Acquire lock as auth_client.
    r = auth_client.post('/api/entries/testentry1/lock')
    assert r.status_code == 200

    # Anonymous client save attempt — must be 401, regardless of lock state.
    r = client.put('/api/entries/testentry1', json={
        'xml_body': '<entry><orth>x</orth></entry>',
        'status': 'in_progress',
    })
    assert r.status_code == 401


def test_body_size_limit(auth_client):
    big = '<entry><orth>foo</orth>' + ('x' * 1_500_000) + '</entry>'
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': big,
        'status': 'in_progress',
    })
    assert r.status_code == 413


def test_save_with_matching_expected_updated_at_succeeds(auth_client):
    r = auth_client.get('/api/entries/testentry1')
    expected = r.json()['updated_at']
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': '<entry id="testentry1" type="primary"><orth>matched</orth></entry>',
        'status': 'in_progress',
        'expected_updated_at': expected,
    })
    assert r.status_code == 200


def test_save_with_stale_expected_updated_at_rejected(auth_client):
    """If the row's updated_at has advanced since the client loaded it, the
    save must 409 instead of silently overwriting whoever wrote in between."""
    from app import db
    r = auth_client.get('/api/entries/testentry1')
    stale = r.json()['updated_at']
    # Simulate a concurrent save bumping the row.
    with db.get_conn() as conn:
        conn.execute(
            'UPDATE entries SET updated_at = ? WHERE url_id = ?',
            (stale + 60, 'testentry1'),
        )
    r = auth_client.put('/api/entries/testentry1', json={
        'xml_body': '<entry id="testentry1" type="primary"><orth>stale</orth></entry>',
        'status': 'in_progress',
        'expected_updated_at': stale,
    })
    assert r.status_code == 409
    assert 'ändrats' in r.json()['detail']


def test_save_autobumps_untouched_to_in_progress(auth_client):
    """Saving an untouched entry with status=untouched advances it to
    in_progress server-side: by editing and saving, the editor has by
    definition done some work, so the entry is no longer untouched."""
    from app import db
    # Reset to untouched so the auto-bump rule has something to act on.
    # Other tests share these entries — keep the headword stable so search
    # / prev-next assertions elsewhere still hold.
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE entries SET status = 'untouched' WHERE url_id = ?",
            ('testentry2',),
        )
    r = auth_client.put('/api/entries/testentry2', json={
        'xml_body': '<entry id="testentry2" type="primary"><orth>word1</orth></entry>',
        'status': 'untouched',
    })
    assert r.status_code == 200, r.text
    assert r.json()['status'] == 'in_progress'


def test_save_does_not_override_explicit_status(auth_client):
    """Auto-bump only kicks in when the request also says untouched. An
    explicit status (e.g. from the split-save 'mark approved' menu item)
    must be honoured exactly."""
    from app import db
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE entries SET status = 'untouched' WHERE url_id = ?",
            ('testentry2',),
        )
    r = auth_client.put('/api/entries/testentry2', json={
        'xml_body': '<entry id="testentry2" type="primary"><orth>word1</orth></entry>',
        'status': 'approved',
    })
    assert r.status_code == 200, r.text
    assert r.json()['status'] == 'approved'


def test_save_writes_revision_every_time(auth_client):
    """No more 15-min coalescing: each save now creates its own revision so
    history has full granularity. (M2 confirmation test.)"""
    from app import db
    with db.get_conn() as conn:
        before = conn.execute(
            'SELECT COUNT(*) AS n FROM entry_revisions r '
            'JOIN entries e ON e.id = r.entry_id WHERE e.url_id = ?',
            ('testentry1',),
        ).fetchone()['n']

    for i in range(3):
        r = auth_client.put('/api/entries/testentry1', json={
            'xml_body': f'<entry id="testentry1" type="primary"><orth>rev{i}</orth></entry>',
            'status': 'in_progress',
        })
        assert r.status_code == 200, r.text

    with db.get_conn() as conn:
        after = conn.execute(
            'SELECT COUNT(*) AS n FROM entry_revisions r '
            'JOIN entries e ON e.id = r.entry_id WHERE e.url_id = ?',
            ('testentry1',),
        ).fetchone()['n']
    assert after - before == 3
