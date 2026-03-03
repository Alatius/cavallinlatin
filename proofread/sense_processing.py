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
        """Check if a sequence of markers is valid."""
        if len(markers_to_check) < 1:
            return True

        seen_types = {}
        for marker, mtype, mval, punct in markers_to_check:
            if mtype not in seen_types:
                seen_types[mtype] = mval
                if mtype in ('letter', 'letter_upper', 'double_letter', 'greek'):
                    if mval != 0:
                        return False
                elif mtype in ('roman_lower', 'roman_upper'):
                    if mval != 1:
                        return False
                elif mtype == 'digit':
                    if mval != 1:
                        return False

        for i in range(1, len(markers_to_check)):
            prev_marker, prev_type, prev_val, prev_punct = markers_to_check[i-1]
            curr_marker, curr_type, curr_val, curr_punct = markers_to_check[i]

            if prev_type == curr_type:
                if curr_val <= prev_val or curr_val > prev_val + 1:
                    if prev_type not in ('unknown',):
                        return False
            elif prev_type == 'digit' and curr_type in ('letter', 'double_letter', 'greek', 'roman_lower'):
                pass
            elif prev_type in ('letter', 'double_letter', 'greek', 'roman_lower') and curr_type == 'digit':
                pass
            elif prev_type in ('letter', 'double_letter', 'greek', 'roman_lower') and curr_type in ('letter', 'double_letter', 'greek', 'roman_lower'):
                pass
            elif prev_type in ('roman_lower', 'roman_upper', 'letter_upper') and curr_type in ('letter', 'double_letter', 'greek', 'digit'):
                pass
            elif prev_type in ('letter', 'double_letter', 'greek') and curr_type in ('roman_lower', 'roman_upper', 'letter_upper'):
                pass
            elif prev_type == 'digit' and curr_type in ('roman_lower', 'roman_upper', 'letter_upper'):
                pass
            elif prev_type in ('roman_lower', 'roman_upper', 'letter_upper') and curr_type == 'digit':
                pass
            elif prev_type in ('roman_upper', 'letter_upper') and curr_type in ('roman_upper', 'letter_upper'):
                pass
            else:
                if not (prev_type == 'unknown' or curr_type == 'unknown'):
                    return False

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
        for m in re.finditer(r'<br/>\n<orth>', para_content):
            candidate_orths.append(m)
            candidate_orth_positions.append(m.start())

        # All <orth> positions (including inline) for sequence validity checking
        all_orth_positions = [m.start() for m in re.finditer(r'<orth>', para_content)]

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

        if not candidate_orths:
            # No line-initial orths to split at; still check sequence validity
            if len(markers) >= 2 and not is_sequence_valid(markers):
                if not any_valid_partition(all_orth_positions):
                    return '<p>!!!' + para_content
            return full_para

        # If no markers or only 1 marker, all candidate orths become paragraph breaks
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

            # Inline orths (not line-initial) that can serve as optional reset points
            inline_orth_positions = [p for p in all_orth_positions
                                     if p not in set(candidate_orth_positions)]

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
                    valid_permutations.append(set(active_line_resets))

            # No valid permutations — mark for manual review, don't modify
            if not valid_permutations:
                return '<p>!!!' + para_content

            # Classify each candidate line-initial orth
            break_positions = set(always_break)
            for i, pos in enumerate(between_markers_positions):
                # If this orth is a reset in at least one valid permutation, it's a break
                is_break_in_any = any(pos in vp for vp in valid_permutations)
                if is_break_in_any:
                    break_positions.add(pos)

        # Apply changes: process candidate orths from end to start to preserve positions
        result = para_content
        for i in range(len(candidate_orths) - 1, -1, -1):
            m = candidate_orths[i]
            pos = candidate_orth_positions[i]
            if pos in break_positions:
                # Replace <br/>\n<orth> with </p>\n\n<p><orth>
                result = result[:m.start()] + '</p>\n\n<p><orth>' + result[m.end():]
            else:
                # Remove \n from <br/>\n<orth>
                result = result[:m.start()] + ' </br><orth>' + result[m.end():]

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
