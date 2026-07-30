"""Search endpoint: snippet uses control-char markers, no HTML."""

from __future__ import annotations


def test_lookup_known_headword(client):
    # testentry2 keeps its seeded headword for the whole session; testentry1
    # gets mutated by the save tests so its headword can't be relied on.
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


def test_search_survives_fts5_metacharacters_and_control_chars(client):
    """/api/search is unauthenticated, so no input may reach FTS5 in a form it
    rejects. A NUL used to escape _sanitize and surface as a 500, because
    FTS5's query parser is C-string based and saw an unterminated phrase.
    """
    hostile = [
        '\x00', 'a\x00b', '\x01\x02', 'a\x7fb',      # control characters
        '"', 'a"b', "'", '\\',                        # quoting
        '*', '^a', 'a*', '-a', '(((', '{1}',          # FTS5 syntax
        'a OR b', 'a AND', 'NEAR(', 'NEAR(a b, 2)',   # operators
        'headword:x', 'a:b:c',                        # column filters
        '', '   ', '#$%&/()=?', 'ss' * 40,
    ]
    for q in hostile:
        r = client.get('/api/search', params={'q': q})
        assert r.status_code == 200, f'q={q!r} -> {r.status_code} {r.text[:120]}'
        assert r.json()['total'] >= 0


def test_search_control_chars_keep_word_boundaries(client):
    """Controls fold to a space rather than vanishing, so 'word\\x001' must not
    be silently glued into the real term 'word1'."""
    r = client.get('/api/search', params={'q': 'word\x001'})
    assert r.status_code == 200


def test_headwords_endpoint(client):
    r = client.get('/api/headwords')
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2
    assert {'url_id', 'headword', 'type', 'status'}.issubset(items[0].keys())
