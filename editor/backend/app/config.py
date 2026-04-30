"""Runtime configuration, driven by environment variables."""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
EDITOR_DIR = BACKEND_DIR.parent


def _path(env_var: str, default_rel: str) -> Path:
    v = os.environ.get(env_var)
    if v:
        p = Path(v).expanduser()
        return p if p.is_absolute() else (EDITOR_DIR / p).resolve()
    return EDITOR_DIR / default_rel


DB_PATH = _path('CAVALLIN_DB_PATH', 'data/cavallin.db')
COLUMNS_DIR = _path('CAVALLIN_COLUMNS_DIR', 'data/columns')
XML_PATH = _path('CAVALLIN_XML_PATH', 'data/cavallinlatin.xml')
# Strip a trailing slash so callers that build paths as `BASE_PATH + '/'`
# (cookie path, route prefixes) don't end up with a double slash if the
# operator wrote the env var as '/cavallinlatin/'.
BASE_PATH = os.environ.get('CAVALLIN_BASE_PATH', '/cavallinlatin').rstrip('/')
COOKIE_NAME = os.environ.get('CAVALLIN_COOKIE_NAME', 'cavallin_session')
COOKIE_SECURE = os.environ.get('CAVALLIN_COOKIE_SECURE', 'false').lower() == 'true'

SESSION_LIFETIME_SECONDS = 30 * 24 * 60 * 60
LOCK_TTL_SECONDS = 15 * 60
INVITE_LIFETIME_SECONDS = 14 * 24 * 60 * 60
