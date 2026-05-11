"""Pydantic request/response models."""

from __future__ import annotations

import json
from typing import Literal, get_args

from pydantic import BaseModel, EmailStr, Field


Status = Literal[
    'untouched', 'in_progress', 'approved',
]

EntryType = Literal[
    'primary', 'derived', 'proper', 'plain', 'reference', 'etym',
]

ENTRY_TYPES: frozenset[str] = frozenset(get_args(EntryType))


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    is_admin: bool


class UserAdminOut(UserOut):
    created_at: int
    last_login_at: int | None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class LockInfo(BaseModel):
    user_id: int
    display_name: str
    expires_at: int  # unix seconds


class EntrySummary(BaseModel):
    url_id: str
    headword: str
    alt_headwords: list[str] = []
    type: EntryType
    status: Status
    comment_count: int = 0

    @classmethod
    def from_row(cls, row) -> 'EntrySummary':
        # `comment_count` is optional on the row: list endpoints that don't
        # need it (e.g. paginated /entries?status=…) skip the join, while
        # /headwords supplies the per-entry total.
        keys = row.keys() if hasattr(row, 'keys') else ()
        return cls(
            url_id=row['url_id'],
            headword=row['headword'],
            alt_headwords=json.loads(row['alt_headwords'] or '[]'),
            type=row['type'],
            status=row['status'],
            comment_count=row['comment_count'] if 'comment_count' in keys else 0,
        )


class EntryOut(BaseModel):
    url_id: str
    xml_id: str | None
    xml_root: str | None
    type: EntryType
    headword: str
    alt_headwords: list[str] = []
    status: Status
    xml_body: str
    starting_column: str | None
    prev_url_id: str | None
    next_url_id: str | None
    updated_at: int
    lock: LockInfo | None = None
    # Headword + url_id of the entry whose xml_id matches this entry's
    # xml_root, used by the toolbar breadcrumb. Null for primary/proper
    # entries (which are roots themselves) and for orphans whose root is
    # missing.
    root_headword: str | None = None
    root_url_id: str | None = None


class EntryList(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[EntrySummary]


class EntryGroupItem(BaseModel):
    """A single member of an etymological group, with just the fields the
    public group view needs to render. Drops lock/prev/next/updated_at — those
    are editor concerns and don't apply to non-focus members in a group."""
    url_id: str
    xml_id: str | None
    xml_root: str | None
    type: EntryType
    headword: str
    alt_headwords: list[str] = []
    status: Status
    xml_body: str
    starting_column: str | None

    @classmethod
    def from_row(cls, row) -> 'EntryGroupItem':
        return cls(
            url_id=row['url_id'], xml_id=row['xml_id'], xml_root=row['xml_root'],
            type=row['type'], headword=row['headword'],
            alt_headwords=json.loads(row['alt_headwords'] or '[]'),
            status=row['status'], xml_body=row['xml_body'],
            starting_column=row['starting_column'],
        )


class EntryGroupOut(BaseModel):
    focus_url_id: str
    # url_id of the head (the primary/proper entry that anchors the group),
    # or None when the group has no head — e.g. a reference entry, an isolated
    # plain entry, or an orphan whose root is missing from the DB.
    head_url_id: str | None
    # Members in document (sort_key) order. The head, if any, is items[0].
    items: list[EntryGroupItem]


class EntrySaveIn(BaseModel):
    xml_body: str
    status: Status
    # The updated_at the client believes it's editing on top of. If supplied
    # and the server's row has advanced, the save is rejected with 409 so a
    # stale draft can't silently overwrite a newer save (e.g., when both
    # editors' soft locks lapsed between their saves). Optional so admin
    # tooling and tests can opt out.
    expected_updated_at: int | None = None


class EntrySplitIn(BaseModel):
    # Character offset into the saved xml_body at which to split. Must land
    # between two top-level children of the root <entry>; the server
    # rejects offsets that produce malformed halves or a second half that
    # lacks an <orth>.
    offset: int = Field(ge=0)


class EntrySplitOut(BaseModel):
    # Updated summary of the surviving (first) entry. Its url_id is
    # unchanged, but its alt_headwords typically shrinks (any <orth>s that
    # moved to the new half are now absent). The frontend uses this to
    # patch the sidebar row in place.
    source_entry: EntrySummary
    # Summary of the newly-created entry; its url_id matches its xml_id,
    # derived from the first <orth> in the new half with homograph
    # numbering bumped to avoid id collisions. The frontend splices this
    # row into the index right after the source without refetching the
    # full ~35k-row /headwords list.
    new_entry: EntrySummary


class CommentOut(BaseModel):
    id: int
    user_id: int
    display_name: str
    body: str
    created_at: int


class CommentCreateIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class ActivityItem(BaseModel):
    url_id: str
    headword: str
    user_id: int | None
    display_name: str | None
    snippet: str | None  # comment body for /activity/comments; None for edits
    at: int
    count: int  # total comments / revisions for this entry


class RevisionMeta(BaseModel):
    """One snapshot in an entry's history. `id` is "current" or
    str(entry_revisions.id). `saved_by_*` is null only for the imported
    snapshot (no save event behind it)."""
    id: str
    is_current: bool
    status: Status
    saved_at: int
    saved_by_id: int | None
    saved_by: str | None


class RevisionContent(RevisionMeta):
    xml_body: str


class InviteCreateIn(BaseModel):
    email: EmailStr
    display_name: str | None = None


class InviteCreateOut(BaseModel):
    token: str
    expires_at: int


class InviteInfoOut(BaseModel):
    email: str | None
    display_name: str | None
    expires_at: int


class InviteAdminOut(BaseModel):
    token_hash: str
    email: str | None
    display_name: str | None
    created_at: int
    expires_at: int
    consumed_at: int | None


class InviteAcceptIn(BaseModel):
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1)


class SearchHit(BaseModel):
    url_id: str
    headword: str
    # Snippet text where matched runs are wrapped in U+0001 / U+0002 control
    # markers. The frontend splits and renders <mark>…</mark> via React, so
    # no HTML ever flows through dangerouslySetInnerHTML.
    snippet: str


class SearchOut(BaseModel):
    query: str
    total: int
    items: list[SearchHit]


class UrlIdOut(BaseModel):
    url_id: str
