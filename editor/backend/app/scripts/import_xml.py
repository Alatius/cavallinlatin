"""Import editor/data/cavallinlatin.xml into SQLite.

Rebuilds the entries table from the XML file. Identity and editorial state
round-trip through the attributes export_xml writes: `urlid` pins an
entry's url_id (without it, id-less entries get positional ref-NNNNN ids
minted at import time, which renumber on any insertion or deletion), and
`status` restores the editorial status. Both are stripped before the body
is stored, so they exist only in the exported file.

What survives a reimport: entry bodies, url_ids, statuses, sort order, and
both comments and revision history (re-attached by url_id afterwards; a
row whose entry is gone from the file is dropped and counted in the
summary). What does not: locks, and any edit made after the file was
exported.

Refuses to run against a non-empty database without --force, so production
edits aren't clobbered by an accidental rerun.

Run from editor/backend/ with `python -m app.scripts.import_xml`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import get_args

from lxml import etree

# Allow `python app/scripts/import_xml.py` in addition to `-m`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import config, db, security  # noqa: E402
from app.models import Status  # noqa: E402
from app.text import (  # noqa: E402
    canonical_entry_xml, column_markers, derive_entry_fields,
)
from app.xml_parsing import SAFE_XML_PARSER  # noqa: E402

VALID_STATUSES = frozenset(get_args(Status))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--force', action='store_true',
                   help='Reimport even if the entries table is already populated')
    args = p.parse_args(argv)

    if not config.XML_PATH.exists():
        print(f'XML not found: {config.XML_PATH}', file=sys.stderr)
        return 1

    if not args.force:
        with db.get_conn() as conn:
            existing = conn.execute(
                'SELECT COUNT(*) AS n FROM entries'
            ).fetchone()['n']
            revisions = conn.execute(
                'SELECT COUNT(*) AS n FROM entry_revisions'
            ).fetchone()['n']
            comments = conn.execute(
                'SELECT COUNT(*) AS n FROM entry_comments'
            ).fetchone()['n']
        if existing:
            print(
                f'Refusing to import: entries table already has {existing} rows '
                f'(plus {revisions} revisions and {comments} comments). '
                f'Pass --force to wipe and reimport — this discards every edit '
                f'made since the XML was exported; comments and revisions are '
                f're-attached by url_id where their entry still exists.',
                file=sys.stderr,
            )
            return 1

    tree = etree.parse(str(config.XML_PATH), SAFE_XML_PARSER)
    root = tree.getroot()
    if root.tag != 'dictionary':
        print(f'Expected <dictionary> root, got <{root.tag}>', file=sys.stderr)
        return 1

    def importable(entry: 'etree._Element') -> bool:
        # Skip orphan entries with no <orth> (typically stray cross-refs
        # that slipped through make_lexicon.py's fixup pass).
        return entry.find('.//orth') is not None

    # Validation pass, before anything touches the database: every explicit
    # url_id (a `urlid` attribute, else the entry's own id) must be unique,
    # and every status must be one the schema accepts. Minted ref-NNNNN ids
    # must avoid the explicit ones, so collect them all first.
    explicit_ids: set[str] = set()
    problems: list[str] = []
    for pos, entry in enumerate(e for e in root.iter('entry') if importable(e)):
        url_id = entry.get('urlid') or entry.get('id')
        if url_id:
            if url_id in explicit_ids:
                problems.append(f'duplicate url_id {url_id!r}')
            explicit_ids.add(url_id)
        status = entry.get('status')
        if status is not None and status not in VALID_STATUSES:
            problems.append(
                f'invalid status {status!r} on entry #{pos + 1}'
                f' ({url_id or "no id"})'
            )
    if problems:
        for msg in problems[:20]:
            print(f'Refusing to import: {msg}', file=sys.stderr)
        if len(problems) > 20:
            print(f'... and {len(problems) - 20} more', file=sys.stderr)
        return 1

    now = security.now()
    with db.get_conn() as conn:
        conn.execute('BEGIN')
        try:
            # Snapshot comments and revisions before the wipe: DELETE FROM
            # entries cascades into both tables. They are re-keyed by url_id
            # (the numeric entry ids are about to be regenerated) and
            # re-attached after the entries are back. ORDER BY id preserves
            # the original insertion order, so rows sharing a created_at
            # second keep their relative order under the app's sorting.
            saved_comments = conn.execute(
                'SELECT e.url_id, c.user_id, c.body, c.created_at '
                'FROM entry_comments c JOIN entries e ON e.id = c.entry_id '
                'ORDER BY c.id'
            ).fetchall()
            saved_revisions = conn.execute(
                'SELECT e.url_id, r.xml_body, r.status, r.user_id, r.created_at '
                'FROM entry_revisions r JOIN entries e ON e.id = r.entry_id '
                'ORDER BY r.id'
            ).fetchall()

            conn.execute('DELETE FROM entry_revisions')
            conn.execute('DELETE FROM entries')
            conn.execute("INSERT INTO entries_fts(entries_fts) VALUES('rebuild')")

            current_column: str | None = None
            taken_ids = set(explicit_ids)
            ref_counter = 0
            sort_key = 0
            skipped_orphans = 0
            minted_refs = 0

            for entry in root.iter('entry'):
                if not importable(entry):
                    skipped_orphans += 1
                    continue

                sort_key += 100

                # urlid and status exist only in the exported file — strip
                # them before the body is serialized for storage.
                url_id = entry.attrib.pop('urlid', None) or entry.get('id')
                status = entry.attrib.pop('status', None) or 'untouched'
                if not url_id:
                    # Pre-urlid files: mint positional ids, skipping any the
                    # file claims explicitly elsewhere.
                    while True:
                        ref_counter += 1
                        url_id = f'ref-{ref_counter:05d}'
                        if url_id not in taken_ids:
                            break
                    taken_ids.add(url_id)
                    minted_refs += 1

                xml_body = canonical_entry_xml(entry)
                xml_id = entry.get('id')
                entry_type = entry.get('type') or 'plain'
                xml_root = entry.get('root')

                leading_cb, trailing_cb = column_markers(entry)
                starting_column = leading_cb or current_column
                if trailing_cb:
                    current_column = trailing_cb

                fields = derive_entry_fields(entry, headword_fallback=url_id)

                conn.execute(
                    'INSERT INTO entries (url_id, xml_id, xml_root, type, headword, '
                    'headword_sort, alt_headwords, starting_column, first_orth_y, '
                    'status, xml_body, plaintext, sort_key, created_at, updated_at) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (url_id, xml_id, xml_root, entry_type, fields.headword,
                     fields.headword_sort,
                     json.dumps(fields.alt_headwords, ensure_ascii=False),
                     starting_column, fields.first_orth_y,
                     status, xml_body, fields.plaintext, sort_key, now, now),
                )

            def reattach(rows, insert_sql: str, cols: tuple[str, ...]) -> tuple[int, int]:
                restored = dropped = 0
                for r in rows:
                    entry = conn.execute(
                        'SELECT id FROM entries WHERE url_id = ?', (r['url_id'],)
                    ).fetchone()
                    if entry is None:
                        dropped += 1
                        continue
                    conn.execute(insert_sql, (entry['id'], *(r[c] for c in cols)))
                    restored += 1
                return restored, dropped

            restored_comments, dropped_comments = reattach(
                saved_comments,
                'INSERT INTO entry_comments (entry_id, user_id, body, created_at) '
                'VALUES (?, ?, ?, ?)',
                ('user_id', 'body', 'created_at'),
            )
            restored_revisions, dropped_revisions = reattach(
                saved_revisions,
                'INSERT INTO entry_revisions (entry_id, xml_body, status, user_id, created_at) '
                'VALUES (?, ?, ?, ?, ?)',
                ('xml_body', 'status', 'user_id', 'created_at'),
            )

            conn.execute('COMMIT')
        except Exception:
            conn.execute('ROLLBACK')
            raise

        total = conn.execute('SELECT COUNT(*) AS n FROM entries').fetchone()['n']
        fts_total = conn.execute(
            'SELECT COUNT(*) AS n FROM entries_fts'
        ).fetchone()['n']
        refs = conn.execute(
            "SELECT COUNT(*) AS n FROM entries WHERE url_id LIKE 'ref-%'"
        ).fetchone()['n']
        without_col = conn.execute(
            'SELECT COUNT(*) AS n FROM entries WHERE starting_column IS NULL'
        ).fetchone()['n']
        print(f'Imported {total} entries (fts={fts_total}, refs={refs} '
              f'of which {minted_refs} newly minted, '
              f'without starting_column={without_col}, '
              f'skipped orphans={skipped_orphans}).')
        if restored_comments or dropped_comments:
            print(f'Comments: {restored_comments} restored, '
                  f'{dropped_comments} dropped (entry no longer in the file).')
        if restored_revisions or dropped_revisions:
            print(f'Revisions: {restored_revisions} restored, '
                  f'{dropped_revisions} dropped (entry no longer in the file).')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
