import re
import unicodedata
from collections import defaultdict

from fodt_to_html import convert_fodt_files
from postprocess import postprocess


def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join(c for c in nfkd_form if not unicodedata.category(c).startswith('Mn'))


def roman_to_int(s):
    """Convert a Roman numeral string (e.g. 'III', 'IV') to an integer."""
    values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    result = 0
    for i, c in enumerate(s):
        if i + 1 < len(s) and values.get(c, 0) < values.get(s[i + 1], 0):
            result -= values.get(c, 0)
        else:
            result += values.get(c, 0)
    return result


# Mixed <b>X</b><u>rest</u> markup: these are proper nouns (normalize to <b>X</b>rest).
# All others with this pattern are derived forms (normalize to <u>Xrest</u>).
MIXED_PROPER_IDS = {'Aethiops', 'Aloeus', 'Eburones', 'Gergovia', 'Ocnus', 'Oreas'}

MARKUP_LEVELS = {'plain': 0, 'derived': 1, 'proper': 2, 'major': 3}
LEVEL_TO_TYPE = {v: k for k, v in MARKUP_LEVELS.items()}


def make_entry_id(headword_html):
    """Generate an entry ID from headword HTML: strip tags, remove diacritics,
    remove punctuation."""
    text = re.sub(r'<[^>]*>', '', headword_html)
    text = text.replace('æ', 'ae').replace('œ', 'oe').replace('Æ', 'Ae').replace('Œ', 'Oe')
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.category(c).startswith('Mn'))
    text = re.sub(r'[^\w]', '', text)
    return text


def normalize_mixed_markup(content):
    """Normalize <b>X</b><u>rest</u> patterns within <orth> tags.

    Proper nouns (MIXED_PROPER_IDS) become first-letter-bold: <b>X</b>rest
    All others (In-, Sub-, Super- compounds) become underlined: <u>Xrest</u>
    """
    def normalize_match(m):
        orth_open = m.group(1)
        bold_text = m.group(2)
        underline_text = m.group(3)
        trailing = m.group(4)

        combined_id = make_entry_id(bold_text + underline_text)

        if combined_id in MIXED_PROPER_IDS:
            return f'{orth_open}<b>{bold_text}</b>{underline_text}{trailing}'
        else:
            return f'{orth_open}<u>{bold_text}{underline_text}</u>{trailing}'

    return re.sub(
        r'(<orth[^>]*>)<b>([^<]+)</b><u>([^<]+)</u>([^<]*)',
        normalize_match,
        content
    )


def classify_orth(orth_inner_html):
    """Classify an orth tag's content by its markup level.

    Returns: 'major', 'proper', 'derived', or 'plain'.
    """
    bare = orth_inner_html.strip().lstrip('(')

    if bare.startswith('<b>'):
        close_b = bare.find('</b>')
        if close_b < 0:
            return 'major'
        after_b = bare[close_b + 4:]
        after_text = re.sub(r'<[^>]*>', '', after_b)
        after_letters = sum(1 for c in after_text if c.isalpha())
        if after_letters >= 2:
            return 'proper'
        return 'major'
    elif bare.startswith('<u>'):
        return 'derived'
    return 'plain'


def determine_entry_type(content, has_ref):
    """Determine entry type from the maximum orth markup level."""
    if has_ref:
        return 'reference'

    max_level = 0
    for orth_m in re.finditer(r'<orth[^>]*>(.*?)</orth>', content):
        level = MARKUP_LEVELS.get(classify_orth(orth_m.group(1)), 0)
        max_level = max(max_level, level)

    return LEVEL_TO_TYPE.get(max_level, 'plain')


