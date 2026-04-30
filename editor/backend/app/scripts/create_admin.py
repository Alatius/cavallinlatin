"""Seed the first admin user (Johan). Interactive password prompt."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import db, security  # noqa: E402


DEFAULT_EMAIL = 'johan.winge@gmail.com'
DEFAULT_NAME = 'Johan Winge'


def main() -> int:
    email = input(f'Email [{DEFAULT_EMAIL}]: ').strip() or DEFAULT_EMAIL
    name = input(f'Display name [{DEFAULT_NAME}]: ').strip() or DEFAULT_NAME

    while True:
        pw1 = getpass.getpass('Password (min 8 chars): ')
        if len(pw1) < 8:
            print('Too short.')
            continue
        pw2 = getpass.getpass('Password (again): ')
        if pw1 != pw2:
            print('Mismatch.')
            continue
        break

    now = security.now()
    pw_hash = security.hash_password(pw1)
    with db.get_conn() as conn:
        existing = conn.execute(
            'SELECT id FROM users WHERE email = ?', (email,),
        ).fetchone()
        if existing:
            conn.execute(
                'UPDATE users SET display_name = ?, password_hash = ?, is_admin = 1 '
                'WHERE id = ?',
                (name, pw_hash, existing['id']),
            )
            print(f'Admin updated: {email}')
        else:
            conn.execute(
                'INSERT INTO users (email, display_name, password_hash, is_admin, created_at) '
                'VALUES (?, ?, ?, 1, ?)',
                (email, name, pw_hash, now),
            )
            print(f'Admin created: {email}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
