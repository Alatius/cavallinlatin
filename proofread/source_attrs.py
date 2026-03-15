import bisect
import os
import re

TIFF_HEIGHT = 5120


def compute_element_sources(html, alignment, rtml):
    """Compute source attribution for <orth> and <li> tags.

    Returns (orth_attrs, li_attrs) dicts: {ordinal_index: (tiff_filename, y_pct)}
    Must be called on the same HTML that the alignment was built from.
    """
    html_plain_map = alignment.html_plain_map
    html_to_rtml = alignment.html_to_rtml
    html_plain = alignment.html_plain
    source_map = rtml.source_map
    rtml_text = rtml.text

    def _find_source(html_pos_start, html_pos_end):
        """Find source attribution for a range in the original HTML."""
        h_plain_pos = bisect.bisect_left(html_plain_map, html_pos_start)
        h_plain_end = bisect.bisect_left(html_plain_map, html_pos_end)

        if h_plain_pos >= len(html_to_rtml):
            return None

        # Find the first character where html and rtml actually agree
        rtml_pos = -1
        for hp in range(h_plain_pos, min(h_plain_end, len(html_to_rtml))):
            rp = html_to_rtml[hp]
            if rp >= 0 and rp < len(rtml_text) and html_plain[hp] == rtml_text[rp]:
                rtml_pos = rp
                break
        if rtml_pos == -1:
            # Fallback: use first valid mapping
            for hp in range(h_plain_pos, min(h_plain_end, len(html_to_rtml))):
                if html_to_rtml[hp] >= 0:
                    rtml_pos = html_to_rtml[hp]
                    break

        if rtml_pos >= 0 and rtml_pos < len(source_map):
            tiff, top = source_map[rtml_pos]
            if tiff is not None:
                return (tiff, round(top / TIFF_HEIGHT * 100, 1))
        return None

    # Compute orth sources
    orth_attrs = {}
    last_attribution = None
    for orth_idx, m in enumerate(re.finditer(r'<orth>(.*?)</orth>', html)):
        found = _find_source(m.start(1), m.end(1))
        if found is not None:
            last_attribution = found
        if last_attribution is not None:
            orth_attrs[orth_idx] = last_attribution

    # Compute li sources
    li_attrs = {}
    for li_idx, m in enumerate(re.finditer(r'<li>', html)):
        content_start = m.end()
        # Use a short range after <li> for the sense marker
        content_end = min(content_start + 10, len(html))
        found = _find_source(content_start, content_end)
        if found is not None:
            li_attrs[li_idx] = found

    return orth_attrs, li_attrs


def apply_source_attrs(html, orth_attrs, li_attrs):
    """Replace <orth> and <li> tags with attributed versions (by ordinal index)."""
    total_orth = 0
    attributed_orth = 0

    def replace_orth(m):
        nonlocal total_orth, attributed_orth
        idx = total_orth
        total_orth += 1
        if idx in orth_attrs:
            attributed_orth += 1
            tiff, y = orth_attrs[idx]
            base_name = os.path.basename(tiff).replace('.tiff', '.png')
            return f'<orth data-img="{base_name}" data-y="{y}">'
        return '<orth>'

    html = re.sub(r'<orth>', replace_orth, html)

    if total_orth > 0 and attributed_orth < total_orth:
        print(f"  Warning: {total_orth - attributed_orth} orths could not be attributed")

    total_li = 0
    attributed_li = 0

    def replace_li(m):
        nonlocal total_li, attributed_li
        idx = total_li
        total_li += 1
        if idx in li_attrs:
            attributed_li += 1
            tiff, y = li_attrs[idx]
            base_name = os.path.basename(tiff).replace('.tiff', '.png')
            return f'<li data-img="{base_name}" data-y="{y}">'
        return '<li>'

    html = re.sub(r'<li>', replace_li, html)

    if total_li > 0 and attributed_li < total_li:
        print(f"  Warning: {total_li - attributed_li} list items could not be attributed")

    return html


def insert_original_linebreaks(html, alignment, rtml):
    """Replace spaces in HTML with \\n where the original print had line breaks."""
    html_plain = alignment.html_plain
    html_to_rtml = alignment.html_to_rtml
    html_plain_map = alignment.html_plain_map
    line_breaks = rtml.line_breaks

    positions_to_replace = []
    for i in range(len(html_plain)):
        if html_plain[i] != ' ':
            continue
        rtml_pos = html_to_rtml[i]
        if rtml_pos < 0:
            continue
        if rtml_pos not in line_breaks:
            continue
        abs_pos = html_plain_map[i]
        if abs_pos < len(html) and html[abs_pos] == ' ':
            positions_to_replace.append(abs_pos)

    # Apply from end to preserve positions
    html_chars = list(html)
    for pos in sorted(positions_to_replace, reverse=True):
        html_chars[pos] = '\n'
    html = ''.join(html_chars)

    # Shift \n to be adjacent to tag boundaries:
    # Move \n past immediately following closing tags
    html = re.sub(r'\n((?:</[^>]+>)+)', lambda m: m.group(1) + '\n', html)
    # Remove spaces between \n and next content
    html = re.sub(r'\n +', '\n', html)
    # Remove spaces before \n
    html = re.sub(r' +\n', '\n', html)

    return html
