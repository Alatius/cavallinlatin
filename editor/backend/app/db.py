"""SQLite connection and schema."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from . import config


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  email         TEXT NOT NULL UNIQUE,
  display_name  TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  is_admin      INTEGER NOT NULL DEFAULT 0,
  created_at    INTEGER NOT NULL,
  last_login_at INTEGER
);

CREATE TABLE IF NOT EXISTS entries (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  url_id           TEXT NOT NULL UNIQUE,
  xml_id           TEXT,
  xml_root         TEXT,
  type             TEXT NOT NULL,
  headword         TEXT NOT NULL,
  headword_sort    TEXT NOT NULL COLLATE NOCASE,
  alt_headwords    TEXT NOT NULL DEFAULT '[]',
  starting_column  TEXT,
  first_orth_y     REAL,
  status           TEXT NOT NULL DEFAULT 'untouched'
                    CHECK(status IN ('untouched','in_progress','approved')),
  xml_body         TEXT NOT NULL,
  plaintext        TEXT NOT NULL,
  sort_key         INTEGER NOT NULL UNIQUE,
  lock_user_id     INTEGER REFERENCES users(id),
  lock_expires_at  INTEGER,
  created_at       INTEGER NOT NULL,
  updated_at       INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS entries_headword_sort ON entries(headword_sort);
CREATE INDEX IF NOT EXISTS entries_status        ON entries(status);
CREATE INDEX IF NOT EXISTS entries_sort_key      ON entries(sort_key);
CREATE INDEX IF NOT EXISTS entries_xml_root      ON entries(xml_root);
CREATE INDEX IF NOT EXISTS entries_xml_id        ON entries(xml_id);

CREATE TABLE IF NOT EXISTS entry_revisions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_id    INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  xml_body    TEXT NOT NULL,
  status      TEXT NOT NULL,
  user_id     INTEGER REFERENCES users(id),
  created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS entry_revisions_entry_id ON entry_revisions(entry_id, created_at DESC);

CREATE TABLE IF NOT EXISTS entry_comments (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_id    INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  body        TEXT NOT NULL,
  created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS entry_comments_entry_id ON entry_comments(entry_id, created_at DESC);
CREATE INDEX IF NOT EXISTS entry_comments_created  ON entry_comments(created_at DESC);

CREATE TABLE IF NOT EXISTS invites (
  token_hash    TEXT PRIMARY KEY,
  email         TEXT,
  display_name  TEXT,
  created_by    INTEGER NOT NULL REFERENCES users(id),
  created_at    INTEGER NOT NULL,
  expires_at    INTEGER NOT NULL,
  consumed_at   INTEGER,
  consumed_user INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sessions (
  id          TEXT PRIMARY KEY,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at  INTEGER NOT NULL,
  expires_at  INTEGER NOT NULL,
  last_seen   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS sessions_user_id ON sessions(user_id);

CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
  headword, plaintext,
  content='entries', content_rowid='id',
  tokenize = "unicode61 remove_diacritics 2"
);

CREATE TRIGGER IF NOT EXISTS entries_fts_ai AFTER INSERT ON entries BEGIN
  INSERT INTO entries_fts(rowid, headword, plaintext)
  VALUES (new.id, new.headword, new.plaintext);
END;

CREATE TRIGGER IF NOT EXISTS entries_fts_ad AFTER DELETE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, headword, plaintext)
  VALUES ('delete', old.id, old.headword, old.plaintext);
END;

CREATE TRIGGER IF NOT EXISTS entries_fts_au AFTER UPDATE ON entries
WHEN old.headword <> new.headword OR old.plaintext <> new.plaintext
BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, headword, plaintext)
  VALUES ('delete', old.id, old.headword, old.plaintext);
  INSERT INTO entries_fts(rowid, headword, plaintext)
  VALUES (new.id, new.headword, new.plaintext);
END;
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = config.DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False is safe: FastAPI uses a new connection per
    # request (via get_db), and each connection is accessed sequentially
    # within one request, even if dep-resolution and handler run on
    # different threadpool threads.
    conn = sqlite3.connect(str(db_path), isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode = WAL;')
    conn.execute('PRAGMA foreign_keys = ON;')
    # If another connection holds the write lock, wait up to 5s instead of
    # erroring immediately — handlers using transaction() under load.
    conn.execute('PRAGMA busy_timeout = 5000;')
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Wrap a block of statements in BEGIN IMMEDIATE / COMMIT.

    `connect()` opens with isolation_level=None (autocommit), so multi-
    statement handlers must explicitly demarcate atomic units. IMMEDIATE
    grabs the write lock up front, avoiding the read→write upgrade race
    that DEFERRED would expose under concurrent writers.
    """
    conn.execute('BEGIN IMMEDIATE')
    try:
        yield
    except BaseException:
        conn.execute('ROLLBACK')
        raise
    conn.execute('COMMIT')


# Bump when the schema changes, and add the statements that take an existing
# database from the previous version to the new one.
#
# This exists because `CREATE TABLE IF NOT EXISTS` builds a correct database
# from scratch and then silently does nothing to one that already exists. So
# adding a column to `entries` works locally against a fresh DB, does nothing
# at all to the deployed one, and the app fails at runtime on the first query
# that names it. deploy.sh has no migration step to notice the difference.
#
# Version 1 is the baseline: whatever SCHEMA above produces. Existing
# databases report user_version 0 and are simply stamped, since they already
# match. A future change means SCHEMA_VERSION = 2 plus MIGRATIONS[2] = (...),
# with the SCHEMA text updated too so fresh databases skip the migration.
SCHEMA_VERSION = 1
MIGRATIONS: dict[int, tuple[str, ...]] = {}


def migrate(conn: sqlite3.Connection) -> None:
    """Bring an existing database up to SCHEMA_VERSION."""
    version: int = conn.execute('PRAGMA user_version').fetchone()[0]
    if version >= SCHEMA_VERSION:
        return
    # Only take the write lock when there is actually something to do —
    # init_schema runs on every connection.
    with transaction(conn):
        for target in range(version + 1, SCHEMA_VERSION + 1):
            for stmt in MIGRATIONS.get(target, ()):
                conn.execute(stmt)
        # PRAGMA doesn't take bound parameters; the value is our own int.
        conn.execute(f'PRAGMA user_version = {int(SCHEMA_VERSION)}')


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    migrate(conn)


@contextmanager
def get_conn(db_path: Path | None = None):
    conn = connect(db_path)
    try:
        init_schema(conn)
        yield conn
    finally:
        conn.close()
