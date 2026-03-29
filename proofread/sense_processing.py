import re


def get_marker_type_and_value(marker):
    """Return (type, numeric_value) for a sense marker."""
    clean = marker.rstrip('.,;')

    if clean.isdigit():
        return ('digit', int(clean))
    elif len(clean) == 1 and ord(clean) >= 0x03B1 and ord(clean) <= 0x03C9:
        return ('greek', ord(clean) - 0x03B1)
    elif len(clean) == 1 and clean.isalpha() and clean.islower():
        if clean <= 'i':
            letter_val = ord(clean) - ord('a')
        else:
            letter_val = ord(clean) - ord('a') - 1
        return ('letter', letter_val)
    elif len(clean) == 2 and clean[0] == clean[1] and clean[0].isalpha() and clean[0].islower():
        if clean[0] <= 'i':
            base_val = ord(clean[0]) - ord('a')
        else:
            base_val = ord(clean[0]) - ord('a') - 1
        return ('double_letter', base_val)
    elif all(c in 'IVXivx' for c in clean):
        if clean.isupper():
            roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12}
            return ('roman_upper', roman_map.get(clean, 0))
        else:
            roman_map = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12}
            return ('roman_lower', roman_map.get(clean, 0))
    elif len(clean) == 1 and clean.isalpha() and clean.isupper():
        letter_val = ord(clean) - ord('A')
        return ('letter_upper', letter_val)
    else:
        return ('unknown', 0)


_CSS_CLASS = {
    'letter_upper': 'sense-Alpha',
    'roman_upper': 'sense-Roman',
    'digit': 'sense-decimal',
    'letter': 'sense-alpha',
    'greek': 'sense-greek',
    'roman_lower': 'sense-roman',
    'double_letter': 'sense-double-alpha',
}


def _dynamic_stack_analyze(marker_types_vals):
    """Analyze markers using dynamic nesting based on order of appearance.

    Determines nesting dynamically rather than using a fixed level hierarchy:
    - A marker type already on the stack: pop back to it and continue
    - A new marker type with a starting value: push as a new nested level

    This correctly handles both the standard hierarchy (A > I > 1 > a) and
    entries like Prīmus where digits (1-6) are the outer level with
    letter_upper (A-C) nested inside.

    Args:
        marker_types_vals: list of (mtype, mval) tuples

    Returns:
        (is_valid, levels): is_valid is bool, levels is list of int levels
        (may be shorter than input if validation fails early)
    """
    stack = []  # list of [mtype, mval, level]
    levels = []

    for mtype, mval in marker_types_vals:
        if mtype == 'unknown':
            levels.append(None)
            continue

        # Look for this marker type on the stack (search from top)
        found_idx = None
        for i in range(len(stack) - 1, -1, -1):
            if stack[i][0] == mtype:
                found_idx = i
                break

        if found_idx is not None:
            # Existing type: pop everything above it
            del stack[found_idx + 1:]
            # Check that value is sequential
            if mval != stack[found_idx][1] + 1:
                return False, levels
            stack[found_idx][1] = mval
            levels.append(stack[found_idx][2])
        else:
            # New type: must start at its beginning value
            if mtype in ('letter', 'letter_upper', 'double_letter', 'greek'):
                if mval != 0:
                    return False, levels
            elif mtype in ('digit', 'roman_lower', 'roman_upper'):
                if mval != 1:
                    return False, levels
            # Assign next deeper level
            new_level = (stack[-1][2] + 1) if stack else 0
            stack.append([mtype, mval, new_level])
            levels.append(new_level)

    return True, levels


def _is_sequence_valid(markers):
    """Check if a marker sequence forms a valid nesting structure."""
    if not markers:
        return True
    mtv = [(mtype, mval) for _, mtype, mval, _ in markers]
    return _dynamic_stack_analyze(mtv)[0]


