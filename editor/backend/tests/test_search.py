"""Search endpoint: snippet uses control-char markers, no HTML."""

from __future__ import annotations


def test_lookup_known_headword(client):
    # testentry2 is read-only across the test suite; testentry1 gets mutated
    # by the save tests so its headword can't be relied on.
    r = client.get('/api/lookup', params={'q': 'word1'})
    assert r.status_code == 200
    assert r.json() == {'url_id': 'testentry2'}


def test_lookup_unknown_headword(client):
    r = client.get('/api/lookup', params={'q': 'no-such-headword-xyzzy'})
    assert r.status_code == 404


def test_search_returns_marker_wrapped_snippets(client):
    r = client.get('/api/search', params={'q': 'word1'})
    assert r.status_code == 200
    body = r.json()
    assert body['total'] >= 1
    snippet = body['items'][0]['snippet']
    # The match should be wrapped in U+0001/U+0002, not <mark>…</mark>.
    assert '\x01' in snippet
    assert '\x02' in snippet
    assert '<mark>' not in snippet
    assert '</mark>' not in snippet


def test_headwords_endpoint(client):
    r = client.get('/api/headwords')
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2
    assert {'url_id', 'headword', 'type', 'status'}.issubset(items[0].keys())
