"""Shared pytest fixtures.

Sets up an isolated SQLite DB and seeds a user and a couple of entries so
each test module can hit the FastAPI surface end-to-end.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Set env vars BEFORE the app imports config.py, since config reads env
# at import time.
_TMP_DB = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
_TMP_DB.close()
os.environ['CAVALLIN_DB_PATH'] = _TMP_DB.name
os.environ['CAVALLIN_COOKIE_NAME'] = 'cav_test'
os.environ['CAVALLIN_COOKIE_SECURE'] = 'false'
os.environ['CAVALLIN_BASE_PATH'] = ''  # cookie path becomes '/'.

# Make backend/ importable as a package root regardless of where pytest runs.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope='session')
def app():
    from app.main import app as _app
    return _app


@pytest.fixture(scope='session', autouse=True)
def seed(app):
    """Seed an admin user and two entries once for the whole test session."""
    from app import db, security
    pw_hash = security.hash_password('correctpass1234')
    now = security.now()
    with db.get_conn() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO users (email, display_name, password_hash, is_admin, created_at) '
            'VALUES (?, ?, ?, 1, ?)',
            ('test@example.com', 'Test', pw_hash, now),
        )
        for i, url in enumerate(['testentry1', 'testentry2']):
            xml = f'<entry id="{url}" type="primary"><orth>word{i}</orth> contents</entry>'
            conn.execute(
                'INSERT OR IGNORE INTO entries '
                '(url_id, type, headword, headword_sort, xml_body, plaintext, '
                ' sort_key, created_at, updated_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (url, 'primary', f'word{i}', f'word{i}', xml,
                 f'word{i} contents', (i + 1) * 100, now, now),
            )
    yield


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def auth_client(app, reset_login_attempts):
    """Fresh TestClient with a session cookie installed; intentionally
    separate from `client` so tests can hold two independent sessions."""
    c = TestClient(app)
    r = c.post('/api/auth/login', json={
        'email': 'test@example.com', 'password': 'correctpass1234',
    })
    assert r.status_code == 200, r.text
    return c


@pytest.fixture
def reset_login_attempts():
    """Clear in-memory rate-limit state before and after the test."""
    from app.routers import auth
    auth._LOGIN_ATTEMPTS.clear()
    yield
    auth._LOGIN_ATTEMPTS.clear()