def split_paragraphs_at_orths(html):
    """Split paragraphs at line-initial <orth> tags into separate <p> elements.

    Each fodt paragraph may contain multiple dictionary entries separated by
    <br/>\n. This function decides which <orth> tags mark new entries vs.
    sub-headwords within the same entry, by checking that sense marker
    sequences (1., a., α., etc.) remain valid after splitting.

    Lines where splitting is not possible are joined with ' <br/>' instead.
    Paragraphs where no valid split combination exists are prefixed with !!!
    for manual review.
    """

    SENSE_RE = re.compile(
        r'^\s*([0-9]+|[a-z]{1,2}|[A-Z]|[IVXivx]+|[α-ω])([.,;])?(?=\s|<|$)'
    )
    ORTH_INITIAL_RE = re.compile(r'^<orth[^>]*>')
    ORTH_ANY_RE = re.compile(r'<orth[^>]*>')

    def try_partition_combination(markers, active_resets, marker_line_indices):
        """Try a specific combination of reset line indices and check if all partitions are valid."""
        if not active_resets:
            return _is_sequence_valid(markers)

        current_partition = []
        for i, (li, marker_info) in enumerate(zip(marker_line_indices, markers)):
            should_reset = False
            if i > 0:
                for reset_li in active_resets:
                    if marker_line_indices[i-1] < reset_li < li:
                        should_reset = True
                        break

            if should_reset and current_partition:
                if not _is_sequence_valid(current_partition):
                    return False
                current_partition = [marker_info]
            else:
                current_partition.append(marker_info)

        if current_partition and not _is_sequence_valid(current_partition):
            return False

        return True

    def reassemble(lines, line_tags):
        """Reassemble lines into paragraph(s) based on per-line tags."""
        parts = [lines[0]]
        for i in range(1, len(lines)):
            if line_tags[i] == 'split':
                parts.append('</p>\n\n<p>')
            elif line_tags[i] == 'join':
                parts.append(' <br/>')
            else:
                parts.append('<br/>\n')
            parts.append(lines[i])
        return '<p>' + ''.join(parts) + '</p>'

    def process_paragraph(match):
        full_para = match.group(0)
        para_content = match.group(1)

        # Each fodt <p> may contain multiple dictionary entries separated by
        # <br/>\n. Split into individual lines to analyse them.
        lines = para_content.split('<br/>\n')
        if len(lines) <= 1:
            return full_para

        # Collect sense markers (e.g. "1.", "a.", "IV.") from all lines after
        # the first (which is the headword line). marker_line_indices records
        # which line each marker came from, so we can later test whether
        # splitting at a given orth line would break a valid marker sequence.
        markers = []
        marker_line_indices = []
        for li in range(1, len(lines)):
            m = SENSE_RE.match(lines[li])
            if m:
                marker = m.group(1)
                punct = m.group(2)
                mtype, mval = get_marker_type_and_value(marker)
                markers.append((marker, mtype, mval, punct))
                marker_line_indices.append(li)

        # Find line-initial orth candidates: lines starting with <orth> that
        # could mark the beginning of a new dictionary entry.
        candidate_orth_lines = []
        for li in range(1, len(lines)):
            if ORTH_INITIAL_RE.match(lines[li]):
                candidate_orth_lines.append(li)

        # Find inline orth candidates: lines that contain <orth> somewhere in
        # the middle (not at start) and don't begin with a sense marker. These
        # are a secondary source of potential split points.
        inline_orth_lines = []
        for li in range(1, len(lines)):
            if ORTH_INITIAL_RE.match(lines[li]):
                continue
            if SENSE_RE.match(lines[li]):
                continue
            if ORTH_ANY_RE.search(lines[li]):
                inline_orth_lines.append(li)

        # Per-line tags: 'keep' = preserve original <br/>\n,
        # 'split' = start a new <p>, 'join' = merge with previous line via <br/>
        line_tags = ['keep'] * len(lines)

        if not candidate_orth_lines:
            # No line-initial orths to split at. If the sense marker sequence
            # is broken, try inline orths as emergency split points; otherwise
            # return the paragraph unchanged.
            if len(markers) >= 2 and not _is_sequence_valid(markers):
                for li in inline_orth_lines:
                    if try_partition_combination(markers, [li], marker_line_indices):
                        line_tags[li] = 'split'
                        return reassemble(lines, line_tags)
                return '<p>!!!' + para_content + '</p>'
            return full_para

        if len(markers) < 2:
            # Fewer than 2 sense markers means there is no sequence to
            # protect, so every candidate orth line is safe to split at.
            for li in candidate_orth_lines:
                line_tags[li] = 'split'
        else:
            last_marker_li = marker_line_indices[-1]

            # Orth lines after the last sense marker can always be split —
            # they can't disrupt the marker sequence. Orth lines interspersed
            # among markers ("between_markers") need combinatorial checking.
            always_break = []
            between_markers = []
            for li in candidate_orth_lines:
                if li > last_marker_li:
                    always_break.append(li)
                else:
                    between_markers.append(li)

            # Try all 2^n combinations of potential split points (both
            # between-marker orths and inline orths) to find which ones keep
            # every partition's sense sequence valid. Cap at 20 bits to avoid
            # exponential blowup; if exceeded, skip inline candidates.
            n_bm = len(between_markers)
            n_il = len(inline_orth_lines)
            if n_bm + n_il > 20:
                total_bits = n_bm
                use_inline = False
            else:
                total_bits = n_bm + n_il
                use_inline = True

            valid_perms = []
            for mask in range(1 << total_bits):
                active_line = [between_markers[i] for i in range(n_bm) if (mask >> i) & 1]
                active_inline = ([inline_orth_lines[i] for i in range(n_il) if (mask >> (n_bm + i)) & 1]
                                 if use_inline else [])
                all_resets = active_line + always_break + active_inline
                if try_partition_combination(markers, all_resets, marker_line_indices):
                    valid_perms.append((set(active_line), set(active_inline)))

            if not valid_perms:
                return '<p>!!!' + para_content + '</p>'

            # A line becomes a split if it appears in *any* valid combination.
            for li in always_break:
                line_tags[li] = 'split'
            for li in between_markers:
                if any(li in vp[0] for vp in valid_perms):
                    line_tags[li] = 'split'
            for li in inline_orth_lines:
                if any(li in vp[1] for vp in valid_perms):
                    line_tags[li] = 'split'

        # Line-initial orths that weren't chosen as splits still shouldn't
        # keep a bare <br/>\n — join them to the previous line with ' <br/>'.
        for li in candidate_orth_lines:
            if line_tags[li] != 'split':
                line_tags[li] = 'join'

        return reassemble(lines, line_tags)

    html = re.sub(r'<p>(.*?)</p>', process_paragraph, html, flags=re.DOTALL)
    return html