def fix_tag_nesting(content):
    """Fix inline tags (span, b, i, u) that cross structural boundaries (ol, li).

    Closes open inline tags before structural tags and reopens them inside
    text-containing structural elements, producing valid XML nesting.
    """
    INLINE_TAGS = {'span', 'b', 'i', 'u'}

    # Tokenize into tags and text segments
    tokens = []
    pos = 0
    for m in re.finditer(r'<[^>]+>', content):
        if m.start() > pos:
            tokens.append(('text', content[pos:m.start()]))
        tokens.append(('tag', m.group()))
        pos = m.end()
    if pos < len(content):
        tokens.append(('text', content[pos:]))

    TAG_NAME_RE = re.compile(r'^</?(\w+)')

    inline_stack = []   # logical: (tag_name, full_opening_tag)
    emitted = []        # currently open in output: (tag_name, full_opening_tag)
    output = []

    for tok_type, tok_val in tokens:
        if tok_type == 'text':
            output.append(tok_val)
            continue

        tag_match = TAG_NAME_RE.match(tok_val)
        if not tag_match:
            output.append(tok_val)  # self-closing or comment
            continue

        tag_name = tag_match.group(1)
        is_close = tok_val.startswith('</')

        if tag_name in ('ol', 'li'):
            # Close all currently emitted inlines
            for name, _ in reversed(emitted):
                output.append(f'</{name}>')
            emitted.clear()

            output.append(tok_val)

            # Reopen inlines after <li> (can contain text) or </ol> (back in parent)
            if (not is_close and tag_name == 'li') or (is_close and tag_name == 'ol'):
                for item in inline_stack:
                    output.append(item[1])
                    emitted.append(item)

        elif tag_name in INLINE_TAGS:
            if is_close:
                # Remove from logical stack
                for j in range(len(inline_stack) - 1, -1, -1):
                    if inline_stack[j][0] == tag_name:
                        inline_stack.pop(j)
                        break
                # Remove from emitted and output close tag
                for j in range(len(emitted) - 1, -1, -1):
                    if emitted[j][0] == tag_name:
                        emitted.pop(j)
                        output.append(tok_val)
                        break
                # If not in emitted, tag was already closed at structural boundary
            else:
                inline_stack.append((tag_name, tok_val))
                emitted.append((tag_name, tok_val))
                output.append(tok_val)
        else:
            output.append(tok_val)

    return ''.join(output)


