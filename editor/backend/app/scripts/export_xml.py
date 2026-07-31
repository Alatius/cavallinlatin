"""Export SQLite entries back to cavallinlatin.xml.

Writes every xml_body in sort_key order, wrapped in <dictionary>. Used to
regenerate editor/data/cavallinlatin.xml after edits, for git history.

The file is a faithful serialization of current editorial *state*, so that
import_xml can rebuild the database without inventing anything:

- `urlid` is written on any <entry> whose database url_id differs from its
  own id attribute — most importantly the ref-NNNNN entries, whose ids used
  to be re-minted positionally on import, renumbering thousands of URLs and
  <ref> targets after any insertion or deletion.
- `status` is written when it isn't the default 'untouched'.

Both attributes are stripped again by import_xml before the body is stored,
so neither editors nor the renderer ever see them. Editorial *history*
(entry_revisions, and durability in general) is deliberately not exported —
that is what backup_db is for.
"""

from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import config, db  # noqa: E402
from app.text import canonical_entry_xml  # noqa: E402
from app.xml_parsing import SAFE_XML_PARSER  # noqa: E402


def main() -> int:
    out = config.XML_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    with db.get_conn() as conn, out.open('w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<dictionary>\n')
        first = True
        for row in conn.execute(
            'SELECT url_id, status, xml_body FROM entries ORDER BY sort_key'
        ):
            # Blank line between entries, matching the file's historical
            # format so re-exports diff cleanly against git history.
            if not first:
                f.write('\n')
            first = False
            el = etree.fromstring(row['xml_body'].encode('utf-8'), SAFE_XML_PARSER)
            if row['url_id'] != el.get('id'):
                el.set('urlid', row['url_id'])
            if row['status'] != 'untouched':
                el.set('status', row['status'])
            f.write(canonical_entry_xml(el))
            f.write('\n')
        f.write('</dictionary>\n')
    print(f'Wrote {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
