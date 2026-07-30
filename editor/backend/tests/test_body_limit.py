"""Request body ceiling.

A Content-Length check alone is bypassable: a chunked request carries no such
header, so the body streams into memory unchecked. These tests pin both paths.
"""

from __future__ import annotations

import json

from app.main import MAX_BODY_BYTES


def _oversized_payload() -> bytes:
    return json.dumps({
        'email': 'test@example.com',
        'password': 'x' * (MAX_BODY_BYTES + 1000),
    }).encode()


def test_oversized_body_with_content_length_is_rejected(client, reset_login_attempts):
    r = client.post(
        '/api/auth/login',
        content=_oversized_payload(),
        headers={'Content-Type': 'application/json'},
    )
    assert r.status_code == 413


def test_oversized_chunked_body_is_rejected(client, reset_login_attempts):
    """No Content-Length header at all — httpx streams an iterator as chunked."""
    payload = _oversized_payload()

    def chunks():
        for i in range(0, len(payload), 64 * 1024):
            yield payload[i:i + 64 * 1024]

    r = client.post(
        '/api/auth/login',
        content=chunks(),
        headers={'Content-Type': 'application/json'},
    )
    assert r.status_code == 413


def test_normal_body_still_passes(client, reset_login_attempts):
    r = client.post('/api/auth/login', json={
        'email': 'test@example.com', 'password': 'correctpass1234',
    })
    assert r.status_code == 200
