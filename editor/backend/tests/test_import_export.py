"""Round-trip tests for import_xml / export_xml.

The exported XML is the only durable copy of the dictionary in version
control, so export → import must be a faithful inverse of the database
state: bodies byte-identical, url_ids stable (especially the minted
ref-NNNNN ones, which used to renumber positionally on every reimport),
statuses preserved, comments re-attached by url_id.

These tests run against their own database and XML file (monkeypatched
config paths), not the session-shared fixture DB.
"""

from __future__ import annotations

import pytest

from app import config, db, security
from app.scripts import export_xml, import_xml

# Two id-carrying entries and two id-less ones (which get minted ref-NNNNN
# url_ids), plus an orphan without <orth> that import skips.
SOURCE_XML = '''<?xml version="1.0" encoding="utf-8"?>
<dictionary>
<entry id="abacus" type="primary"><cb n="0001a"/><orth y="10.5">abacus</orth> a table</entry>
<entry><orth y="20.0">abaculus</orth> se <ref target="abacus">abacus</ref></entry>
<entry id="abbas" type="primary"><orth y="30.0">abbas</orth> an abbot</entry>
<entry><orth y="40.0">abbatia</orth> abbey</entry>
<entry><ref target="abacus">orphan without orth</ref></entry>
</dictionary>
'''


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Fresh DB + XML file, with SOURCE_XML already imported."""
    monkeypatch.setattr(config, 'DB_PATH', tmp_path / 'roundtrip.db')
    monkeypatch.setattr(config, 'XML_PATH', tmp_path / 'dictionary.xml')
    config.XML_PATH.write_text(SOURCE_XML, encoding='utf-8')
    assert import_xml.main([]) == 0
    return tmp_path


def entry_state(conn) -> list[tuple]:
    return [
        (r['url_id'], r['status'], r['xml_body'])
        for r in conn.execute(
            'SELECT url_id, status, xml_body FROM entries ORDER BY sort_key'
        )
    ]


def add_comment(conn, url_id: str, body: str) -> None:
    now = security.now()
    conn.execute(
        'INSERT OR IGNORE INTO users (email, display_name, password_hash, created_at) '
        "VALUES ('commenter@example.com', 'Commenter', 'x', ?)",
        (now,),
    )
    user_id = conn.execute(
        "SELECT id FROM users WHERE email = 'commenter@example.com'"
    ).fetchone()['id']
    entry_id = conn.execute(
        'SELECT id FROM entries WHERE url_id = ?', (url_id,)
    ).fetchone()['id']
    conn.execute(
        'INSERT INTO entry_comments (entry_id, user_id, body, created_at) '
        'VALUES (?, ?, ?, ?)',
        (entry_id, user_id, body, now),
    )


def comment_bodies(conn, url_id: str) -> list[str]:
    return [
        r['body'] for r in conn.execute(
            'SELECT c.body FROM entry_comments c '
            'JOIN entries e ON e.id = c.entry_id WHERE e.url_id = ?',
            (url_id,),
        )
    ]


def test_initial_import_mints_positional_ref_ids(workdir):
    with db.get_conn() as conn:
        state = entry_state(conn)
    assert [s[0] for s in state] == ['abacus', 'ref-00001', 'abbas', 'ref-00002']
    assert all(s[1] == 'untouched' for s in state)


def test_roundtrip_preserves_ids_status_bodies_comments_and_revisions(workdir):
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE entries SET status = 'in_progress' WHERE url_id = 'ref-00001'"
        )
        add_comment(conn, 'ref-00002', 'check this against the scan')
        conn.execute(
            'INSERT INTO entry_revisions (entry_id, xml_body, status, created_at) '
            "SELECT id, '<entry id=\"abacus\"><orth>old</orth></entry>', status, 7 "
            "FROM entries WHERE url_id = 'abacus'"
        )
        before = entry_state(conn)

    assert export_xml.main() == 0
    exported = config.XML_PATH.read_text(encoding='utf-8')
    assert 'urlid="ref-00001"' in exported
    assert 'status="in_progress"' in exported
    # The decoration attributes belong to the file, not to stored bodies.
    assert import_xml.main(['--force']) == 0

    with db.get_conn() as conn:
        after = entry_state(conn)
        assert after == before
        assert 'urlid' not in after[1][2] and 'status' not in after[1][2]
        assert comment_bodies(conn, 'ref-00002') == ['check this against the scan']
        rev = conn.execute(
            'SELECT e.url_id, r.xml_body, r.created_at FROM entry_revisions r '
            'JOIN entries e ON e.id = r.entry_id'
        ).fetchall()
        assert [(r['url_id'], r['xml_body'], r['created_at']) for r in rev] == [
            ('abacus', '<entry id="abacus"><orth>old</orth></entry>', 7),
        ]


def test_comments_and_revisions_of_removed_entries_are_dropped(workdir, capsys):
    with db.get_conn() as conn:
        add_comment(conn, 'ref-00001', 'orphaned soon')
        conn.execute(
            'INSERT INTO entry_revisions (entry_id, xml_body, status, created_at) '
            "SELECT id, xml_body, status, 0 FROM entries WHERE url_id = 'ref-00001'"
        )
    assert export_xml.main() == 0
    # Simulate the entry disappearing between export and import.
    xml = config.XML_PATH.read_text(encoding='utf-8')
    xml = '\n'.join(line for line in xml.splitlines()
                    if 'urlid="ref-00001"' not in line)
    config.XML_PATH.write_text(xml, encoding='utf-8')

    assert import_xml.main(['--force']) == 0
    out = capsys.readouterr().out
    assert 'Comments: 0 restored, 1 dropped' in out
    assert 'Revisions: 0 restored, 1 dropped' in out
    with db.get_conn() as conn:
        assert conn.execute('SELECT COUNT(*) AS n FROM entry_comments').fetchone()['n'] == 0
        assert conn.execute('SELECT COUNT(*) AS n FROM entry_revisions').fetchone()['n'] == 0


def test_deleting_a_ref_entry_does_not_renumber_the_rest(workdir):
    """The original #29 failure: any deletion shifted every later ref id."""
    with db.get_conn() as conn:
        add_comment(conn, 'ref-00002', 'still attached after the join')
        conn.execute("DELETE FROM entries WHERE url_id = 'ref-00001'")

    assert export_xml.main() == 0
    assert import_xml.main(['--force']) == 0

    with db.get_conn() as conn:
        ids = [s[0] for s in entry_state(conn)]
        assert ids == ['abacus', 'abbas', 'ref-00002']
        assert comment_bodies(conn, 'ref-00002') == ['still attached after the join']