def convert_senses_to_lists(html):
    """Convert sense markers (I., 1., a., α., aa.) into nested <ol>/<li> HTML lists."""

    sense_pattern = r'(?:<br/>\n?)\s*([0-9]+|[a-z]{1,2}|[A-Z]|[IVXivx]+|[α-ω])([.,;])?(?=\s|<|$)'

    def process_paragraph(match):
        full_para = match.group(0)
        para_content = match.group(1)

        # Skip !!!-marked paragraphs
        if para_content.startswith('!!!'):
            return full_para

        # Find the first <br/> to skip headword line
        first_br = para_content.find('<br/>')
        if first_br < 0:
            return '<p>' + para_content + '</p>'
        content_after_hw = para_content[first_br:]

        # Find all sense markers after the headword
        raw_markers = []
        for m in re.finditer(sense_pattern, content_after_hw):
            marker_text = m.group(1)
            mtype, mval = get_marker_type_and_value(marker_text)
            if mtype == 'unknown':
                continue
            # abs_start: where <br/> begins; abs_marker_start: where marker text begins
            abs_start = first_br + m.start()
            abs_marker_start = first_br + m.start(1)
            raw_markers.append((abs_start, abs_marker_start, mtype, mval))

        if not raw_markers:
            return full_para

        # Compute nesting levels dynamically based on marker order
        mtv = [(mtype, mval) for _, _, mtype, mval in raw_markers]
        _, dyn_levels = _dynamic_stack_analyze(mtv)

        markers = [(s, ms, lv, mt)
                   for (s, ms, mt, _), lv in zip(raw_markers, dyn_levels)
                   if lv is not None]

        if not markers:
            return full_para

        # Build output: preamble + list structure
        # Split at each <br/> before a marker, keeping the marker text
        parts = []
        prev_end = 0
        for abs_start, abs_marker_start, level, mtype in markers:
            # Text before this <br/>
            preamble = para_content[prev_end:abs_start]
            parts.append(('text', preamble))
            parts.append(('marker', level, mtype))
            # Continue from the marker text (preserving it in output)
            prev_end = abs_marker_start

        # Remaining content after last marker
        trailing = para_content[prev_end:]

        # Now build the output with a stack
        stack = []
        output = []

        for part in parts:
            if part[0] == 'text':
                output.append(part[1])
            else:
                _, level, mtype = part
                # Close deeper levels
                while stack and stack[-1] > level:
                    output.append('</li></ol>')
                    stack.pop()
                # Sibling
                if stack and stack[-1] == level:
                    output.append('</li> <li>')
                else:
                    # New nested level
                    css_class = _CSS_CLASS.get(mtype, 'sense')
                    output.append(f' <ol class="{css_class}"><li>')
                    stack.append(level)

        # Append trailing content
        output.append(trailing)

        # Close remaining stack
        while stack:
            output.append('</li></ol>')
            stack.pop()

        return '<p>' + ''.join(output) + '</p>'

    html = re.sub(r'<p>(.*?)</p>', process_paragraph, html, flags=re.DOTALL)
    return html
