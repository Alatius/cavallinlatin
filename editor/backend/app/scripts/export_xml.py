"""Export SQLite entries back to cavallinlatin.xml.

Writes the concatenation of xml_body in sort_key order, wrapped in
<dictionary>. Used to regenerate editor/data/cavallinlatin.xml after
edits, for git history.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import config, db  # noqa: E402


def main() -> int:
    out = config.XML_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    with db.get_conn() as conn, out.open('w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<dictionary>\n')
        for row in conn.execute(
            'SELECT xml_body FROM entries ORDER BY sort_key'
        ):
            f.write(row['xml_body'])
            f.write('\n')
        f.write('</dictionary>\n')
    print(f'Wrote {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
