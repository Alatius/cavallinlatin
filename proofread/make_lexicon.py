import re
import unicodedata

from fodt_to_html import convert_fodt_files
from postprocess import postprocess


def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join(c for c in nfkd_form if not unicodedata.category(c).startswith('Mn'))


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
    """Convert postprocessed HTML with <p> tags to XML with <entry> elements."""
    id_counts = {}
    entry_count = 0

    def process_entry(m):
        nonlocal entry_count
        p_attrs = m.group(1)
        content = m.group(2)

        has_ref = 'data-ref' in p_attrs

        has_review = content.startswith('!!!')
        if has_review:
            content = content[3:]

        content = fix_tag_nesting(content)
        content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)

        orth_m = re.search(r'<orth[^>]*>(.*?)</orth>', content)
        headword_html = orth_m.group(1) if orth_m else ''

        base_id = make_entry_id(headword_html) or 'unknown'

        if base_id not in id_counts:
            id_counts[base_id] = 1
            entry_id = base_id
        else:
            id_counts[base_id] += 1
            entry_id = f'{base_id}.{id_counts[base_id]}'

        attrs = f' id="{entry_id}"'
        if has_ref:
            attrs += ' data-ref=""'
        if has_review:
            attrs += ' data-review=""'

        entry_count += 1
        return f'<entry{attrs}>{content}</entry>'

    xml_body = re.sub(r'<p([^>]*)>(.*?)</p>', process_entry, html, flags=re.DOTALL)
    return xml_body, entry_count


html = convert_fodt_files()
html = postprocess(html)

xml_body, entry_count = convert_to_xml(html)

with open('cavallinlatin.xml', 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n')
    f.write('<dictionary>\n')
    f.write(xml_body.strip())
    f.write('\n</dictionary>\n')

print(f"  Wrote {entry_count} entries to cavallinlatin.xml")
