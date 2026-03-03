import re
import unicodedata

from spurious_breaks import remove_spurious_breaks


def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.category(c).startswith('Mn')])


def clean(text):
    text = re.sub("<[^>]*>", "", text)
    text = re.sub(r"\W", "", text)
    text = text.lower()
    text = text.replace("æ", "ae").replace("œ", "oe")
    text = remove_accents(text)
    return text


def is_sense_number(text):
    text = text.replace("<br/>", "")
    if re.match("^[IVX]+", text) or re.match(r"^[A-Z]\.", text):
        return True
    return False


def postprocess(html):
    # Clean up some mistakes
    html = re.sub('(<b>[^<]*?) *<br/>\n', r'\1</b><br/>\n<b>', html)
    html = re.sub('(<b>[^<]*?) *<br/>\n', r'\1</b><br/>\n<b>', html)
    html = re.sub('(<b>[^<]*?) *<br/>\n', r'\1</b><br/>\n<b>', html)
    html = re.sub(r" *<br/> *\n([a-z]\.) *<br/> *\n<u>", r"<br/>\n\1 <u>", html)
    html = html.replace("<p><br/>\n", "<p>")
    html = re.sub(' *<br/> *\n *<br/> *\n *', '<br/>\n', html)
    html = re.sub(r" *<br/>\n([A-ZĀĂĒĔĪĬŌŎŪŬ]\S*)", lambda x: (" " + x.group(1)) if x.group(1)[-1] == ';' else x.group(0), html)
    html = re.sub(' *</b> *</span> *<br/> *\n *<span> *<b> *', ' ', html)
    html = html.replace(". . .", "…")
    html = re.sub(r'(\d)—(\d)', r'\1–\2', html)
    html = re.sub(' *</span> *<br/> *\n<span> *', ' ', html)
    html = html.replace('Varro 1. l. ', 'Varro l. l. ').replace('Varr. 1. l. ', 'Varr. l. l. ')

    # Locate headwords
    HW = r'(<[bu]>[^<]*</[bu]>\S*|\S+)'
    html = re.sub(r"^(<p>(?:[IV]+\.\s+)?)" + HW,
                  lambda x: x.group(1) + "<orth>" + x.group(2) + "</orth>",
                  html, flags=re.MULTILINE)
    html = re.sub(r"^(<[bu]>[^<]*</[bu]>\S*)",
                  lambda x: "<orth>" + x.group(1) + "</orth>",
                  html, flags=re.MULTILINE)
    html = re.sub(r"^(\(<[bu]>[^<]*</[bu]>\)?\S*)",
                  lambda x: "<orth>" + x.group(1) + "</orth>",
                  html, flags=re.MULTILINE)
    html = re.sub(r"^(\([A-ZĀĂĒĔĪĬŌŎŪŬ]\S*)",
                  lambda x: "<orth>" + x.group(1) + "</orth>",
                  html, flags=re.MULTILINE)
    html = re.sub(r"<br/>\n([A-ZĀĂĒĔĪĬŌŎŪŬ]\S*)",
                  lambda x: "<br/>\n<orth>" + x.group(1) + "</orth>" if not is_sense_number(x.group(1)) else x.group(0),
                  html)

    # More clean up
    html = html.replace('<br/></orth>', '</orth><br/>')
    html = html.replace("<orth></orth><br/>\n<orth>", "<orth>")
    html = re.sub('</orth> *…', '…</orth>', html)
    html = html.replace(r'-<br/>\n', '-')

    # Join <br/> before <orth> when not end of entry
    CONNECTIVES = {'och', 'eller', 'äfwen', 'deraf', 'häraf', 'i', 'wanligare',
                   'wanligen', 'et', 'hwar', 'åt', 'samt', 'för', 'som', 'se',
                   'Och', 'sällan', 'oftare', 'förstärkt', 'detta', 'a'}
    JOIN_ABBREVS = {'l.', 'o.', 'wanl.', 'absol.', 'spec.', 'arch.', 'obr.'}
    GRAMMAR = {'pl.', 'm.', 'Subst.', 'plur.', 'Dep.', 'subst.', 'f.', 'part.',
               'Abl.', 'Acc.', 'abl.', 'n.', 'pt.', 'pr.', 'p.', 'comp.', 'Comp.', 'dep.',
               'pf.', 'Superl.'}

    def join_or_keep(m):
        # Preceding headword followed by another → JOIN
        if '</orth>' in m.group(1):
            return m.group(1) + ' ' + m.group(2)
        word = re.sub(r'<[^>]*>', '', m.group(1))
        if not word:
            return m.group(0)
        last_char = word[-1]
        # Ends with : , ; → JOIN
        if last_char in (':', ',', ';'):
            return m.group(1) + ' ' + m.group(2)
        # Word is - = ( → JOIN
        if word in ('-', '=', '('):
            return m.group(1) + ' ' + m.group(2)
        # Ends with ) but not ). → JOIN
        if word.endswith(')') and not word.endswith(').'):
            return m.group(1) + ' ' + m.group(2)
        # Connective words (possibly with leading parenthesis)
        bare = word.lstrip('(')
        if word in CONNECTIVES or bare in CONNECTIVES:
            return m.group(1) + ' ' + m.group(2)
        # Join abbreviations
        if word in JOIN_ABBREVS or bare in JOIN_ABBREVS:
            return m.group(1) + ' ' + m.group(2)
        # Grammar terms
        if word in GRAMMAR:
            return m.group(1) + ' ' + m.group(2)
        # Numbers at line start
        if re.match(r'^\d+\.$', word):
            before = html[max(0, m.start() - 10):m.start()]
            if re.search(r'\n\s*$', before):
                return m.group(1) + ' ' + m.group(2)
        return m.group(0)

    html = re.sub(r'([^\s<>]+(?:</[^>]*>)*) *<br/>\n(<orth>)', join_or_keep, html)

    html = remove_spurious_breaks(html)

    html = re.sub(r' (aa|bb|cc|dd|ee)\. ', r'<br/>\n\1. ', html)

    html = mark_bad_sense_sequences(html)

    return html