def test_guard_refuses_nonempty_db_and_reports_what_is_at_stake(workdir, capsys):
    with db.get_conn() as conn:
        add_comment(conn, 'abacus', 'a comment')
        before = entry_state(conn)
    assert import_xml.main([]) == 1
    err = capsys.readouterr().err
    assert 'Refusing to import' in err and '1 comments' in err
    with db.get_conn() as conn:
        assert entry_state(conn) == before


def test_duplicate_url_ids_are_rejected_before_the_wipe(workdir, capsys):
    with db.get_conn() as conn:
        before = entry_state(conn)
    config.XML_PATH.write_text(
        '<dictionary>'
        '<entry id="abacus"><orth>a</orth></entry>'
        '<entry urlid="abacus"><orth>b</orth></entry>'
        '</dictionary>',
        encoding='utf-8',
    )
    assert import_xml.main(['--force']) == 1
    assert "duplicate url_id 'abacus'" in capsys.readouterr().err
    with db.get_conn() as conn:
        assert entry_state(conn) == before


def test_invalid_status_is_rejected_before_the_wipe(workdir, capsys):
    config.XML_PATH.write_text(
        '<dictionary><entry id="a" status="finished"><orth>a</orth></entry></dictionary>',
        encoding='utf-8',
    )
    assert import_xml.main(['--force']) == 1
    assert "invalid status 'finished'" in capsys.readouterr().err


def test_minting_skips_url_ids_the_file_claims_explicitly(workdir):
    config.XML_PATH.write_text(
        '<dictionary>'
        '<entry urlid="ref-00001"><orth>pinned</orth></entry>'
        '<entry><orth>minted</orth></entry>'
        '</dictionary>',
        encoding='utf-8',
    )
    assert import_xml.main(['--force']) == 0
    with db.get_conn() as conn:
        ids = [s[0] for s in entry_state(conn)]
    assert ids == ['ref-00001', 'ref-00002']