def convert_to_xml(html):
    """Convert postprocessed HTML with <p> tags to XML with <entry> elements.

    Entry types (from orth markup, max level across all orths):
    - major:     fully bold headword — root/core vocabulary
    - proper:    first-letter-bold headword — proper nouns
    - derived:   underlined headword — etymological derivatives
    - reference: cross-reference entry (from data-ref)

    Homograph numbering:
    - Reference entries get no id attribute.
    - Non-reference entries with explicit homograph numbers (Roman/Arabic prefix
      before <orth>) get that number as their #N suffix.
    - Remaining non-reference duplicates fill in the lowest available numbers
      in dictionary order.
    - Singleton entries (one non-ref, no explicit number) get a bare id.

    Derived entries get a root attribute pointing to the most recent major entry.
    """

    # --- Pass 1: collect all entries ---
    entries = []
    for m in re.finditer(r'<p([^>]*)>(.*?)</p>', html, flags=re.DOTALL):
        p_attrs = m.group(1)
        content = m.group(2)

        has_ref = 'data-ref' in p_attrs

        has_review = content.startswith('!!!')
        if has_review:
            content = content[3:]

        content = fix_tag_nesting(content)
        content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)

        # Normalize mixed <b>+<u> markup in orth tags
        content = normalize_mixed_markup(content)

        # Extract explicit homograph number from prefix before <orth>
        explicit_num = None
        orth_pos = content.find('<orth')
        prefix = content[:orth_pos] if orth_pos >= 0 else ''
        num_match = re.match(r'^([IVX]+|\d+)\.\s*', prefix)
        if num_match:
            num_str = num_match.group(1)
            if num_str.isdigit():
                explicit_num = int(num_str)
            else:
                explicit_num = roman_to_int(num_str)

        orth_m = re.search(r'<orth[^>]*>(.*?)</orth>', content)
        headword_html = orth_m.group(1) if orth_m else ''
        base_id = make_entry_id(headword_html) or 'unknown'

        entry_type = determine_entry_type(content, has_ref)

        entries.append({
            'start': m.start(),
            'end': m.end(),
            'content': content,
            'has_ref': has_ref,
            'has_review': has_review,
            'base_id': base_id,
            'explicit_num': explicit_num,
            'entry_id': None,
            'type': entry_type,
            'root': None,
        })

    # --- Group non-ref entries by base_id ---
    groups = defaultdict(list)
    for entry in entries:
        if not entry['has_ref']:
            groups[entry['base_id']].append(entry)

    # --- Assign IDs ---
    for base_id, group_entries in groups.items():
        if len(group_entries) == 1 and group_entries[0]['explicit_num'] is None:
            # Single entry, no explicit number -> bare id
            group_entries[0]['entry_id'] = base_id
        else:
            # Step 1: assign explicit numbers
            taken = set()
            for entry in group_entries:
                if entry['explicit_num'] is not None:
                    num = entry['explicit_num']
                    if num in taken:
                        # Collision: bump to next available
                        orig = num
                        while num in taken:
                            num += 1
                        print(f"  WARNING: duplicate explicit homograph {orig} "
                              f"for '{base_id}', reassigned to {num}")
                    entry['entry_id'] = f'{base_id}#{num}'
                    taken.add(num)

            # Step 2: fill in remaining with lowest available numbers
            next_num = 1
            for entry in group_entries:
                if entry['entry_id'] is None:
                    while next_num in taken:
                        next_num += 1
                    entry['entry_id'] = f'{base_id}#{next_num}'
                    taken.add(next_num)
                    next_num += 1

    # --- Check for cross-group id collisions ---
    seen_ids = set()
    for entry in entries:
        if entry['entry_id'] is not None:
            if entry['entry_id'] in seen_ids:
                orig = entry['entry_id']
                suffix = 2
                while f"{orig}_{suffix}" in seen_ids:
                    suffix += 1
                entry['entry_id'] = f"{orig}_{suffix}"
                print(f"  WARNING: cross-group id collision for '{orig}', "
                      f"reassigned to '{entry['entry_id']}'")
            seen_ids.add(entry['entry_id'])

    # --- Assign root for derived/plain entries ---
    last_root_id = None
    for entry in entries:
        if entry['type'] in ('major', 'proper'):
            last_root_id = entry['entry_id']
        elif entry['type'] in ('derived', 'plain') and last_root_id is not None:
            entry['root'] = last_root_id

    # --- Pass 2: build output ---
    type_counts = defaultdict(int)
    result_parts = []
    last_end = 0
    entry_count = 0

    for entry in entries:
        result_parts.append(html[last_end:entry['start']])

        attrs = ''
        if entry['entry_id'] is not None:
            attrs += f' id="{entry["entry_id"]}"'
        attrs += f' type="{entry["type"]}"'
        if entry['root'] is not None:
            attrs += f' root="{entry["root"]}"'
        if entry['has_review']:
            attrs += ' data-review=""'

        result_parts.append(f'<entry{attrs}>{entry["content"]}</entry>')
        entry_count += 1
        type_counts[entry['type']] += 1
        last_end = entry['end']

    result_parts.append(html[last_end:])

    print(f"  Entry types: {dict(type_counts)}")

    return ''.join(result_parts), entry_count


html = convert_fodt_files()
html = postprocess(html)

xml_body, entry_count = convert_to_xml(html)

with open('cavallinlatin.xml', 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n')
    f.write('<dictionary>\n')
    f.write(xml_body.strip())
    f.write('\n</dictionary>\n')

print(f"  Wrote {entry_count} entries to cavallinlatin.xml")
