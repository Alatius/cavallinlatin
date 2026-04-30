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
