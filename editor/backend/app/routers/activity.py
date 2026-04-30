"""Activity feed: most-recently-commented and most-recently-edited entries.

One row per entry, surfacing the latest event so a low-volume editor can find
what's been touched without scanning the whole index.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..deps import Conn, Editor
from ..models import ActivityItem


router = APIRouter()


@router.get('/comments', response_model=list[ActivityItem])
def latest_commented(
    conn: Conn,
    _: Editor,
    limit: int = Query(default=50, ge=1, le=200),
):
    # Window the latest comment per entry, then join the entry + author. The
    # subquery's GROUP BY collapses each entry to its most recent row; the
    # outer JOIN gets the body/author from that exact row via (entry_id, max).
    rows = conn.execute(
        '''
        WITH latest AS (
          SELECT entry_id, MAX(created_at) AS at, COUNT(*) AS n
          FROM entry_comments GROUP BY entry_id
        )
        SELECT e.url_id, e.headword, c.user_id, u.display_name,
               c.body AS snippet, latest.at, latest.n
        FROM latest
        JOIN entries e ON e.id = latest.entry_id
        JOIN entry_comments c
          ON c.entry_id = latest.entry_id AND c.created_at = latest.at
        LEFT JOIN users u ON u.id = c.user_id
        ORDER BY latest.at DESC
        LIMIT ?
        ''',
        (limit,),
    ).fetchall()
    return [
        ActivityItem(
            url_id=r['url_id'], headword=r['headword'],
            user_id=r['user_id'], display_name=r['display_name'],
            snippet=r['snippet'], at=r['at'], count=r['n'],
        )
        for r in rows
    ]


@router.get('/edits', response_model=list[ActivityItem])
def latest_edited(
    conn: Conn,
    _: Editor,
    limit: int = Query(default=50, ge=1, le=200),
):
    # entries.updated_at is bumped on every save, so we can rank entries by it
    # directly without joining entry_revisions. The author / revision count
    # come from entry_revisions for entries that have ever been saved by an
    # editor (untouched imports stay absent from the feed).
    # last_rev: the most recent revision per entry, picked by MAX(id) so
    # multiple revisions saved within the same second still resolve uniquely.
    rows = conn.execute(
        '''
        WITH rev AS (
          SELECT entry_id, COUNT(*) AS n, MAX(id) AS last_id
          FROM entry_revisions GROUP BY entry_id
        )
        SELECT e.url_id, e.headword, r.user_id, u.display_name,
               e.updated_at AS at, rev.n AS n
        FROM entries e
        JOIN rev ON rev.entry_id = e.id
        LEFT JOIN entry_revisions r ON r.id = rev.last_id
        LEFT JOIN users u ON u.id = r.user_id
        ORDER BY e.updated_at DESC
        LIMIT ?
        ''',
        (limit,),
    ).fetchall()
    return [
        ActivityItem(
            url_id=r['url_id'], headword=r['headword'],
            user_id=r['user_id'], display_name=r['display_name'],
            snippet=None, at=r['at'], count=r['n'],
        )
        for r in rows
    ]
