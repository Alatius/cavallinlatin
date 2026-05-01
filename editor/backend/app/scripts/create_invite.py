"""Mint an invite token. Interactive prompt.

Prints the alatius.com redemption URL. The recipient sets their own
password on that page and becomes a regular (non-admin) user.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import config, db, security  # noqa: E402


def main() -> int:
    email = input('Email: ').strip()
    if not email:
        print('Email required.', file=sys.stderr)
        return 1
    name = input('Display name (optional): ').strip() or None

    now = security.now()
    expires = now + config.INVITE_LIFETIME_SECONDS
    raw = security.new_invite_token()

    with db.get_conn() as conn:
        existing = conn.execute(
            'SELECT id FROM users WHERE email = ?', (email,),
        ).fetchone()
        if existing:
            print(f'A user with email {email} already exists (id={existing["id"]}).',
                  file=sys.stderr)
            return 1

        pending = conn.execute(
            'SELECT token_hash, expires_at FROM invites '
            'WHERE email = ? AND consumed_at IS NULL AND expires_at > ?',
            (email, now),
        ).fetchone()
        if pending:
            print(f'Note: an unredeemed invite for {email} already exists '
                  f'(expires_at={pending["expires_at"]}).', file=sys.stderr)
            answer = input('Create another anyway? [y/N]: ').strip().lower()
            if answer != 'y':
                return 1

        row = conn.execute(
            'SELECT id FROM users WHERE is_admin = 1 ORDER BY id LIMIT 1',
        ).fetchone()
        if not row:
            print('No admin user found. Run create_admin.py first.', file=sys.stderr)
            return 1
        creator_id = row['id']

        conn.execute(
            'INSERT INTO invites (token_hash, email, display_name, created_by, '
            '                     created_at, expires_at) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (security.hash_invite_token(raw), email, name, creator_id, now, expires),
        )

    print('Invite created.')
    print(f'  Email:   {email}')
    if name:
        print(f'  Name:    {name}')
    print(f'  Expires: {config.INVITE_LIFETIME_SECONDS // 86400} days')
    print()
    print('Send this URL to the recipient:')
    print(f'  https://alatius.com/cavallinlatin/editor/invite/{raw}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
