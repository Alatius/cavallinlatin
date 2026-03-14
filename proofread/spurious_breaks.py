import bisect
import re


def _compute_dash_break_positions(html, alignment):
    """Compute absolute HTML positions of <br/> tags that correspond to
    em-dashes in the rtml source, using pre-computed global alignment."""
    dash_break_positions = set()

    html_plain_map = alignment.html_plain_map
    html_to_rtml = alignment.html_to_rtml
    rtml_dashes = alignment.rtml_dashes

    for bm in re.finditer(r' *<br/>\n', html):
        break_end_abs = bm.end()

        # Find the html_plain position corresponding to just after the break
        h_plain_pos = bisect.bisect_left(html_plain_map, break_end_abs)
        if h_plain_pos >= len(html_to_rtml):
            continue

        # Look up corresponding rtml position
        rtml_pos = html_to_rtml[h_plain_pos]

        if rtml_pos < 0:
            continue

        # Check if nearby rtml position is a dash
        if (rtml_pos - 2) in rtml_dashes:
            dash_break_positions.add(bm.start())

    return dash_break_positions


def remove_spurious_breaks(html, alignment):
    """Remove <br/> tags that don't correspond to em-dashes in the rtml source."""
    dash_break_positions = _compute_dash_break_positions(html, alignment)

    SENSE_RE = re.compile(r'^(?:[0-9]+\.|[IVX]+\.|([a-z])\1?\.|[A-Z]\.|[α-ω]\.)')

    def replace_break(m):
        after = html[m.end():m.end() + 30]
        if SENSE_RE.match(after):
            return '<br/>\n'
        if after.startswith('<orth>'):
            return '<br/>\n'
        if m.start() in dash_break_positions:
            return ' —<br/>\n'
        return ' '

    html = re.sub(r' *<br/>\n', replace_break, html)

    return html
