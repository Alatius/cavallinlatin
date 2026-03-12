import bisect
import os
import re

TIFF_HEIGHT = 5120


def compute_orth_sources(html, alignment):
    """Compute source attribution for each <orth> tag by ordinal index.

    Must be called on the same HTML that the alignment was built from,
    so that absolute positions in html_plain_map match."""
    html_plain_map = alignment.html_plain_map
    html_to_rtml = alignment.html_to_rtml
    source_map = alignment.source_map
    rtml_text = alignment.rtml_text

    orth_attrs = {}
    last_attribution = None

    # Build html_plain for character matching
    from text_alignment import clean_html_text
    html_plain, _ = clean_html_text(html)

    for orth_idx, m in enumerate(re.finditer(r'<orth>(.*?)</orth>', html)):
        orth_html_pos = m.start(1)
        orth_html_end = m.end(1)
        h_plain_pos = bisect.bisect_left(html_plain_map, orth_html_pos)
        h_plain_end = bisect.bisect_left(html_plain_map, orth_html_end)

        if h_plain_pos >= len(html_to_rtml):
            if last_attribution is not None:
                orth_attrs[orth_idx] = last_attribution
            continue

        # Find the first character in the orth where the html and rtml
        # actually agree. This skips expanded prefixes like "Ĭnĭmī" in
        # "Ĭnĭmīcĭter" when the rtml has "-cĭter", landing on "c" instead.
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

        found_attribution = None
        if rtml_pos >= 0 and rtml_pos < len(source_map):
            tiff, top = source_map[rtml_pos]
            if tiff is not None:
                found_attribution = (tiff, round(top / TIFF_HEIGHT * 100, 1))

        if found_attribution is not None:
            last_attribution = found_attribution

        if last_attribution is not None:
            orth_attrs[orth_idx] = last_attribution

    return orth_attrs


def apply_orth_attrs(html, orth_attrs):
    """Replace <orth> tags with attributed versions (by ordinal index)."""
    total = 0
    attributed = 0

    def replace_orth(m):
        nonlocal total, attributed
        idx = total
        total += 1
        if idx in orth_attrs:
            attributed += 1
            tiff, y = orth_attrs[idx]
            base_name = os.path.basename(tiff).replace('.tiff', '.png')
            return f'<orth data-img="{base_name}" data-y="{y}">'
        return '<orth>'

    result = re.sub(r'<orth>', replace_orth, html)
    if total > 0:
        if attributed < total:
            print(f"  Warning: {total - attributed} orths could not be attributed")
    return result
