"""Import editor/data/cavallinlatin.xml into SQLite.

Wipes entries + entry_revisions and reimports. Refuses to run against a
non-empty database without --force, so production edits aren't clobbered
by an accidental rerun.

Run from editor/backend/ with `python -m app.scripts.import_xml`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from lxml import etree

# Allow `python app/scripts/import_xml.py` in addition to `-m`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import config, db, security  # noqa: E402
from app.text import column_markers, first_orth_y, fold, orth_texts  # noqa: E402
from app.xml_parsing import SAFE_XML_PARSER  # noqa: E402


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
        if existing:
            print(
                f'Refusing to import: entries table already has {existing} rows. '
                f'Pass --force to wipe and reimport (this discards all editor work).',
                file=sys.stderr,
            )
            return 1

    tree = etree.parse(str(config.XML_PATH), SAFE_XML_PARSER)
    root = tree.getroot()
    if root.tag != 'dictionary':
        print(f'Expected <dictionary> root, got <{root.tag}>', file=sys.stderr)
        return 1

    now = security.now()
    with db.get_conn() as conn:
        conn.execute('BEGIN')
        try:
            conn.execute('DELETE FROM entry_revisions')
            conn.execute('DELETE FROM entries')
            conn.execute("INSERT INTO entries_fts(entries_fts) VALUES('rebuild')")

            current_column: str | None = None
            ref_counter = 0
            sort_key = 0
            skipped_orphans = 0

            for entry in root.iter('entry'):
                # Skip orphan entries with no <orth> (typically stray cross-refs
                # that slipped through make_lexicon.py's fixup pass).
                if entry.find('.//orth') is None:
                    skipped_orphans += 1
                    continue

                sort_key += 100

                # with_tail=False drops whitespace after </entry> (which
                # would otherwise be the separator to the next sibling entry
                # in the source file).
                xml_body = etree.tostring(entry, encoding='unicode', with_tail=False)
                # Also strip any whitespace directly before </entry> so the
                # editor doesn't open with a trailing blank line.
                xml_body = re.sub(r'\s+</entry>', '</entry>', xml_body)
                xml_id = entry.get('id')
                entry_type = entry.get('type') or 'plain'
                xml_root = entry.get('root')

                leading_cb, trailing_cb = column_markers(entry)
                starting_column = leading_cb or current_column
                if trailing_cb:
                    current_column = trailing_cb

                if xml_id:
                    url_id = xml_id
                else:
                    ref_counter += 1
                    url_id = f'ref-{ref_counter:05d}'

                orths = orth_texts(entry)
                headword = orths[0] if orths else url_id
                alt_headwords_json = json.dumps(orths[1:], ensure_ascii=False)
                headword_sort = fold(headword)
                first_y = first_orth_y(entry)
                plaintext = ' '.join(''.join(entry.itertext()).split())

                conn.execute(
                    'INSERT INTO entries (url_id, xml_id, xml_root, type, headword, '
                    'headword_sort, alt_headwords, starting_column, first_orth_y, '
                    'status, xml_body, plaintext, sort_key, created_at, updated_at) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (url_id, xml_id, xml_root, entry_type, headword,
                     headword_sort, alt_headwords_json, starting_column, first_y,
                     'untouched', xml_body, plaintext, sort_key, now, now),
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
        print(f'Imported {total} entries (fts={fts_total}, refs={refs}, '
              f'without starting_column={without_col}, '
              f'skipped orphans={skipped_orphans}).')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
