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


def _marker_level(mtype):
    """Return the nesting level for a marker type."""
    level_map = {
        'letter_upper': 0,
        'roman_upper': 1,
        'digit': 2,
        'letter': 3,
        'greek': 4,
        'roman_lower': 5,
        'double_letter': 6,
    }
    return level_map.get(mtype)


def _css_class(mtype):
    """Return a CSS class for the list style matching the marker type."""
    class_map = {
        'letter_upper': 'sense-Alpha',
        'roman_upper': 'sense-Roman',
        'digit': 'sense-decimal',
        'letter': 'sense-alpha',
        'greek': 'sense-greek',
        'roman_lower': 'sense-roman',
        'double_letter': 'sense-double-alpha',
    }
    return class_map.get(mtype, 'sense')


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
        r'^\s*([0-9]+|[a-z]{1,2}|[A-Z]|[IVXivx]+|[α-ω])([.,;])?(?=\s|<)'
    )
    ORTH_INITIAL_RE = re.compile(r'^<orth[^>]*>')
    ORTH_ANY_RE = re.compile(r'<orth[^>]*>')

    def is_sequence_valid(markers_to_check):
        """Check if a sequence of markers is valid using stack-based nesting."""
        if len(markers_to_check) < 1:
            return True

        stack = []

        for marker, mtype, mval, punct in markers_to_check:
            if mtype == 'unknown':
                continue
            level = _marker_level(mtype)
            if level is None:
                continue

            while stack and stack[-1][0] > level:
                stack.pop()

            if stack and stack[-1][0] == level:
                prev_val = stack[-1][1]
                if mval != prev_val + 1:
                    return False
                stack[-1] = (level, mval)
            else:
                if mtype in ('letter', 'letter_upper', 'double_letter', 'greek'):
                    if mval != 0:
                        return False
                elif mtype in ('digit', 'roman_lower', 'roman_upper'):
                    if mval != 1:
                        return False
                stack.append((level, mval))

        return True

    def try_partition_combination(markers, active_resets, marker_line_indices):
        """Try a specific combination of reset line indices and check if all partitions are valid."""
        if not active_resets:
            return is_sequence_valid(markers)

        current_partition = []
        for i, (li, marker_info) in enumerate(zip(marker_line_indices, markers)):
            should_reset = False
            if i > 0:
                for reset_li in active_resets:
                    if marker_line_indices[i-1] < reset_li < li:
                        should_reset = True
                        break

            if should_reset and current_partition:
                if not is_sequence_valid(current_partition):
                    return False
                current_partition = [marker_info]
            else:
                current_partition.append(marker_info)

        if current_partition and not is_sequence_valid(current_partition):
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

        # Split content into lines at <br/>\n boundaries
        lines = para_content.split('<br/>\n')
        if len(lines) <= 1:
            return full_para

        # Extract sense markers from lines[1:] (skip headword line)
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

        # Find line-initial orth candidates (lines starting with <orth>)
        candidate_orth_lines = []
        for li in range(1, len(lines)):
            if ORTH_INITIAL_RE.match(lines[li]):
                candidate_orth_lines.append(li)

        # Find inline orth candidates (lines containing <orth> but not at start,
        # and not starting with a sense marker)
        inline_orth_lines = []
        for li in range(1, len(lines)):
            if ORTH_INITIAL_RE.match(lines[li]):
                continue
            if SENSE_RE.match(lines[li]):
                continue
            if ORTH_ANY_RE.search(lines[li]):
                inline_orth_lines.append(li)

        # Initialize per-line tags
        line_tags = ['keep'] * len(lines)

        if not candidate_orth_lines:
            # No line-initial orths to split at; check sequence validity
            if len(markers) >= 2 and not is_sequence_valid(markers):
                # Try inline orths as split points
                for li in inline_orth_lines:
                    if try_partition_combination(markers, [li], marker_line_indices):
                        line_tags[li] = 'split'
                        return reassemble(lines, line_tags)
                return '<p>!!!' + para_content + '</p>'
            return full_para

        if len(markers) < 2:
            # No sense sequence to protect — all candidate orths become splits
            for li in candidate_orth_lines:
                line_tags[li] = 'split'
        else:
            last_marker_li = marker_line_indices[-1]

            # Orths after the last marker can always be splits
            always_break = []
            between_markers = []
            for li in candidate_orth_lines:
                if li > last_marker_li:
                    always_break.append(li)
                else:
                    between_markers.append(li)

            # Try all 2^n combinations of between-markers line-initial orths
            # and (if feasible) inline orths
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

            for li in always_break:
                line_tags[li] = 'split'
            for li in between_markers:
                if any(li in vp[0] for vp in valid_perms):
                    line_tags[li] = 'split'
            for li in inline_orth_lines:
                if any(li in vp[1] for vp in valid_perms):
                    line_tags[li] = 'split'

        # Non-split line-initial orths get joined
        for li in candidate_orth_lines:
            if line_tags[li] != 'split':
                line_tags[li] = 'join'

        return reassemble(lines, line_tags)

    html = re.sub(r'<p>(.*?)</p>', process_paragraph, html, flags=re.DOTALL)
    return html


def convert_senses_to_lists(html):
    """Convert sense markers (I., 1., a., α., aa.) into nested <ol>/<li> HTML lists."""

    sense_pattern = r'(?:<br/>\n?)\s*([0-9]+|[a-z]{1,2}|[A-Z]|[IVXivx]+|[α-ω])([.,;])?(?=\s|<)'

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
        markers = []
        for m in re.finditer(sense_pattern, content_after_hw):
            marker_text = m.group(1)
            mtype, mval = get_marker_type_and_value(marker_text)
            level = _marker_level(mtype)
            if level is None:
                continue
            # abs_start: where <br/> begins; abs_marker_start: where marker text begins
            abs_start = first_br + m.start()
            abs_marker_start = first_br + m.start(1)
            markers.append((abs_start, abs_marker_start, level, mtype))

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
                    css_class = _css_class(mtype)
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
