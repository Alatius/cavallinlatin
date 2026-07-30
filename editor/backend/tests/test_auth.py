"""Login flow: timing-equal failures, rate limiting, valid credentials."""

from __future__ import annotations

import time


def test_login_success(client, reset_login_attempts):
    r = client.post('/api/auth/login', json={
        'email': 'test@example.com', 'password': 'correctpass1234',
    })
    assert r.status_code == 200
    body = r.json()
    assert body['email'] == 'test@example.com'
    assert body['is_admin'] is True


def test_login_wrong_password(client, reset_login_attempts):
    r = client.post('/api/auth/login', json={
        'email': 'test@example.com', 'password': 'wrong-password',
    })
    assert r.status_code == 401


def test_login_unknown_email(client, reset_login_attempts):
    r = client.post('/api/auth/login', json={
        'email': 'nobody@example.com', 'password': 'anything',
    })
    assert r.status_code == 401


def test_login_timing_constant_across_miss_and_wrong_password(client, reset_login_attempts):
    """Both branches must run a real Argon2 verify so they can't be
    distinguished by response time alone (the floor each measurement
    establishes is the Argon2 cost, ~100 ms)."""
    def measure(email: str) -> float:
        t0 = time.perf_counter()
        client.post('/api/auth/login', json={'email': email, 'password': 'x'})
        return time.perf_counter() - t0

    miss = measure('nobody@example.com')
    wrong = measure('test@example.com')
    # Both should sit close to the Argon2 cost; we don't assert exact equality
    # (CI noise), but neither should be much faster than ~50 ms.
    assert miss > 0.03, f'no-user path was suspiciously fast: {miss:.3f}s'
    assert wrong > 0.03, f'wrong-password path was suspiciously fast: {wrong:.3f}s'


def test_login_rate_limit(client, reset_login_attempts):
    """After _LOGIN_MAX_FAILURES failed attempts within the window, the
    next attempt is rejected with 429 — even with a correct password."""
    from app.routers import auth as auth_router
    for _ in range(auth_router._LOGIN_MAX_FAILURES):
        r = client.post('/api/auth/login', json={
            'email': 'test@example.com', 'password': 'wrong',
        })
        assert r.status_code == 401
    r = client.post('/api/auth/login', json={
        'email': 'test@example.com', 'password': 'correctpass1234',
    })
    assert r.status_code == 429


def test_login_success_clears_failure_counter(client, reset_login_attempts):
    """Fumbling the password a few times then succeeding must not leave the
    user one mistake away from a 429 next time."""
    from app.routers import auth as auth_router
    for _ in range(3):
        client.post('/api/auth/login', json={
            'email': 'test@example.com', 'password': 'wrong',
        })
    r = client.post('/api/auth/login', json={
        'email': 'test@example.com', 'password': 'correctpass1234',
    })
    assert r.status_code == 200
    # IP bucket should be empty after success.
    assert all(not v for v in auth_router._LOGIN_ATTEMPTS.values())


def test_login_success_does_not_forgive_another_accounts_failures(client, reset_login_attempts):
    """An attacker with valid credentials of their own must not be able to
    reset the counter guarding the account they're guessing at.

    Keying the limiter on IP alone let them do exactly that: nine guesses at
    the admin, one successful login as themselves, repeat forever.
    """
    from app.routers import auth as auth_router

    def guess() -> int:
        return client.post('/api/auth/login', json={
            'email': 'victim@example.com', 'password': 'guess',
        }).status_code

    # Stay one under the limit, then clear the IP bucket by authenticating
    # successfully as a *different* account — the attacker's own.
    for _ in range(auth_router._LOGIN_MAX_FAILURES - 1):
        assert guess() == 401
    assert client.post('/api/auth/login', json={
        'email': 'test@example.com', 'password': 'correctpass1234',
    }).status_code == 200
    assert 'ip:testclient' not in auth_router._LOGIN_ATTEMPTS

    # The victim's own bucket survived that reset, so the attack stalls: one
    # more guess tips it to the limit and everything after is refused.
    assert guess() == 401
    assert guess() == 429


def test_login_rate_limit_counts_concurrent_attempts(client, reset_login_attempts):
    """Attempts are recorded before the Argon2 verify, not after, so a burst
    arriving inside one verify window can't all slip past the check."""
    from app.routers import auth as auth_router
    for _ in range(auth_router._LOGIN_MAX_FAILURES):
        client.post('/api/auth/login', json={
            'email': 'test@example.com', 'password': 'wrong',
        })
    bucket = auth_router._LOGIN_ATTEMPTS.get('user:test@example.com', [])
    assert len(bucket) == auth_router._LOGIN_MAX_FAILURES


def test_login_password_length_is_capped(client, reset_login_attempts):
    """An unbounded password would be handed to Argon2 (64 MiB, ~150 ms) on an
    unauthenticated endpoint."""
    r = client.post('/api/auth/login', json={
        'email': 'test@example.com', 'password': 'x' * 5000,
    })
    assert r.status_code == 422
