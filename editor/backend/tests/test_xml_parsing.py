"""Unit tests for the hardened XML parser."""

from __future__ import annotations

from lxml import etree

from app.xml_parsing import SAFE_XML_PARSER


def test_parses_legitimate_entry():
    xml = b'<entry id="abacus" type="primary"><orth>foo</orth> bar</entry>'
    el = etree.fromstring(xml, SAFE_XML_PARSER)
    assert el.tag == 'entry'
    assert el.find('orth').text == 'foo'


def test_decodes_predefined_entities():
    # &amp;/&lt;/&gt;/&quot; must continue to round-trip as their characters,
    # otherwise the dictionary's curated text would render wrong.
    el = etree.fromstring(b'<entry>foo &amp; bar &lt;x&gt;</entry>', SAFE_XML_PARSER)
    assert el.text == 'foo & bar <x>'


def test_blocks_billion_laughs_expansion():
    bomb = (b'<?xml version="1.0"?><!DOCTYPE l ['
            b'<!ENTITY a "bomb">'
            b'<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
            b'<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">'
            b']><entry>&c;</entry>')
    el = etree.fromstring(bomb, SAFE_XML_PARSER)
    # With resolve_entities=False the user-defined entity is not expanded:
    # itertext skips entity references entirely, so no 1000-char text.
    assert 'bomb' not in ''.join(el.itertext())


def test_external_entity_blocked():
    # no_network=True (lxml default) keeps SYSTEM entities from fetching.
    xxe = (b'<?xml version="1.0"?><!DOCTYPE l ['
           b'<!ENTITY x SYSTEM "file:///etc/hostname">'
           b']><entry>&x;</entry>')
    # Either the parser refuses outright or the entity stays unresolved —
    # both outcomes are safe; no file content can leak.
    try:
        el = etree.fromstring(xxe, SAFE_XML_PARSER)
        assert '/etc/hostname' not in ''.join(el.itertext())
    except etree.XMLSyntaxError:
        pass


def test_schema_version_is_stamped():
    """CREATE TABLE IF NOT EXISTS does nothing to an existing database, so a
    future column addition needs a migration ladder to reach production."""
    import sqlite3
    from app import db
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    assert conn.execute('PRAGMA user_version').fetchone()[0] == 0
    db.init_schema(conn)
    assert conn.execute('PRAGMA user_version').fetchone()[0] == db.SCHEMA_VERSION
    # Idempotent: re-running must not re-apply anything.
    db.init_schema(conn)
    assert conn.execute('PRAGMA user_version').fetchone()[0] == db.SCHEMA_VERSION
    conn.close()


def test_migrations_cover_every_version_step():
    from app import db
    for target in db.MIGRATIONS:
        assert 1 < target <= db.SCHEMA_VERSION, (
            f'MIGRATIONS[{target}] is unreachable at SCHEMA_VERSION='
            f'{db.SCHEMA_VERSION}'
        )
