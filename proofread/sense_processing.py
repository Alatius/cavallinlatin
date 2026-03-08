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
    """
    Split paragraphs at line-initial <orth> tags when doing so does not break
    valid sense number sequences. Orths that cannot be split (because they'd
    break a sequence) are joined with " — " instead.
    """

    def is_sequence_valid(markers_to_check):
        """Check if a sequence of markers is valid using stack-based nesting."""
        if len(markers_to_check) < 1:
            return True

        # Stack of (level, last_value) mirroring convert_senses_to_lists
        stack = []

        for marker, mtype, mval, punct in markers_to_check:
            if mtype == 'unknown':
                continue
            level = _marker_level(mtype)
            if level is None:
                continue

            # Pop deeper levels (returning to a shallower nesting)
            while stack and stack[-1][0] > level:
                stack.pop()

            if stack and stack[-1][0] == level:
                # Sibling: must be exactly prev + 1
                prev_val = stack[-1][1]
                if mval != prev_val + 1:
                    return False
                stack[-1] = (level, mval)
            else:
                # New nested level (or first marker): check initial value
                if mtype in ('letter', 'letter_upper', 'double_letter', 'greek'):
                    if mval != 0:
                        return False
                elif mtype in ('digit', 'roman_lower', 'roman_upper'):
                    if mval != 1:
                        return False
                stack.append((level, mval))

        return True

    def try_partition_combination(markers, active_resets, marker_positions):
        """Try a specific combination of reset points and check if all partitions are valid."""
        if not active_resets:
            return is_sequence_valid(markers)

        current_partition = []
        for i, (pos, marker_info) in enumerate(zip(marker_positions, markers)):
            should_reset = False
            if i > 0:
                for orth_pos in active_resets:
                    if marker_positions[i-1] < orth_pos < pos:
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

    def process_paragraph(match):
        full_para = match.group(0)
        para_content = match.group(1)

        # Find the first <br/> to skip headword line
        first_br = para_content.find('<br/>')
        content_for_markers = para_content[first_br:] if first_br >= 0 else para_content
        offset = first_br if first_br >= 0 else 0

        # Extract sense markers (after <br/>\n)
        sense_pattern = r'(?:<br/>\n)\s*([0-9]+|[a-z]{1,2}|[A-Z]|[IVXivx]+|[α-ω])([.,;])?(?=\s|<)'
        markers = []
        marker_positions = []
        for m in re.finditer(sense_pattern, content_for_markers, re.MULTILINE):
            marker = m.group(1)
            punct = m.group(2)
            mtype, mval = get_marker_type_and_value(marker)
            markers.append((marker, mtype, mval, punct))
            marker_positions.append(offset + m.start())

        # Find candidate orth split points: line-initial <orth> tags (preceded by <br/>\n)
        candidate_orths = []
        candidate_orth_positions = []
        candidate_orth_tags = []
        for m in re.finditer(r'<br/>\n(<orth[^>]*>)', para_content):
            candidate_orths.append(m)
            candidate_orth_positions.append(m.start())
            candidate_orth_tags.append(m.group(1))

        # All <orth> positions (including inline) for sequence validity checking
        all_orth_positions = [m.start() for m in re.finditer(r'<orth[^>]*>', para_content)]

        # Helper: check if any combination of the given orth positions makes the
        # marker sequence valid (used for !!! detection)
        def any_valid_partition(orth_positions):
            n = len(orth_positions)
            if n > 20:
                return True  # too many to check, assume valid
            for mask in range(1 << n):
                active = [orth_positions[i] for i in range(n) if (mask >> i) & 1]
                if try_partition_combination(markers, active, marker_positions):
                    return True
            return False

        # Inline orths (not line-initial) that can serve as reset/split points
        candidate_orth_set = set(candidate_orth_positions)
        # Exclude inline orths on lines that start with a sense number,
        # since splitting there would break the sense numbering.
        sense_line_re = re.compile(r'<br/>\n\s*(?:[0-9]+|[a-z]{1,2}|[A-Z]|[IVXivx]+|[α-ω])[.,;]?\s')
        def is_on_sense_line(orth_pos):
            br_pos = para_content.rfind('<br/>\n', 0, orth_pos)
            return br_pos >= 0 and sense_line_re.match(para_content, br_pos)
        inline_orth_positions = [p for p in all_orth_positions
                                 if p not in candidate_orth_set
                                 and not is_on_sense_line(p)]

        if not candidate_orths:
            # No line-initial orths to split at; still check sequence validity
            if len(markers) >= 2 and not is_sequence_valid(markers):
                # Try inline orths as split points
                for orth_pos in inline_orth_positions:
                    if try_partition_combination(markers, [orth_pos], marker_positions):
                        # Find the <br/>\n before this orth to split there
                        br_pos = para_content.rfind('<br/>\n', 0, orth_pos)
                        if br_pos >= 0:
                            br_end = br_pos + len('<br/>\n')
                            result = para_content[:br_pos] + '</p>\n\n<p>' + para_content[br_end:]
                            return '<p>' + result
                return '<p>!!!' + para_content
            return full_para

        # If no markers or only 1 marker, all candidate orths become paragraph breaks
        inline_break_positions = set()
        if len(markers) < 2:
            break_positions = set(candidate_orth_positions)
        else:
            # Find which candidate orths are between markers (and thus affect sequences)
            last_marker_pos = marker_positions[-1] if marker_positions else -1

            # Orths after the last marker can always be breaks
            always_break = set()
            between_markers = []
            between_markers_positions = []
            for i, pos in enumerate(candidate_orth_positions):
                if pos > last_marker_pos:
                    always_break.add(pos)
                else:
                    between_markers.append(i)
                    between_markers_positions.append(pos)

            # Try all 2^n combinations of the between-markers line-initial orths,
            # and for each, also try all 2^m combinations of inline orths
            n = len(between_markers)
            m = len(inline_orth_positions)
            if n + m > 20:
                # Too many candidates; just use line-initial orths without inline
                total_bits = n
                use_inline_combos = False
            else:
                total_bits = n + m
                use_inline_combos = True

            valid_permutations = []
            for mask in range(1 << total_bits):
                active_line_resets = [between_markers_positions[i] for i in range(n) if (mask >> i) & 1]
                if use_inline_combos:
                    active_inline_resets = [inline_orth_positions[i] for i in range(m) if (mask >> (n + i)) & 1]
                else:
                    active_inline_resets = []
                all_resets = active_line_resets + list(always_break) + active_inline_resets
                if try_partition_combination(markers, all_resets, marker_positions):
                    valid_permutations.append((set(active_line_resets), set(active_inline_resets)))

            # No valid permutations — mark for manual review, don't modify
            if not valid_permutations:
                return '<p>!!!' + para_content

            # Classify each candidate line-initial orth
            break_positions = set(always_break)
            for i, pos in enumerate(between_markers_positions):
                is_break_in_any = any(pos in vp[0] for vp in valid_permutations)
                if is_break_in_any:
                    break_positions.add(pos)

            # Collect inline orths that appear in any valid permutation
            inline_break_positions = set()
            for _, inline_set in valid_permutations:
                inline_break_positions |= inline_set

        # Collect all split operations: (start_pos, end_pos, replacement)
        # Process from end to start to preserve positions
        operations = []

        # Line-initial orth operations
        for i in range(len(candidate_orths)):
            m = candidate_orths[i]
            pos = candidate_orth_positions[i]
            orth_tag = candidate_orth_tags[i]
            if pos in break_positions:
                operations.append((m.start(), m.end(), f'</p>\n\n<p>{orth_tag}'))
            else:
                operations.append((m.start(), m.end(), f' </br>{orth_tag}'))

        # Inline orth split operations (split at preceding <br/>\n)
        for orth_pos in inline_break_positions:
            br_pos = para_content.rfind('<br/>\n', 0, orth_pos)
            if br_pos >= 0:
                operations.append((br_pos, br_pos + len('<br/>\n'), '</p>\n\n<p>'))

        # Apply from end to start
        result = para_content
        for start, end, replacement in sorted(operations, key=lambda x: x[0], reverse=True):
            result = result[:start] + replacement + result[end:]

        return '<p>' + result

    # Match each paragraph
    html = re.sub(r'<p>(.*?)(?=<p>|$)', process_paragraph, html, flags=re.DOTALL)

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

        # Strip </p> and trailing whitespace so closing tags end up inside the paragraph
        suffix = ''
        stripped = para_content
        close_idx = stripped.rfind('</p>')
        if close_idx >= 0:
            suffix = stripped[close_idx:]
            stripped = stripped[:close_idx]
        para_content = stripped

        # Find the first <br/> to skip headword line
        first_br = para_content.find('<br/>')
        if first_br < 0:
            return '<p>' + para_content + suffix
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
                    output.append('</li>')
                    output.append('\n<li>')
                else:
                    # New nested level
                    css_class = _css_class(mtype)
                    output.append(f'\n<ol class="{css_class}"><li>')
                    stack.append(level)

        # Append trailing content
        output.append(trailing)

        # Close remaining stack
        while stack:
            output.append('</li></ol>')
            stack.pop()

        return '<p>' + ''.join(output) + suffix

    html = re.sub(r'<p>(.*?)(?=<p>|$)', process_paragraph, html, flags=re.DOTALL)
    return html
