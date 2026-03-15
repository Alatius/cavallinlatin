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


def make_entry_id(headword_html):
    """Generate an entry ID from headword HTML: strip tags, remove diacritics,
    remove punctuation."""
    text = re.sub(r'<[^>]*>', '', headword_html)
    text = text.replace('æ', 'ae').replace('œ', 'oe').replace('Æ', 'Ae').replace('Œ', 'Oe')
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.category(c).startswith('Mn'))
    text = re.sub(r'[^\w]', '', text)
    return text


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

    Homograph numbering:
    - Reference entries (data-ref) get no id attribute.
    - Non-reference entries with explicit homograph numbers (Roman/Arabic prefix
      before <orth>) get that number as their .N suffix.
    - Remaining non-reference duplicates fill in the lowest available numbers
      in dictionary order.
    - Singleton entries (one non-ref, no explicit number) get a bare id.
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

        entries.append({
            'start': m.start(),
            'end': m.end(),
            'content': content,
            'has_ref': has_ref,
            'has_review': has_review,
            'base_id': base_id,
            'explicit_num': explicit_num,
            'entry_id': None,
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

    # --- Pass 2: build output ---
    result_parts = []
    last_end = 0
    entry_count = 0

    for entry in entries:
        result_parts.append(html[last_end:entry['start']])

        attrs = ''
        if entry['entry_id'] is not None:
            attrs += f' id="{entry["entry_id"]}"'
        if entry['has_ref']:
            attrs += ' data-ref=""'
        if entry['has_review']:
            attrs += ' data-review=""'

        result_parts.append(f'<entry{attrs}>{entry["content"]}</entry>')
        entry_count += 1
        last_end = entry['end']

    result_parts.append(html[last_end:])

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
