import bisect
import re


def _compute_dash_break_positions(html, alignment):
    """Compute absolute HTML positions of <br/> tags that correspond to
    em-dashes in the rtml source, using pre-computed alignment."""
    dash_break_positions = set()

    for (h_to_r, r_dashes, h_norm, h_n2c, h_c2h, h_start, h_end, r_n2c) in alignment.para_alignments:
        if not r_dashes:
            continue

        para_html = html[h_start:h_end]
        for bm in re.finditer(r' *<br/>\n', para_html):
            break_end_abs = h_start + bm.end()

            ci = bisect.bisect_left(h_c2h, break_end_abs)
            if ci >= len(h_c2h):
                continue

            ni = bisect.bisect_left(h_n2c, ci)
            if ni >= len(h_norm):
                continue

            ri_pos = h_to_r.get(ni)
            if ri_pos is None:
                for delta in range(1, 4):
                    if (ni + delta) in h_to_r:
                        ri_pos = h_to_r[ni + delta]
                        break
                    if (ni - delta) in h_to_r:
                        ri_pos = h_to_r[ni - delta]
                        break
            if ri_pos is None:
                continue

            if ri_pos >= len(r_n2c):
                continue
            r_ci = r_n2c[ri_pos]

            if any((r_ci + offset) in r_dashes for offset in range(-2, 3)):
                dash_break_positions.add(h_start + bm.start())

    return dash_break_positions


def remove_spurious_breaks(html, alignment):
    """Remove <br/> tags that don't correspond to em-dashes in the rtml source."""
    dash_break_positions = _compute_dash_break_positions(html, alignment)

    SENSE_RE = re.compile(r'^(?:[0-9]+\.|[IVX]+\.|([a-z])\1?\.|[A-Z]\.|[α-ω]\.)')

    def replace_break(m):
        after = html[m.end():m.end() + 30]
        if SENSE_RE.match(after):
            return m.group(0)
        if after.startswith('<orth>'):
            return m.group(0)
        if m.start() in dash_break_positions:
            return ' —' +m.group(0)
        return ' '

    html = re.sub(r' *<br/>\n', replace_break, html)

    return html
