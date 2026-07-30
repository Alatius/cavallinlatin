"""Login, logout, session introspection, invite acceptance."""

from __future__ import annotations

import sqlite3
import threading

from fastapi import APIRouter, HTTPException, Request, Response, status

from .. import config, db, security
from ..deps import Conn, CurrentUser
from ..models import InviteAcceptIn, InviteInfoOut, LoginIn, UserOut


router = APIRouter()


# In-memory failed-login tracker. Single-worker deployment, so no shared
# state needed; a lock because the endpoint is sync and therefore runs on
# Starlette's threadpool.
#
# Buckets are keyed 'ip:<addr>' AND 'user:<email>', and both must be under the
# limit. The per-account bucket is what stops an attacker who can produce
# successful logins of their own — an invited editor guessing the admin's
# password, say. Keying on IP alone let them reset the counter every tenth
# guess by logging into their own account, since success forgives the whole IP.
_LOGIN_ATTEMPTS: dict[str, list[int]] = {}
_LOGIN_LOCK = threading.Lock()
_LOGIN_WINDOW = 5 * 60  # seconds
_LOGIN_MAX_FAILURES = 10
# Above this many tracked buckets, sweep the whole dict instead of only the
# keys being looked at, so IPs that attacked once and left are reclaimed.
_LOGIN_SWEEP_AT = 1024

# Hash compared against when the email doesn't exist. Argon2 verify against
# this takes the same ~150 ms as a real verify, so an attacker can't tell
# which emails exist by login response timing alone.
_DUMMY_HASH = security.hash_password('cavallin-login-timing-placeholder')


def _client_ip(request: Request) -> str:
    return (request.client.host if request.client else None) or 'unknown'


def _prune(key: str, cutoff: int) -> list[int]:
    """Drop out-of-window failures for `key`, forgetting the key if empty."""
    attempts = [t for t in _LOGIN_ATTEMPTS.get(key, []) if t > cutoff]
    if attempts:
        _LOGIN_ATTEMPTS[key] = attempts
    else:
        _LOGIN_ATTEMPTS.pop(key, None)
    return attempts


def _check_and_record(keys: tuple[str, ...]) -> None:
    """429 if any bucket is over the limit; otherwise record an attempt.

    Recording happens here rather than after the password check because the
    Argon2 verify takes ~150 ms, and a burst arriving inside that window would
    otherwise all pass the check before any of them recorded a failure. The
    attempt is forgiven again by _forget() when the login succeeds.
    """
    now = security.now()
    cutoff = now - _LOGIN_WINDOW
    with _LOGIN_LOCK:
        if len(_LOGIN_ATTEMPTS) > _LOGIN_SWEEP_AT:
            for stale in [k for k in _LOGIN_ATTEMPTS if k not in keys]:
                _prune(stale, cutoff)
        over = any(len(_prune(key, cutoff)) >= _LOGIN_MAX_FAILURES for key in keys)
        if not over:
            for key in keys:
                _LOGIN_ATTEMPTS.setdefault(key, []).append(now)
    if over:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            'För många misslyckade försök; försök igen om några minuter',
        )


def _forget(keys: tuple[str, ...]) -> None:
    """Clear the buckets for a successful login.

    Only the buckets belonging to *this* login: another account's bucket must
    survive, or authenticating as yourself would reset the counter guarding
    the account you are guessing at.
    """
    with _LOGIN_LOCK:
        for key in keys:
            _LOGIN_ATTEMPTS.pop(key, None)


