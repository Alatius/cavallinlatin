"""Entry soft locks: acquire, keepalive, release."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from .. import config, db, security
from ..deps import Conn, Editor
from ..models import LockInfo


router = APIRouter()


@router.post('/{url_id}/lock', response_model=LockInfo)
def acquire_lock(url_id: str, conn: Conn, user: Editor):
    now = security.now()
    expires = now + config.LOCK_TTL_SECONDS
    # Atomic check-and-set: another editor could otherwise pass the SELECT
    # in parallel and both think they grabbed the lock.
    with db.transaction(conn):
        row = conn.execute(
            'SELECT e.id, e.lock_user_id, e.lock_expires_at, u.display_name '
            'FROM entries e LEFT JOIN users u ON u.id = e.lock_user_id '
            'WHERE e.url_id = ?',
            (url_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        held_by_other = (
            row['lock_user_id'] and row['lock_user_id'] != user['user_id']
            and row['lock_expires_at'] and row['lock_expires_at'] > now
        )
        if held_by_other:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={
                    'user_id': row['lock_user_id'],
                    'display_name': row['display_name'] or '',
                    'expires_at': row['lock_expires_at'],
                },
            )

        conn.execute(
            'UPDATE entries SET lock_user_id = ?, lock_expires_at = ? WHERE id = ?',
            (user['user_id'], expires, row['id']),
        )
    return LockInfo(
        user_id=user['user_id'],
        display_name=user['display_name'],
        expires_at=expires,
    )


@router.put('/{url_id}/lock', response_model=LockInfo)
def keepalive_lock(url_id: str, conn: Conn, user: Editor):
    expires = security.now() + config.LOCK_TTL_SECONDS
    with db.transaction(conn):
        row = conn.execute(
            'SELECT id, lock_user_id, lock_expires_at FROM entries WHERE url_id = ?',
            (url_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        if row['lock_user_id'] != user['user_id']:
            raise HTTPException(status.HTTP_409_CONFLICT, 'Låset innehas inte av dig')
        conn.execute(
            'UPDATE entries SET lock_expires_at = ? WHERE id = ?',
            (expires, row['id']),
        )
    return LockInfo(
        user_id=user['user_id'], display_name=user['display_name'],
        expires_at=expires,
    )


@router.delete('/{url_id}/lock', status_code=status.HTTP_204_NO_CONTENT)
def release_lock(url_id: str, conn: Conn, user: Editor):
    conn.execute(
        'UPDATE entries SET lock_user_id = NULL, lock_expires_at = NULL '
        'WHERE url_id = ? AND lock_user_id = ?',
        (url_id, user['user_id']),
    )
