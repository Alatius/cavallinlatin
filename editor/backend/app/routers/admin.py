"""Admin endpoints: invite management, user listing."""

from __future__ import annotations

from fastapi import APIRouter, status

from .. import config, security
from ..deps import Admin, Conn
from ..models import (
    InviteAdminOut, InviteCreateIn, InviteCreateOut, UserAdminOut,
)


router = APIRouter()


@router.post('/invites', response_model=InviteCreateOut)
def create_invite(data: InviteCreateIn, conn: Conn, user: Admin):
    now = security.now()
    expires = now + config.INVITE_LIFETIME_SECONDS
    raw = security.new_invite_token()
    conn.execute(
        'INSERT INTO invites (token_hash, email, display_name, created_by, created_at, expires_at) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (security.hash_invite_token(raw), data.email, data.display_name,
         user['user_id'], now, expires),
    )
    return InviteCreateOut(token=raw, expires_at=expires)


@router.get('/invites', response_model=list[InviteAdminOut])
def list_invites(conn: Conn, user: Admin):
    rows = conn.execute(
        'SELECT token_hash, email, display_name, created_at, expires_at, consumed_at '
        'FROM invites ORDER BY created_at DESC'
    ).fetchall()
    return [InviteAdminOut(**dict(r)) for r in rows]


@router.delete('/invites/{token_hash}', status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(token_hash: str, conn: Conn, user: Admin):
    conn.execute('DELETE FROM invites WHERE token_hash = ?', (token_hash,))


@router.get('/users', response_model=list[UserAdminOut])
def list_users(conn: Conn, user: Admin):
    rows = conn.execute(
        'SELECT id, email, display_name, is_admin, created_at, last_login_at '
        'FROM users ORDER BY id'
    ).fetchall()
    return [
        UserAdminOut(
            id=r['id'], email=r['email'], display_name=r['display_name'],
            is_admin=bool(r['is_admin']),
            created_at=r['created_at'], last_login_at=r['last_login_at'],
        )
        for r in rows
    ]
