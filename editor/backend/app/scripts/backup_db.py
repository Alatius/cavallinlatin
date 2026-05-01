"""Snapshot the SQLite database to editor/data/backups/cavallin-YYYYMMDD.db.

Keeps the most recent KEEP_LAST snapshots and prunes anything older."""

from __future__ import annotations

import datetime as dt
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import config  # noqa: E402


KEEP_LAST = 8


def main() -> int:
    dst_dir = config.DB_PATH.parent / 'backups'
    dst_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime('%Y%m%d')
    dst = dst_dir / f'cavallin-{stamp}.db'
    src = sqlite3.connect(str(config.DB_PATH))
    try:
        dst_conn = sqlite3.connect(str(dst))
        try:
            src.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src.close()
    print(f'Wrote {dst}')

    # Prune. Filenames sort the same as their dates, so newest is last. Keep
    # only the K most recent so the directory doesn't grow without bound.
    snapshots = sorted(dst_dir.glob('cavallin-*.db'))
    pruned = 0
    for old in snapshots[:-KEEP_LAST]:
        old.unlink()
        pruned += 1
    if pruned:
        print(f'Pruned {pruned} old snapshot(s); keeping {KEEP_LAST} most recent.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
