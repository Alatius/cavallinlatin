import bisect
import os
import re

TIFF_HEIGHT = 5120


def compute_orth_sources(html, alignment):
    """Compute source attribution for each <orth> tag by ordinal index.

    Must be called on the same HTML that the alignment was built from,
    so that absolute positions in html_norm_to_html match."""
    blocks = alignment.matching_blocks
    html_norm_to_html = alignment.html_norm_to_html
    rtml_norm_map = alignment.rtml_norm_map
    source_map = alignment.source_map

    block_h_starts = [b[0] for b in blocks]

    orth_attrs = {}
    last_attribution = None

    for orth_idx, m in enumerate(re.finditer(r'<orth>(.*?)</orth>', html)):
        orth_html_pos = m.start(1)
        h_norm_pos = bisect.bisect_left(html_norm_to_html, orth_html_pos)

        idx = bisect.bisect_right(block_h_starts, h_norm_pos) - 1

        rtml_norm_pos = None
        if idx >= 0:
            a, b, size = blocks[idx]
            if a <= h_norm_pos < a + size:
                rtml_norm_pos = b + (h_norm_pos - a)
            else:
                rtml_norm_pos = b + size

        found_attribution = None
        if rtml_norm_pos is not None and rtml_norm_pos < len(rtml_norm_map):
            rtml_pos = rtml_norm_map[rtml_norm_pos]
            if rtml_pos < len(source_map):
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
