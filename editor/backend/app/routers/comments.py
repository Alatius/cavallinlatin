"""Per-entry comments: list and create.

Comments are independent of saves. Anyone with editor access can leave one;
they show up in the entry's slide-down panel and feed the activity page.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from .. import security
from ..deps import Conn, Editor
from ..models import CommentCreateIn, CommentOut


router = APIRouter()


def _entry_id(conn, url_id: str) -> int:
    row = conn.execute('SELECT id FROM entries WHERE url_id = ?', (url_id,)).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return row['id']


@router.get('/{url_id}/comments', response_model=list[CommentOut])
def list_comments(url_id: str, conn: Conn, _: Editor):
    entry_id = _entry_id(conn, url_id)
    rows = conn.execute(
        'SELECT c.id, c.user_id, c.body, c.created_at, u.display_name '
        'FROM entry_comments c LEFT JOIN users u ON u.id = c.user_id '
        'WHERE c.entry_id = ? ORDER BY c.created_at ASC',
        (entry_id,),
    ).fetchall()
    return [
        CommentOut(
            id=r['id'], user_id=r['user_id'],
            display_name=r['display_name'] or '',
            body=r['body'], created_at=r['created_at'],
        )
        for r in rows
    ]


@router.post(
    '/{url_id}/comments',
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(url_id: str, data: CommentCreateIn, conn: Conn, user: Editor):
    body = data.body.strip()
    if not body:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Kommentaren är tom')
    entry_id = _entry_id(conn, url_id)
    now = security.now()
    cur = conn.execute(
        'INSERT INTO entry_comments (entry_id, user_id, body, created_at) '
        'VALUES (?, ?, ?, ?)',
        (entry_id, user['user_id'], body, now),
    )
    return CommentOut(
        id=cur.lastrowid, user_id=user['user_id'],
        display_name=user['display_name'],
        body=body, created_at=now,
    )
