"""Password hashing, session tokens, invite tokens."""

from __future__ import annotations

import hashlib
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from . import config


_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(hash_value: str, password: str) -> bool:
    try:
        _hasher.verify(hash_value, password)
    except VerifyMismatchError:
        return False
    return True


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def new_invite_token() -> str:
    return secrets.token_urlsafe(24)


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def now() -> int:
    return int(time.time())


def session_cookie_params() -> dict:
    return dict(
        key=config.COOKIE_NAME,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite='strict',
        path=config.BASE_PATH + '/',
        max_age=config.SESSION_LIFETIME_SECONDS,
    )