@router.post('/login', response_model=UserOut)
def login(data: LoginIn, response: Response, conn: Conn, request: Request):
    keys = (f'ip:{_client_ip(request)}', f'user:{data.email.lower()}')
    _check_and_record(keys)

    row = conn.execute(
        'SELECT id, email, display_name, password_hash, is_admin '
        'FROM users WHERE email = ?',
        (data.email,),
    ).fetchone()
    # Always run verify against a real Argon2 hash so timing is constant
    # regardless of whether the email exists.
    pw_hash = row['password_hash'] if row else _DUMMY_HASH
    pw_ok = security.verify_password(pw_hash, data.password)
    if not row or not pw_ok:
        # The attempt was already recorded by _check_and_record.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Felaktig e-post eller lösenord')

    # Successful login: forgive this IP's and this account's prior failures so
    # a user who fumbled their password before getting it right isn't locked
    # out next time. Other accounts' buckets are deliberately left alone.
    _forget(keys)

    now = security.now()
    token = security.new_session_token()
    with db.transaction(conn):
        conn.execute(
            'INSERT INTO sessions (id, user_id, created_at, expires_at, last_seen) '
            'VALUES (?, ?, ?, ?, ?)',
            (token, row['id'], now, now + config.SESSION_LIFETIME_SECONDS, now),
        )
        conn.execute(
            'UPDATE users SET last_login_at = ? WHERE id = ?',
            (now, row['id']),
        )
    response.set_cookie(value=token, **security.session_cookie_params())
    return UserOut(
        id=row['id'], email=row['email'], display_name=row['display_name'],
        is_admin=bool(row['is_admin']),
    )


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, conn: Conn, user: CurrentUser):
    if user:
        conn.execute('DELETE FROM sessions WHERE id = ?', (user['session_id'],))
    response.delete_cookie(key=config.COOKIE_NAME, path=config.BASE_PATH + '/')


@router.get('/me', response_model=UserOut)
def me(user: CurrentUser):
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    return UserOut(
        id=user['user_id'], email=user['email'], display_name=user['display_name'],
        is_admin=bool(user['is_admin']),
    )


@router.get('/invite/{token}', response_model=InviteInfoOut)
def invite_info(token: str, conn: Conn):
    row = _lookup_invite(conn, token)
    return InviteInfoOut(
        email=row['email'], display_name=row['display_name'],
        expires_at=row['expires_at'],
    )


@router.post('/invite/{token}', response_model=UserOut)
def invite_accept(
    token: str, data: InviteAcceptIn, response: Response, conn: Conn,
):
    inv = _lookup_invite(conn, token)
    if not inv['email']:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'Inbjudan saknar e-postadress; be administratören skapa en ny',
        )
    now = security.now()
    pw_hash = security.hash_password(data.password)
    sess = security.new_session_token()
    # Atomic: create user, mark invite consumed, open session. Argon2 hashing
    # is the slow step and runs outside the transaction.
    with db.transaction(conn):
        try:
            cur = conn.execute(
                'INSERT INTO users (email, display_name, password_hash, is_admin, created_at) '
                'VALUES (?, ?, ?, 0, ?)',
                (inv['email'], data.display_name, pw_hash, now),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, 'E-postadressen används redan') from None
        user_id = cur.lastrowid
        conn.execute(
            'UPDATE invites SET consumed_at = ?, consumed_user = ? WHERE token_hash = ?',
            (now, user_id, inv['token_hash']),
        )
        conn.execute(
            'INSERT INTO sessions (id, user_id, created_at, expires_at, last_seen) '
            'VALUES (?, ?, ?, ?, ?)',
            (sess, user_id, now, now + config.SESSION_LIFETIME_SECONDS, now),
        )
    response.set_cookie(value=sess, **security.session_cookie_params())
    return UserOut(
        id=user_id, email=inv['email'], display_name=data.display_name, is_admin=False,
    )


def _lookup_invite(conn: sqlite3.Connection, token: str) -> sqlite3.Row:
    th = security.hash_invite_token(token)
    row = conn.execute(
        'SELECT token_hash, email, display_name, expires_at, consumed_at '
        'FROM invites WHERE token_hash = ?',
        (th,),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Inbjudan hittades inte')
    if row['consumed_at']:
        raise HTTPException(status.HTTP_410_GONE, 'Inbjudan har redan använts')
    if row['expires_at'] < security.now():
        raise HTTPException(status.HTTP_410_GONE, 'Inbjudan har löpt ut')
    return row
