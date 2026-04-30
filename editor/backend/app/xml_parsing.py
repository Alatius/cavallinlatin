"""Hardened XML parser shared by everything that consumes user XML.

Disables internal entity resolution (which prevents billion-laughs entity
expansion) and DTD loading. lxml already disables network entity loading
by default, so external-entity attacks (XXE file disclosure) are not
exploitable — the remaining concern was DoS via in-document expansion.

Predefined XML entities (&amp;, &lt;, &gt;, &quot;, &apos;) are still
decoded normally; only user-defined entity references are left as text.
"""

from __future__ import annotations

from lxml import etree


SAFE_XML_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
)
