"""Login, logout, session introspection, invite acceptance."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException, Request, Response, status

from .. import config, db, security
from ..deps import Conn, CurrentUser
from ..models import InviteAcceptIn, InviteInfoOut, LoginIn, UserOut


router = APIRouter()


# In-memory failed-login tracker. Single-worker deployment, so no shared
# state needed. The list per IP is pruned to the rolling window on every
# check, so memory stays bounded by the number of currently-attacking IPs.
_LOGIN_ATTEMPTS: dict[str, list[int]] = {}
_LOGIN_WINDOW = 5 * 60  # seconds
_LOGIN_MAX_FAILURES = 10

# Hash compared against when the email doesn't exist. Argon2 verify against
# this takes the same ~150 ms as a real verify, so an attacker can't tell
# which emails exist by login response timing alone.
_DUMMY_HASH = security.hash_password('cavallin-login-timing-placeholder')


def _client_ip(request: Request) -> str:
    return (request.client.host if request.client else None) or 'unknown'


def _check_login_rate(ip: str) -> None:
    cutoff = security.now() - _LOGIN_WINDOW
    attempts = [t for t in _LOGIN_ATTEMPTS.get(ip, []) if t > cutoff]
    _LOGIN_ATTEMPTS[ip] = attempts
    if len(attempts) >= _LOGIN_MAX_FAILURES:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            'För många misslyckade försök; försök igen om några minuter',
        )


def _record_login_failure(ip: str) -> None:
    _LOGIN_ATTEMPTS.setdefault(ip, []).append(security.now())


@router.post('/login', response_model=UserOut)
def login(data: LoginIn, response: Response, conn: Conn, request: Request):
    ip = _client_ip(request)
    _check_login_rate(ip)

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
        _record_login_failure(ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Felaktig e-post eller lösenord')

    # Successful login: forgive prior failures so a user who fumbled their
    # password before getting it right doesn't get locked out next time.
    _LOGIN_ATTEMPTS.pop(ip, None)

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
