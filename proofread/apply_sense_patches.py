"""Apply sense-number fixes to intermediate HTML.

Override files in sense_overrides/ contain corrected intermediate HTML for
individual entries. Each file replaces the !!!-flagged paragraph for that
entry's headword. Files with a <!-- TODO --> marker are not yet edited and
are skipped.
"""

import os
import re
from xml.etree.ElementTree import fromstring


OVERRIDES_DIR = os.path.join(os.path.dirname(__file__), 'sense_overrides')


def _find_paragraph(html, headword):
    """Find a !!!-flagged paragraph by headword. Returns (start, end) or None."""
    search_start = 0
    while True:
        p_start = html.find('<p>!!!', search_start)
        if p_start < 0:
            return None
        p_end = html.find('</p>', p_start + 6)
        if p_end < 0:
            return None
        p_end += 4

        content = html[p_start + 6:p_end - 4]
        orth_m = re.search(r'<orth[^>]*>(.*?)</orth>', content)
        if orth_m:
            orth_text = re.sub(r'<[^>]*>', '', orth_m.group(1))
            if orth_text == headword:
                return (p_start, p_end)

        search_start = p_end


def _headword_from_content(content):
    """Extract headword text from paragraph content."""
    orth_m = re.search(r'<orth[^>]*>(.*?)</orth>', content)
    if orth_m:
        return re.sub(r'<[^>]*>', '', orth_m.group(1))
    return None


def apply_all_fixes(html):
    """Replace !!!-flagged paragraphs with corrected versions from override files."""
    if not os.path.isdir(OVERRIDES_DIR):
        return html

    applied = 0
    failed = []

    for fname in sorted(os.listdir(OVERRIDES_DIR)):
        if not fname.endswith('.html'):
            continue

        fpath = os.path.join(OVERRIDES_DIR, fname)
        with open(fpath, encoding='utf-8') as f:
            new_content = f.read().strip()

        # Skip unedited files (still have the TODO marker)
        if new_content.startswith('<!-- TODO'):
            continue

        # Extract headword from the override file
        headword = _headword_from_content(new_content)
        if not headword:
            failed.append(fname)
            continue

        span = _find_paragraph(html, headword)
        if span is None:
            failed.append(fname)
            continue

        p_start, p_end = span
        new_para = '<p>' + new_content + '</p>'

        # Validate XML compliance
        xml_test = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', new_para)
        try:
            fromstring(f'<root>{xml_test}</root>')
        except Exception as e:
            print(f"  WARNING: invalid XML in {fname}: {e}")

        html = html[:p_start] + new_para + html[p_end:]
        applied += 1

    if applied:
        print(f"  Applied {applied} sense overrides")
    if failed:
        print(f"  FAILED overrides: {failed}")

    return html


def export_flagged_entries(html, output_dir=None):
    """Export all !!!-flagged paragraphs to individual files for editing."""
    if output_dir is None:
        output_dir = OVERRIDES_DIR
    os.makedirs(output_dir, exist_ok=True)

    count = 0
    for m in re.finditer(r'<p>!!!(.*?)</p>', html, re.DOTALL):
        content = m.group(1)
        headword = _headword_from_content(content)
        if not headword:
            continue

        safe_name = re.sub(r'[^\w-]', '', headword.replace(',', ''))
        fpath = os.path.join(output_dir, f'{safe_name}.html')

        # Don't overwrite existing files (might be manually edited)
        if not os.path.exists(fpath):
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write('<!-- TODO: fix sense numbering -->\n')
                f.write(content)
            count += 1

    if count:
        print(f"  Exported {count} new flagged entries to {output_dir}")