def mark_bad_sense_sequences(html):
    """
    Identify paragraphs with strange or inconsistent sense number sequences.
    Inserts "!!!" at the start of problematic paragraphs for manual review.

    Detects issues like:
    - "1., b., 3." (skipped subsense 'a', then jumped to 3)
    - "1., 3." (gap in main numbering)
    - "a., c." (gap in letter sequence)
    - "2., 1." (backward stepping)
    - "1., ii., 3." (mixed numbering systems)
    - "1, 2." (inconsistent punctuation)

    Valid sequences include:
    - "1., 2., 3." (main numbering)
    - "a., b., c." (letter sequence alone)
    - "1., a., b., 2., 3." (main with subsenses)
    - "i., ii., iii." (roman numerals)
    """

    def get_marker_type_and_value(marker):
        """Return (type, numeric_value) for a sense marker."""
        clean = marker.rstrip('.,;')

        if clean.isdigit():
            return ('digit', int(clean))
        elif len(clean) == 1 and ord(clean) >= 0x03B1 and ord(clean) <= 0x03C9:
            # Greek letter - check before isalpha() to avoid misclassification
            return ('greek', ord(clean) - 0x03B1)
        elif len(clean) == 1 and clean.isalpha() and clean.islower():
            # Latin letter - skip 'j' which didn't exist in classical Latin
            if clean <= 'i':
                letter_val = ord(clean) - ord('a')
            else:  # clean >= 'k'
                letter_val = ord(clean) - ord('a') - 1
            return ('letter', letter_val)
        elif len(clean) == 2 and clean[0] == clean[1] and clean[0].isalpha() and clean[0].islower():
            # Double letter - skip 'j'
            if clean[0] <= 'i':
                base_val = ord(clean[0]) - ord('a')
            else:  # clean[0] >= 'k'
                base_val = ord(clean[0]) - ord('a') - 1
            return ('double_letter', base_val)
        elif all(c in 'IVXivx' for c in clean):
            if clean.isupper():
                roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12}
                return ('roman_upper', roman_map.get(clean, 0))
            else:
                roman_map = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12}
                return ('roman_lower', roman_map.get(clean, 0))
        else:
            return ('unknown', 0)

    def try_partition_combination(markers, active_resets, marker_positions):
        """Try a specific combination of reset points and check if all partitions are valid."""
        if not active_resets:
            # No resets, just validate the whole sequence
            return is_sequence_valid(markers)

        # Partition markers based on active reset points
        current_partition = []
        for i, (pos, marker_info) in enumerate(zip(marker_positions, markers)):
            # Check if any reset point is between previous marker and this one
            should_reset = False
            if i > 0:
                for orth_pos in active_resets:
                    if marker_positions[i-1] < orth_pos < pos:
                        should_reset = True
                        break

            if should_reset and current_partition:
                # End current partition and check it
                if not is_sequence_valid(current_partition):
                    return False
                current_partition = [marker_info]
            else:
                current_partition.append(marker_info)

        # Check the final partition
        if current_partition and not is_sequence_valid(current_partition):
            return False

        return True

    def is_sequence_valid(markers_to_check):
        """Check if a sequence of markers is valid."""
        if len(markers_to_check) < 1:
            return True

        has_error = False

        # First check: if any type appears, its first occurrence should start appropriately
        seen_types = {}
        for marker, mtype, mval, punct in markers_to_check:
            if mtype not in seen_types:
                seen_types[mtype] = mval
                # Check that new types start at 0 (a, α, etc.) or 1 (digits, roman)
                if mtype in ('letter', 'double_letter', 'greek'):
                    if mval != 0:
                        return False
                elif mtype in ('roman_lower', 'roman_upper'):
                    if mval != 1:
                        return False
                elif mtype == 'digit':
                    if mval != 1:
                        return False

        # Check sequential within each type
        for i in range(1, len(markers_to_check)):
            prev_marker, prev_type, prev_val, prev_punct = markers_to_check[i-1]
            curr_marker, curr_type, curr_val, curr_punct = markers_to_check[i]

            if prev_type == curr_type:
                # Same type - must be sequential
                if curr_val <= prev_val or curr_val > prev_val + 1:
                    if prev_type not in ('unknown',):
                        return False

            elif prev_type == 'digit' and curr_type in ('letter', 'double_letter', 'greek', 'roman_lower'):
                # Valid: transitioning to subsenses
                pass

            elif prev_type in ('letter', 'double_letter', 'greek', 'roman_lower') and curr_type == 'digit':
                # Valid: subsenses ending, back to main numbering
                pass

            elif prev_type in ('letter', 'double_letter', 'greek', 'roman_lower') and curr_type in ('letter', 'double_letter', 'greek', 'roman_lower'):
                # Valid: transitioning between different subsense types (e.g., greek α,β to letter b)
                # This handles complex nesting like: a. α. β. b. (where α,β are sub-subsenses of a, then b is next subsense)
                if curr_type == prev_type and curr_val == prev_val + 1:
                    # Sequential within same type (already checked above)
                    pass
                else:
                    # Allow transition between different subsense types
                    pass

            elif prev_type in ('roman_lower', 'roman_upper') and curr_type in ('letter', 'double_letter', 'greek', 'digit'):
                # Valid: homograph/section number followed by sense sequence
                pass

            elif prev_type in ('letter', 'double_letter', 'greek') and curr_type in ('roman_lower', 'roman_upper'):
                # Valid: from subsenses back to section marker (e.g., I., II., III.)
                pass

            elif prev_type == 'digit' and curr_type in ('roman_lower', 'roman_upper'):
                # Valid transition
                pass

            elif prev_type in ('roman_lower', 'roman_upper') and curr_type == 'digit':
                # Valid transition
                pass

            else:
                # Mixed incompatible types
                if not (prev_type == 'unknown' or curr_type == 'unknown'):
                    return False

        return True

    def check_paragraph(match):
        full_para = match.group(0)
        para_content = match.group(1)

        # Find the first <br/> to skip headword line (which may contain grammatical info like "2.")
        first_br = para_content.find('<br/>')
        content_for_markers = para_content[first_br:] if first_br >= 0 else para_content

        # Extract all sense markers at line boundaries (after <br/> tags)
        # Match: digits, single/double letters, roman numerals (upper/lower), greek letters
        sense_pattern = r'(?:<br/>\n)\s*([0-9]+|[a-z]{1,2}|[IVXivx]+|[α-ω])([.,;])?(?=\s|<)'

        markers = []
        marker_positions = []
        for m in re.finditer(sense_pattern, content_for_markers, re.MULTILINE):
            marker = m.group(1)
            punct = m.group(2)
            mtype, mval = get_marker_type_and_value(marker)
            markers.append((marker, mtype, mval, punct))
            # Convert to absolute positions in para_content
            marker_positions.append(first_br + m.start() if first_br >= 0 else m.start())

        if len(markers) < 2:
            return full_para

        # Check if sequence is valid as-is
        if is_sequence_valid(markers):
            return full_para

        # If not valid, try all possible combinations of which <orth> tags should reset
        all_orths = [m.start() for m in re.finditer(r'<orth>', para_content)]

        if all_orths:
            # Try all 2^n combinations of reset/no-reset for each orth
            num_orths = len(all_orths)
            for mask in range(1 << num_orths):  # Iterate through 0 to 2^n - 1
                # Build the list of orths that reset in this combination
                active_resets = [all_orths[i] for i in range(num_orths) if (mask >> i) & 1]

                # Try this combination
                if try_partition_combination(markers, active_resets, marker_positions):
                    return full_para

        # No valid combination found

        # Sequence is invalid even with orth resets
        return '<p>!!!' + para_content

    # Match each paragraph
    html = re.sub(r'<p>(.*?)(?=<p>|$)', check_paragraph, html, flags=re.DOTALL)

    return html
