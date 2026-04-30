"""FastAPI dependencies: DB connection, current user, editor/admin gates."""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from . import config, db, security


def get_db():
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_db)]


def _session_cookie(session: str | None = Cookie(default=None, alias=config.COOKIE_NAME)) -> str | None:
    return session


def current_user(
    conn: Conn,
    session_id: Annotated[str | None, Depends(_session_cookie)],
) -> sqlite3.Row | None:
    if not session_id:
        return None
    now = security.now()
    row = conn.execute(
        'SELECT s.id AS session_id, s.expires_at, s.user_id, '
        '       u.email, u.display_name, u.is_admin '
        'FROM sessions s JOIN users u ON u.id = s.user_id '
        'WHERE s.id = ? AND s.expires_at > ?',
        (session_id, now),
    ).fetchone()
    if not row:
        return None
    new_exp = now + config.SESSION_LIFETIME_SECONDS
    conn.execute(
        'UPDATE sessions SET expires_at = ?, last_seen = ? WHERE id = ?',
        (new_exp, now, session_id),
    )
    return row


CurrentUser = Annotated[sqlite3.Row | None, Depends(current_user)]


def require_editor(user: CurrentUser) -> sqlite3.Row:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Inte inloggad')
    return user


Editor = Annotated[sqlite3.Row, Depends(require_editor)]


def require_admin(user: CurrentUser) -> sqlite3.Row:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Inte inloggad')
    if not user['is_admin']:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Administratörsbehörighet krävs')
    return user


Admin = Annotated[sqlite3.Row, Depends(require_admin)]
