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
    remove punctuation, lowercase."""
    text = re.sub(r'<[^>]*>', '', headword_html)
    text = text.replace('æ', 'ae').replace('œ', 'oe').replace('Æ', 'Ae').replace('Œ', 'Oe')
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.category(c).startswith('Mn'))
    text = re.sub(r'[^\w]', '', text)
    return text.lower()


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
    """Fix inline tags (span, b, i, u) that cross <sense> boundaries.

    Closes open inline tags before <sense>/</sense> and reopens them inside,
    producing valid XML nesting.
    """
    INLINE_TAGS = {'span', 'foreign', 'form', 'b', 'i', 'u'}

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

        if tag_name == 'sense':
            for name, _ in reversed(emitted):
                output.append(f'</{name}>')
            emitted.clear()

            output.append(tok_val)

            # Both <sense ...> and </sense> return to a text context
            for item in inline_stack:
                output.append(item[1])
                emitted.append(item)

        elif tag_name in INLINE_TAGS:
            if is_close:
                for j in range(len(inline_stack) - 1, -1, -1):
                    if inline_stack[j][0] == tag_name:
                        inline_stack.pop(j)
                        break
                for j in range(len(emitted) - 1, -1, -1):
                    if emitted[j][0] == tag_name:
                        emitted.pop(j)
                        output.append(tok_val)
                        break
            else:
                inline_stack.append((tag_name, tok_val))
                emitted.append((tag_name, tok_val))
                output.append(tok_val)
        else:
            output.append(tok_val)

    return ''.join(output)


def flip_spans_to_foreign(content):
    """Invert <span> (fraktur/Swedish) markup to <foreign> (antiqua/Latin) markup.

    Removes <span> tags (Swedish becomes the unmarked default) and wraps
    previously-untagged text in <foreign>. Skips <orth> content (implicitly
    foreign). Flushes foreign regions at <sense> boundaries.
    """
    TAG_RE = re.compile(r'<[^>]+>')

    tokens = []
    pos = 0
    for m in TAG_RE.finditer(content):
        if m.start() > pos:
            tokens.append(('text', content[pos:m.start()]))
        tokens.append(('tag', m.group()))
        pos = m.end()
    if pos < len(content):
        tokens.append(('text', content[pos:]))

    in_span = False
    in_orth = False
    foreign_buf = []
    output = []

    def flush_foreign():
        if not foreign_buf:
            return
        combined = ''.join(foreign_buf)
        foreign_buf.clear()
        if any(c.isalpha() for c in re.sub(r'<[^>]*>', '', combined)):
            output.append(f'<foreign>{combined}</foreign>')
        else:
            output.append(combined)

    for tok_type, tok_val in tokens:
        if tok_type == 'text':
            if in_span:
                flush_foreign()
                output.append(tok_val)
            elif in_orth:
                output.append(tok_val)
            else:
                foreign_buf.append(tok_val)
            continue

        tag_name_m = re.match(r'^</?(\w+)', tok_val)
        if not tag_name_m:
            if in_span or in_orth:
                output.append(tok_val)
            else:
                foreign_buf.append(tok_val)
            continue

        tag_name = tag_name_m.group(1)
        is_close = tok_val.startswith('</')

        if tag_name == 'span':
            if is_close:
                in_span = False
            else:
                flush_foreign()
                in_span = True
        elif tag_name == 'orth':
            if is_close:
                in_orth = False
                output.append(tok_val)
            else:
                flush_foreign()
                in_orth = True
                output.append(tok_val)
        elif tag_name == 'sense':
            flush_foreign()
            output.append(tok_val)
        elif in_span or in_orth:
            output.append(tok_val)
        else:
            foreign_buf.append(tok_val)

    flush_foreign()
    return ''.join(output)


def _is_foreign_letter(c):
    return c.isalpha() and c != 'ɔ'


def _has_foreign_letters(text):
    return any(_is_foreign_letter(c) for c in re.sub(r'<[^>]*>', '', text))


def _next_text_is_letter(s, pos):
    """Check if the next non-tag character at or after pos is a foreign letter."""
    i = pos
    while i < len(s):
        if s[i] == '<':
            close = s.find('>', i)
            if close == -1:
                return False
            i = close + 1
        else:
            return _is_foreign_letter(s[i])
    return False


def _prev_text_is_letter(s, pos):
    """Check if the previous non-tag character at or before pos is a foreign letter."""
    i = pos
    while i >= 0:
        if s[i] == '>':
            open_pos = s.rfind('<', 0, i)
            if open_pos == -1:
                return False
            i = open_pos - 1
        else:
            return _is_foreign_letter(s[i])
    return False


def _prev_text_is_letter_or_digit(s, pos):
    """Check if the previous non-tag character at or before pos is a letter or digit."""
    i = pos
    while i >= 0:
        if s[i] == '>':
            open_pos = s.rfind('<', 0, i)
            if open_pos == -1:
                return False
            i = open_pos - 1
        else:
            return _is_foreign_letter(s[i]) or s[i].isdigit()
    return False


def _has_matching_close_paren(s, pos):
    """Check if '(' at pos has a matching ')' scanning forward."""
    depth = 0
    in_tag = False
    for i in range(pos, len(s)):
        if s[i] == '<':
            in_tag = True
        elif s[i] == '>':
            in_tag = False
        elif not in_tag:
            if s[i] == '(':
                depth += 1
            elif s[i] == ')':
                depth -= 1
                if depth == 0:
                    return True
    return False


def _has_matching_open_paren(s, pos, min_pos):
    """Check if ')' at pos has a matching '(' scanning backward to min_pos."""
    depth = 0
    in_tag = False
    for i in range(pos, min_pos - 1, -1):
        if s[i] == '>':
            in_tag = True
        elif s[i] == '<':
            in_tag = False
        elif not in_tag:
            if s[i] == ')':
                depth += 1
            elif s[i] == '(':
                depth -= 1
                if depth == 0:
                    return True
    return False


def _trim_foreign_edges(content):
    """Trim non-letter, non-tag characters from edges of each <foreign> tag.

    Preserves word-bound punctuation at edges:
    - '.' preceded by a letter or digit (abbreviation period, reference number)
    - '-' adjacent to a letter (morphological marker)
    - '(' with a matching ')' inside the tag (balanced parenthetical)
    - ')' with a matching '(' inside the tag
    """
    def process(m):
        inner = m.group(1)
        left = 0
        while left < len(inner):
            c = inner[left]
            if c == '<' or _is_foreign_letter(c):
                break
            if c == '-' and _next_text_is_letter(inner, left + 1):
                break
            if c == '(' and _has_matching_close_paren(inner, left):
                break
            left += 1
        right = len(inner)
        while right > left:
            c = inner[right - 1]
            if c == '>' or _is_foreign_letter(c) or c.isdigit():
                break
            if c == '-' and _prev_text_is_letter(inner, right - 2):
                break
            if c == '.' and right >= 2 and _prev_text_is_letter_or_digit(inner, right - 2):
                break
            if c == ')' and _has_matching_open_paren(inner, right - 1, left):
                break
            right -= 1
        before = inner[:left]
        middle = inner[left:right]
        after = inner[right:]
        if not middle:
            return before + after
        return f'{before}<foreign>{middle}</foreign>{after}'
    return re.sub(r'<foreign>(.*?)</foreign>', process, content, flags=re.DOTALL)


def _remove_empty_foreign(content):
    """Remove <foreign> tags whose content has no meaningful letters."""
    def check(m):
        if _has_foreign_letters(m.group(1)):
            return m.group(0)
        return m.group(1)
    return re.sub(r'<foreign>(.*?)</foreign>', check, content, flags=re.DOTALL)


def _split_foreign_at_unbalanced_parens(content):
    """Split <foreign> tags at unmatched closing parentheses."""
    def process(m):
        inner = m.group(1)
        segments = []
        current_start = 0
        depth = 0
        in_tag = False
        for i, c in enumerate(inner):
            if c == '<':
                in_tag = True
            elif c == '>':
                in_tag = False
            elif not in_tag:
                if c == '(':
                    depth += 1
                elif c == ')' and depth == 0:
                    segments.append(('foreign', inner[current_start:i]))
                    j = i
                    while j < len(inner):
                        if inner[j] == '<' or _is_foreign_letter(inner[j]):
                            break
                        j += 1
                    segments.append(('outside', inner[i:j]))
                    current_start = j
                elif c == ')':
                    depth -= 1
        if not segments:
            return m.group(0)
        segments.append(('foreign', inner[current_start:]))
        parts = []
        for seg_type, seg_content in segments:
            if not seg_content:
                continue
            if seg_type == 'foreign' and _has_foreign_letters(seg_content):
                parts.append(f'<foreign>{seg_content}</foreign>')
            else:
                parts.append(seg_content)
        return ''.join(parts)
    return re.sub(r'<foreign>(.*?)</foreign>', process, content, flags=re.DOTALL)


def _split_foreign_at_unbalanced_open_parens(content):
    """Split <foreign> tags before unmatched opening parentheses."""
    def process(m):
        inner = m.group(1)
        in_tag = False
        paren_positions = []
        for i, c in enumerate(inner):
            if c == '<':
                in_tag = True
            elif c == '>':
                in_tag = False
            elif not in_tag and c in '()':
                paren_positions.append((i, c))
        unmatched_opens = []
        depth = 0
        for pos, ch in reversed(paren_positions):
            if ch == ')':
                depth += 1
            elif depth > 0:
                depth -= 1
            else:
                unmatched_opens.append(pos)
        if not unmatched_opens:
            return m.group(0)
        split_pos = min(unmatched_opens)
        before = inner[:split_pos]
        j = split_pos
        while j < len(inner):
            if inner[j] == '<' or _is_foreign_letter(inner[j]):
                break
            j += 1
        between = inner[split_pos:j]
        after = inner[j:]
        parts = []
        if _has_foreign_letters(before):
            parts.append(f'<foreign>{before}</foreign>')
        else:
            parts.append(before)
        parts.append(between)
        if _has_foreign_letters(after):
            parts.append(f'<foreign>{after}</foreign>')
        else:
            parts.append(after)
        return ''.join(parts)
    return re.sub(r'<foreign>(.*?)</foreign>', process, content, flags=re.DOTALL)


def _split_foreign_at_emdash(content):
    """Move em-dashes that act as separators outside the <foreign> wrapper.

    Splits at any em-dash preceded by whitespace and followed by a Latin
    letter, a <br/>, or end-of-span. This catches:
      - Reference separators: "Moveo. —Prompt"
      - Trailing em-dashes before sense-end breaks: "Varr. —<br/>"
      - Line-wrapped separators: "Navus.\n—<br/>\nIgne"
    It leaves untouched:
      - Metrical notation (⏑—⏑, ———⏑) where the em-dash sits between
        non-whitespace prosodic symbols.
      - Word-internal shortening (a—m) — no whitespace around the em-dash.
    """
    def process(m):
        inner = m.group(1)
        new_inner, n = re.subn(
            r'(?<=\s)(—(?:\s|<br\s*/?>)*)(?=[A-Za-z-]|$)',
            r'</foreign>\1<foreign>', inner)
        if n == 0:
            return m.group(0)
        return f'<foreign>{new_inner}</foreign>'
    return re.sub(r'<foreign>(.*?)</foreign>', process, content, flags=re.DOTALL)


def _pull_quote_into_foreign(content):
    """Keep Swedish quote pairs (”…”) on the same side of <foreign> boundaries.

    If an opening ” sits just before <foreign> and a matching ” exists inside,
    move the outer ” inside. Mirror for a closing ” sitting just after
    </foreign> when an unmatched ” is inside.
    """
    if '”' not in content:
        return content
    # Tempered inner (not plain .*?) so pull_closing doesn't skip past a
    # </foreign> not followed by ” and rewrap a later span's boundary.
    inner_re = r'((?:(?!</foreign>).)*)'

    def pull_opening(m):
        inner = m.group(1)
        if '”' in inner:
            return f'<foreign>”{inner}</foreign>'
        return m.group(0)
    content = re.sub(rf'”<foreign>{inner_re}</foreign>', pull_opening,
                     content, flags=re.DOTALL)

    def pull_closing(m):
        inner = m.group(1)
        if '”' in inner:
            return f'<foreign>{inner}”</foreign>'
        return m.group(0)
    content = re.sub(rf'<foreign>{inner_re}</foreign>”', pull_closing,
                     content, flags=re.DOTALL)
    return content


def normalize_foreign_boundaries(content):
    """Clean up <foreign> tag boundaries."""
    content = _trim_foreign_edges(content)
    content = _remove_empty_foreign(content)
    content = _split_foreign_at_unbalanced_parens(content)
    content = _split_foreign_at_unbalanced_open_parens(content)
    content = _split_foreign_at_emdash(content)
    content = _trim_foreign_edges(content)
    content = _remove_empty_foreign(content)
    content = re.sub(r'<foreign>(<cb[^/]*/>) ?', r'\1<foreign>', content)
    content = re.sub(r'-(<foreign>)', r'\1-', content)
    content = re.sub(r'(</foreign>)-', r'-\1', content)
    content = re.sub(r'</foreign>(\s*)<foreign>', r'\1', content)
    content = _remove_empty_foreign(content)
    content = _pull_quote_into_foreign(content)
    return content


# --- Grammatical label conversion ---

# Italic labels: <i>LABEL</i> inside <foreign> → <tei>LABEL</tei>
# Compound labels are checked first (whole content), then single-word.
COMPOUND_LABEL_TO_TEI = {
    # --- Composite POS (numerals, pronouns — treat as single POS unit) ---
    'A. Num. Ord.': 'pos', 'A. Num. Distrib.': 'pos',
    'A. Num. Distr.': 'pos', 'A. Num. Card.': 'pos',
    'Num. Card. Indecl.': 'pos', 'Num. Card.': 'pos',
    'Num. Adj.': 'pos', 'Num. Distr.': 'pos', 'Num. Ord.': 'pos',
    'A. Num.': 'pos',
    'Pron. indef.': 'pos', 'Pron. relat.': 'pos',
    'Pron. interrog.': 'pos', 'Pron. indefin.': 'pos',
    'Pron. personale': 'pos', 'Pron. demonstrativum': 'pos',
    'Pron. demonstr.': 'pos', 'Pron. determinativum': 'pos',
    'V. impers.': 'pos',
    'Conj. causalis': 'pos',

    # --- Composite POS: pronouns with full Latin qualifier (treat as one) ---
    'Pron. indefinitum': 'pos', 'Pron. possessivum': 'pos',
    'Pron. possess.': 'pos', 'Pron. possessivum reflexivum': 'pos',
    'Pron. reflexivum': 'pos', 'Pron. interrogativum': 'pos',
    'Pron. Person.': 'pos', 'Pron. possessivum.': 'pos',

    # --- Composite POS: verb class ---
    'V. anom.': 'pos', 'Verb. anom.': 'pos',

    # --- POS + gender (decomposed) ---
    'A. f.': [('pos', 'A.'), ('gen', 'f.')],
    'A., f.': [('pos', 'A.'), ('gen', 'f.')],
    'f. A.': [('gen', 'f.'), ('pos', 'A.')],
    'm. A.': [('gen', 'm.'), ('pos', 'A.')],
    'm., A.': [('gen', 'm.'), ('pos', 'A.')],
    'comm. A.': [('gen', 'comm.'), ('pos', 'A.')],
    'A. m.': [('pos', 'A.'), ('gen', 'm.')],
    'Adj. f.': [('pos', 'Adj.'), ('gen', 'f.')],
    'Adj. m.': [('pos', 'Adj.'), ('gen', 'm.')],
    'adj. f.': [('pos', 'adj.'), ('gen', 'f.')],
    'f. adj.': [('gen', 'f.'), ('pos', 'adj.')],
    'f. Adj.': [('gen', 'f.'), ('pos', 'Adj.')],
    'Subst. m.': [('pos', 'Subst.'), ('gen', 'm.')],
    'Subst., m.': [('pos', 'Subst.'), ('gen', 'm.')],
    'Subst. n.': [('pos', 'Subst.'), ('gen', 'n.')],
    'Subst. c.': [('pos', 'Subst.'), ('gen', 'c.')],
    'Subst. comm.': [('pos', 'Subst.'), ('gen', 'comm.')],
    'Subst. m. f.': [('pos', 'Subst.'), ('gen', 'm. f.')],
    'Pron. A.': [('pos', 'Pron.'), ('pos', 'A.')],
    'Pronomen A.': [('pos', 'Pronomen'), ('pos', 'A.')],

    # --- POS + number (decomposed) ---
    'Subst. pl.': [('pos', 'Subst.'), ('number', 'pl.')],
    'Subst., pl.': [('pos', 'Subst.'), ('number', 'pl.')],
    'm., pl.': [('gen', 'm.'), ('number', 'pl.')],
    'm. pl.': [('gen', 'm.'), ('number', 'pl.')],
    'f. pl.': [('gen', 'f.'), ('number', 'pl.')],
    'n. pl. A.': [('gen', 'n.'), ('number', 'pl.'), ('pos', 'A.')],
    'm. Dem.': [('gen', 'm.'), ('subc', 'Dem.')],
    'f. Dem.': [('gen', 'f.'), ('subc', 'Dem.')],
    'n. pr. m.': [('lbl', 'n. pr.'), ('gen', 'm.')],

    # --- POS + comparison/list label (decomposed) ---
    'A. Comp.': [('pos', 'A.'), ('lbl', 'Comp.')],
    'A., Comp.': [('pos', 'A.'), ('lbl', 'Comp.')],
    'A. Compar.': [('pos', 'A.'), ('lbl', 'Compar.')],
    'A. Superl.': [('pos', 'A.'), ('lbl', 'Superl.')],
    'A. Distribut.': [('pos', 'A.'), ('lbl', 'Distribut.')],
    'A., Superl.': [('pos', 'A.'), ('lbl', 'Superl.')],
    'Adv., Comp.': [('pos', 'Adv.'), ('lbl', 'Comp.')],
    'Adv. Comp.': [('pos', 'Adv.'), ('lbl', 'Comp.')],
    'Adv.: Comp.': [('pos', 'Adv.'), ('lbl', 'Comp.')],
    'Comp., Adv.': [('lbl', 'Comp.'), ('pos', 'Adv.')],
    'Comp., Sup.': [('lbl', 'Comp.'), ('lbl', 'Sup.')],
    'Superl., Adv.': [('lbl', 'Superl.'), ('pos', 'Adv.')],

    # --- POS + iType (decomposed) ---
    'A. p. tr. gr.': [('pos', 'A.'), ('iType', 'p. tr. gr.')],

    # --- POS + label (decomposed) ---
    'Adv. Num.': [('pos', 'Adv.'), ('pos', 'Num.')],
    'Adv. interr.': [('pos', 'Adv.'), ('lbl', 'interr.')],
    'Adv. adversativ': [('pos', 'Adv.'), ('lbl', 'adversativ')],
    'Adv. demonstrativum': [('pos', 'Adv.'), ('lbl', 'demonstrativum')],
    'Conj. concessiva': [('pos', 'Conj.'), ('lbl', 'concessiva')],
    'Conj. adversativa': [('pos', 'Conj.'), ('lbl', 'adversativa')],
    'Conj., Præp.': [('pos', 'Conj.'), ('pos', 'Præp.')],
    'Part. interrogativa': [('pos', 'Part.'), ('lbl', 'interrogativa')],
    'Pron. determ., A.': [('pos', 'Pron. determ.'), ('pos', 'A.')],
    'Pron. det., A.': [('pos', 'Pron. det.'), ('pos', 'A.')],
    'Pron. indef. A.': [('pos', 'Pron. indef.'), ('pos', 'A.')],

    # --- Label + POS (decomposed) ---
    'indefinit Adv.': [('lbl', 'indefinit'), ('pos', 'Adv.')],
    'indef. Adv.': [('lbl', 'indef.'), ('pos', 'Adv.')],
    'disjunctiv Conj.': [('lbl', 'disjunctiv'), ('pos', 'Conj.')],

    # --- Gender + number (decomposed) ---
    'n. pl.': [('gen', 'n.'), ('number', 'pl.')],
    'n. pl': [('gen', 'n.'), ('number', 'pl')],
    'n.: plur.': [('gen', 'n.'), ('number', 'plur.')],
    'pl. n.': [('number', 'pl.'), ('gen', 'n.')],
    'pl. m.': [('number', 'pl.'), ('gen', 'm.')],
    'pl. f.': [('number', 'pl.'), ('gen', 'f.')],
    'neutr. pl.': [('gen', 'neutr.'), ('number', 'pl.')],
    'f. sing.': [('gen', 'f.'), ('number', 'sing.')],
    'fem. sing.': [('gen', 'fem.'), ('number', 'sing.')],
    'sing. m.': [('number', 'sing.'), ('gen', 'm.')],
    'plur. m.': [('number', 'plur.'), ('gen', 'm.')],
    'plur. masc.': [('number', 'plur.'), ('gen', 'masc.')],
    'masc. plur.': [('gen', 'masc.'), ('number', 'plur.')],
    'A. pl.': [('pos', 'A.'), ('number', 'pl.')],

    # --- Case + number (decomposed) ---
    'abl. sing.': [('case', 'abl.'), ('number', 'sing.')],
    'abl. pl.': [('case', 'abl.'), ('number', 'pl.')],
    'abl. plur.': [('case', 'abl.'), ('number', 'plur.')],
    'acc. sing.': [('case', 'acc.'), ('number', 'sing.')],
    'acc. pl.': [('case', 'acc.'), ('number', 'pl.')],
    'Acc. pl.': [('case', 'Acc.'), ('number', 'pl.')],
    'acc. plur.': [('case', 'acc.'), ('number', 'plur.')],
    'acc. plur. neutr.': [('case', 'acc.'), ('number', 'plur.'), ('gen', 'neutr.')],
    'accus. sing.': [('case', 'accus.'), ('number', 'sing.')],
    'dat. pl.': [('case', 'dat.'), ('number', 'pl.')],
    'dat. plur.': [('case', 'dat.'), ('number', 'plur.')],
    'gen. pl.': [('case', 'gen.'), ('number', 'pl.')],
    'gen. plur.': [('case', 'gen.'), ('number', 'plur.')],
    'gen. sing.': [('case', 'gen.'), ('number', 'sing.')],
    'dat. sing.': [('case', 'dat.'), ('number', 'sing.')],
    'nom. plur.': [('case', 'nom.'), ('number', 'plur.')],
    'nom. plur. fem.': [('case', 'nom.'), ('number', 'plur.'), ('gen', 'fem.')],
    'nom. plur. masc.': [('case', 'nom.'), ('number', 'plur.'), ('gen', 'masc.')],
    'nom. masc.': [('case', 'nom.'), ('gen', 'masc.')],
    'acc. fem.': [('case', 'acc.'), ('gen', 'fem.')],
    'acc. m.': [('case', 'acc.'), ('gen', 'm.')],
    'nom. sing.': [('case', 'nom.'), ('number', 'sing.')],
    'nom. pl.': [('case', 'nom.'), ('number', 'pl.')],
    'plur. nom.': [('number', 'plur.'), ('case', 'nom.')],
    'loc. sing.': [('case', 'loc.'), ('number', 'sing.')],

    # --- Case + gender (decomposed) ---
    'abl. f.': [('case', 'abl.'), ('gen', 'f.')],
    'abl. fem.': [('case', 'abl.'), ('gen', 'fem.')],
    'abl. sing. fem.': [('case', 'abl.'), ('number', 'sing.'), ('gen', 'fem.')],
    'abl. neutr.': [('case', 'abl.'), ('gen', 'neutr.')],
    'abl. m.': [('case', 'abl.'), ('gen', 'm.')],
    'acc. neutr.': [('case', 'acc.'), ('gen', 'neutr.')],
    'acc. pl. neutr.': [('case', 'acc.'), ('number', 'pl.'), ('gen', 'neutr.')],
    'pl. neutr. nom.': [('number', 'pl.'), ('gen', 'neutr.'), ('case', 'nom.')],
    'Nom. neutr. gen.': [('case', 'Nom.'), ('gen', 'neutr.'), ('case', 'gen.')],
    'nomen neutr. gen.': [('pos', 'nomen'), ('gen', 'neutr.'), ('case', 'gen.')],
    'nom. sing. comm.': [('case', 'nom.'), ('number', 'sing.'), ('gen', 'comm.')],
    'nom. sing. f.': [('case', 'nom.'), ('number', 'sing.'), ('gen', 'f.')],
    'nom. sing. neutr.': [('case', 'nom.'), ('number', 'sing.'), ('gen', 'neutr.')],
    'nom. plur. n.': [('case', 'nom.'), ('number', 'plur.'), ('gen', 'n.')],
    'neutr. gen.': [('gen', 'neutr.'), ('case', 'gen.')],
    'neutr. nom.': [('gen', 'neutr.'), ('case', 'nom.')],
    'neutr. sing.': [('gen', 'neutr.'), ('number', 'sing.')],
    'sing. acc.': [('number', 'sing.'), ('case', 'acc.')],
    'sing. collectivt': [('number', 'sing.'), ('lbl', 'collectivt')],
    'dat., abl.': [('case', 'dat.'), ('case', 'abl.')],
    'dat., abl. pl.': [('case', 'dat.'), ('case', 'abl.'), ('number', 'pl.')],
    'plur. dat., abl.': [('number', 'plur.'), ('case', 'dat.'), ('case', 'abl.')],

    # --- Case + mood/label (decomposed) ---
    'acc. inf.': [('case', 'acc.'), ('mood', 'inf.')],
    'acc. modi': [('case', 'acc.'), ('lbl', 'modi')],
    'absol. acc.': [('lbl', 'absol.'), ('case', 'acc.')],
    'dat. pers.': [('case', 'dat.'), ('lbl', 'pers.')],
    'dat. finalis': [('case', 'dat.'), ('lbl', 'finalis')],
    'dat. commodi': [('case', 'dat.'), ('lbl', 'commodi')],
    'dativus finalis': [('case', 'dativus'), ('lbl', 'finalis')],
    'adj. neutr. gen.': [('pos', 'adj.'), ('gen', 'neutr.'), ('case', 'gen.')],
    'imper. pass.': [('mood', 'imper.'), ('subc', 'pass.')],
    'inf. act.': [('mood', 'inf.'), ('subc', 'act.')],
    'cas. obl. sing.': [('lbl', 'cas. obl.'), ('number', 'sing.')],

    # --- Gender + label combined ---
    'Nom. Def.': [('case', 'Nom.'), ('lbl', 'Def.')],
    'Nom. Num. indecl.': [('pos', 'Nom. Num.'), ('lbl', 'indecl.')],
    'Indecl. n.': [('lbl', 'Indecl.'), ('gen', 'n.')],
    'indecl. def. n.': [('lbl', 'indecl.'), ('lbl', 'def.'), ('gen', 'n.')],
    'Subst. def.': [('pos', 'Subst.'), ('lbl', 'def.')],
    'Subst. Def.': [('pos', 'Subst.'), ('lbl', 'Def.')],

    # --- Two genders (combined) ---
    'f., m.': 'gen', 'f. m.': 'gen',
    'm., f.': 'gen', 'm. f.': 'gen',
    'm., n.': 'gen', 'm. n.': 'gen',

    # --- Two cases (combined) ---
    'acc., abl.': 'case', 'gen., dat.': 'case',
    'abl., acc.': 'case', 'gen., abl.': 'case',

    # --- Participle + tense/voice (decomposed) ---
    'part. pf.': [('lbl', 'part.'), ('tns', 'pf.')],
    'part. præs.': [('lbl', 'part.'), ('tns', 'præs.')],
    'part. praes.': [('lbl', 'part.'), ('tns', 'praes.')],
    'part. perf.': [('lbl', 'part.'), ('tns', 'perf.')],
    'part. pr.': [('lbl', 'part.'), ('tns', 'pr.')],
    'part. præt.': [('lbl', 'part.'), ('tns', 'præt.')],
    'part. fut.': [('lbl', 'part.'), ('tns', 'fut.')],
    'part. pass.': [('lbl', 'part.'), ('subc', 'pass.')],
    'part. pf. dep.': [('lbl', 'part.'), ('tns', 'pf.'), ('subc', 'dep.')],
    'part. pf. pass.': [('lbl', 'part.'), ('tns', 'pf.'), ('subc', 'pass.')],
    'perf. part. pass.': [('tns', 'perf.'), ('lbl', 'part.'), ('subc', 'pass.')],
    'præs. part.': [('tns', 'præs.'), ('lbl', 'part.')],
    'pt. pf.': [('lbl', 'pt.'), ('tns', 'pf.')],
    'pt. pass.': [('lbl', 'pt.'), ('subc', 'pass.')],
    'pt. præs.': [('lbl', 'pt.'), ('tns', 'præs.')],
    'pf. pt.': [('tns', 'pf.'), ('lbl', 'pt.')],
    'pf. part.': [('tns', 'pf.'), ('lbl', 'part.')],
    'p. pf.': [('lbl', 'p.'), ('tns', 'pf.')],
    'p. p.': 'lbl',  # ambiguous "participium perfecti" as a single unit
    'p. præs.': [('lbl', 'p.'), ('tns', 'præs.')],
    'p. pr.': [('lbl', 'p.'), ('tns', 'pr.')],
    'pass. part.': [('subc', 'pass.'), ('lbl', 'part.')],
    'pass. refl.': [('subc', 'pass.'), ('subc', 'refl.')],
    'part. pt.': 'lbl',

    # --- Tense + mood/form (decomposed) ---
    'pf. inf.': [('tns', 'pf.'), ('mood', 'inf.')],
    'pf. indic.': [('tns', 'pf.'), ('mood', 'indic.')],
    'præs. conj.': [('tns', 'præs.'), ('mood', 'conj.')],
    'impf. conj.': [('tns', 'impf.'), ('mood', 'conj.')],
    'plusqpf. conj.': [('tns', 'plusqpf.'), ('mood', 'conj.')],
    'inf. præs.': [('mood', 'inf.'), ('tns', 'præs.')],
    'pr. conj.': [('tns', 'pr.'), ('mood', 'conj.')],
    'Conj. pr.': [('mood', 'Conj.'), ('tns', 'pr.')],
    'final conjunctivus': [('lbl', 'final'), ('mood', 'conjunctivus')],
    'inf. historicus': 'lbl',
    'fut. exact.': 'tns', 'fut. ex.': 'tns',
    'fut. ex. pass.': [('tns', 'fut. ex.'), ('subc', 'pass.')],
    'fut. ex. conj.': [('tns', 'fut. ex.'), ('mood', 'conj.')],

    # --- Verb subcategorization compounds (decomposed) ---
    'Dep. Frequ.': [('subc', 'Dep.'), ('subc', 'Frequ.')],
    'Dep. intr.': [('subc', 'Dep.'), ('subc', 'intr.')],
    'Frequ., intr.': [('subc', 'Frequ.'), ('subc', 'intr.')],
    'pers., trans.': [('lbl', 'pers.'), ('subc', 'trans.')],
    'depon. transit.': [('subc', 'depon.'), ('subc', 'transit.')],
    'intr., absol.': [('subc', 'intr.'), ('lbl', 'absol.')],

    # --- Label + gender (decomposed) ---
    'ind. n.': [('lbl', 'ind.'), ('gen', 'n.')],
    'def. n.': [('lbl', 'def.'), ('gen', 'n.')],
    'f.: Dem.': [('gen', 'f.'), ('subc', 'Dem.')],
    'm.: Dem.': [('gen', 'm.'), ('subc', 'Dem.')],
    'A.: Dem.': [('pos', 'A.'), ('subc', 'Dem.')],
    'A. Dem.': [('pos', 'A.'), ('subc', 'Dem.')],
    'A. indecl.': [('pos', 'A.'), ('lbl', 'indecl.')],
    'relat. indefinitum, Adj.': [('lbl', 'relat. indefinitum'), ('pos', 'Adj.')],

    # --- Idiomatic constructions (keep as single unit) ---
    'acc. c. inf.': 'lbl', 'acc. cum inf.': 'lbl',
    'acc. c. inf. fut.': 'lbl', 'acc. cum inf. futuri': 'lbl',
    'accus. c. inf.': 'lbl',
    'abl. absol.': 'lbl',
    'accus. mensuræ': 'lbl', 'abl. mensuræ': 'lbl',
    'gen. part.': 'lbl', 'gen. qual.': 'lbl', 'gen. pretii': 'lbl',
    'gen. obj.': 'lbl', 'gen. subj.': 'lbl',
    'genitivi qualitatis': 'lbl',
    'abl. mens.': 'lbl', 'n. app.': 'lbl',
    'accus. temporis': 'lbl',
    'dat. gerundivi': 'lbl',
    'acc. græc.': 'lbl',
    'abl. pretii': 'lbl',
    'acc. obj.': 'lbl', 'acc. gr.': 'lbl',
    'sing. collect.': 'lbl',
    'cas. obl.': 'lbl',
    'nom. propr.': 'lbl', 'n. propr.': 'lbl', 'nom. pr.': 'lbl',
    'pronomen indefinitum, interrogativum, relativum': 'pos',
    'præs., impf., fut.': 'tns',
    'relativum indefinitum': 'lbl',
    'indirect frågesats': 'lbl',
    'pl. tant.': 'lbl',
    'amplific.': 'lbl', 'abstr.': 'lbl', 'nominat.': 'case',
    'obj. acc.': 'lbl', 'obj.-acc.': 'lbl',
    'subjects-acc.': 'lbl', 'prædicats-accus.': 'lbl',
    'objects-acc.': 'lbl', 'accus. object': 'lbl',
    'objects-': 'lbl', 'object': 'lbl', 'måttsaccus.': 'lbl',
    'abl.?': 'case',

    # --- Verb type labels (keep as single unit) ---
    'verb. Def.': 'lbl', 'Verb. defect.': 'lbl', 'Verb. def.': 'lbl',
    'verb. defect.': 'lbl',
    'Verb. anomalum': 'lbl',
    'Positivus': 'lbl', 'indefin.': 'lbl',
}

# Single-word labels
LABEL_TO_TEI = {
    # POS
    'A.': 'pos', 'Adj.': 'pos', 'adj.': 'pos',
    'Adv.': 'pos', 'adv.': 'pos',
    'Subst.': 'pos', 'subst.': 'pos',
    'Præp.': 'pos', 'Præpos.': 'pos', 'præp.': 'pos', 'præpos.': 'pos',
    'Conj.': 'pos', 'Conjunction': 'pos', 'conjunction': 'pos',
    'Conjunctio': 'pos',
    'Interj.': 'pos', 'interjection': 'pos',
    'Pron.': 'pos', 'Pronom.': 'pos', 'pronom.': 'pos', 'pronomen': 'pos',
    'Adverbium': 'pos', 'Nomen': 'pos', 'nomen': 'pos',
    'A': 'pos',  # dropped period (18 occurrences)
    'S.': 'pos',  # Swedish "Substantiv" (noun) — see Colchus entry
    # Gender
    'm.': 'gen', 'f.': 'gen', 'n.': 'gen', 'c.': 'gen',
    'comm.': 'gen', 'masc.': 'gen', 'fem.': 'gen',
    # Verb subcategorization
    'Dep.': 'subc', 'dep.': 'subc',
    'Frequ.': 'subc', 'frequ.': 'subc', 'Frequ': 'subc',
    'Inch.': 'subc', 'Inchoat.': 'subc',
    'Intens.': 'subc', 'Desid.': 'subc',
    'Dem.': 'subc', 'dem.': 'subc', 'Demin.': 'subc',
    'trans.': 'subc', 'transit.': 'subc', 'tr.': 'subc',
    'trans': 'subc', 'transitivt': 'subc',
    'intrans.': 'subc', 'intr.': 'subc',
    'pass.': 'subc', 'Pass.': 'subc',
    'act.': 'subc', 'activ': 'subc', 'activum': 'subc',
    'refl.': 'subc', 'reflex.': 'subc', 'reflexivt': 'subc',
    'impers.': 'subc', 'Impers.': 'subc',
    'passivum': 'subc',
    # Case
    'abl.': 'case', 'Abl.': 'case',
    'dat.': 'case', 'Dat.': 'case', 'dativ': 'case',
    'acc.': 'case', 'Acc.': 'case', 'accus.': 'case', 'Accus.': 'case',
    'gen.': 'case', 'Gen.': 'case', 'genit.': 'case', 'genitivus': 'case',
    'nom.': 'case', 'Nom.': 'case', 'nomin.': 'case',
    'voc.': 'case', 'vocat.': 'case',
    'loc.': 'case', 'locativ': 'case',
    # Mood
    'conj.': 'mood', 'conjunctivus': 'mood',
    'ind.': 'mood', 'Ind.': 'mood', 'indic.': 'mood',
    'imper.': 'mood', 'Imp.': 'mood',
    'imperat.': 'mood', 'imperativus': 'mood',
    'inf.': 'mood', 'infin.': 'mood', 'infinit.': 'mood',
    'subj.': 'mood',
    'indicat.': 'mood', 'indicativus': 'mood',
    # Tense
    'pf.': 'tns', 'perf.': 'tns',
    'præs.': 'tns', 'praes.': 'tns', 'præsens': 'tns',
    'fut.': 'tns', 'futurum': 'tns',
    'impf.': 'tns', 'plusqpf.': 'tns', 'plusqf.': 'tns',
    'supin.': 'tns', 'sup.': 'tns',
    # Number
    'plur.': 'number', 'pl.': 'number', 'sing.': 'number',
    # Labels
    'Comp.': 'lbl', 'comp.': 'lbl', 'Compar.': 'lbl',
    'Comparat.': 'lbl', 'Comparativus': 'lbl',
    'comparativ': 'lbl', 'comparativa': 'lbl', 'comparativum': 'lbl',
    'Superl.': 'lbl', 'superl.': 'lbl', 'Sup.': 'lbl',
    'Superlativus': 'lbl', 'superlativer': 'lbl',
    'part.': 'lbl', 'Part.': 'lbl', 'pt.': 'lbl', 'partic.': 'lbl',
    'syn.': 'lbl', 'synon.': 'lbl',
    'absol.': 'lbl', 'absolut': 'lbl',
    'n. pr.': 'lbl', 'indecl.': 'lbl', 'Indecl.': 'lbl',
    'Distrib.': 'lbl', 'Distribut.': 'lbl',
    'relat.': 'lbl', 'relativ': 'lbl', 'relativum': 'lbl',
    'relativa': 'lbl', 'relativt': 'lbl', 'relativsats': 'lbl',
    'reflexiva': 'lbl', 'reflexivum': 'lbl',
    'possessivus': 'lbl', 'possessivum': 'lbl', 'possess.': 'lbl',
    'indefinitum': 'lbl', 'indefinit': 'lbl', 'indef.': 'lbl',
    'interrogativum': 'lbl', 'interrogativ': 'lbl', 'interrog.': 'lbl',
    'interr.': 'lbl', 'interrogativa': 'lbl',
    'demonstrativum': 'lbl',
    'temporal': 'lbl', 'consecutiv': 'lbl', 'concessiv': 'lbl',
    'concessiva': 'lbl', 'adversativ': 'lbl', 'adversativa': 'lbl',
    'disjunctiv': 'lbl', 'causal': 'lbl', 'causativt': 'lbl',
    'conclusiv': 'lbl', 'correlat': 'lbl', 'modal': 'lbl',
    'modale': 'lbl', 'modalis': 'lbl', 'local': 'lbl',
    'conjunctivisk': 'lbl', 'final': 'lbl', 'hypothetisk': 'lbl',
    'Posit.': 'lbl', 'posit.': 'lbl', 'pos.': 'lbl', 'poet.': 'lbl',
    'determinativum': 'lbl',
    'personelt': 'lbl', 'personl.': 'lbl', 'collect.': 'lbl',
    'demonstr.': 'lbl', 'deponential': 'lbl',
    'Deminutivum': 'subc',
    'Supinum': 'tns',
    'Participium': 'lbl',
    'Vocativus': 'case',
    'Depon': 'subc',
    'def.': 'lbl', 'Def.': 'lbl',
    'frågeord': 'lbl', 'frågepartikel': 'lbl',
    'neutr.': 'lbl',  # as label (not gender)
    'obj.': 'lbl', 'pers.': 'lbl', 'subject': 'lbl',
}

_TEI_ELEMENTS = frozenset([
    'pos', 'gen', 'subc', 'case', 'mood', 'tns', 'number',
    'iType', 'gram', 'lbl',
])
_TEI_TAG_RE = re.compile(
    r'<(' + '|'.join(_TEI_ELEMENTS) + r')\b[^>]*>.*?</\1>', re.DOTALL)


def _decompose_label(raw, parts):
    """Wrap raw text parts in TEI tags, preserving whitespace between them.

    `parts` is a list of (tag, content) tuples. Each part's content is found
    in `raw` in order, and the text between parts (separators like spaces,
    newlines, commas) is preserved verbatim.
    """
    result = []
    pos = 0
    for tag, content in parts:
        idx = raw.find(content, pos)
        if idx < 0:
            # Fallback: emit with single spaces if we can't find the content
            return ' '.join(f'<{t}>{c}</{t}>' for t, c in parts)
        if idx > pos:
            result.append(raw[pos:idx])
        result.append(f'<{tag}>{content}</{tag}>')
        pos = idx + len(content)
    if pos < len(raw):
        result.append(raw[pos:])
    return ''.join(result)


def _wrap_label(raw, tei, trailing, after):
    """Wrap `raw` in the appropriate TEI tag(s) and append trailing/after."""
    content = raw.rstrip()
    if trailing:
        content = content[:-len(trailing)]
    if isinstance(tei, list):
        return _decompose_label(content, tei) + trailing + after
    return f'<{tei}>{content}</{tei}>{trailing}{after}'


def _convert_italic_label(m):
    """Convert a single <i>CONTENT</i> to a TEI element if it's a grammar label."""
    raw = m.group(1)
    after = m.group(2)  # character after </i>, if any

    # Build lookup key: collapse newlines to spaces for matching
    key = raw.replace('\n', ' ')
    key = key.strip()

    # Separate trailing punctuation for lookup
    trailing = ''
    while key and key[-1] in ':,;':
        trailing = key[-1] + trailing
        key = key[:-1]
    key = key.strip()

    # Try compound lookup first, then single-word
    tei = COMPOUND_LABEL_TO_TEI.get(key)
    if tei is None:
        tei = LABEL_TO_TEI.get(key)

    # Handle <i>A</i>. pattern: period outside italic
    if tei is None and after == '.' and not trailing:
        candidate = key + '.'
        tei = COMPOUND_LABEL_TO_TEI.get(candidate)
        if tei is None:
            tei = LABEL_TO_TEI.get(candidate)
        if tei:
            # Absorb the period into the element
            return _wrap_label(raw.rstrip() + '.', tei, trailing, '')

    if tei is None:
        return m.group(0)  # leave unchanged

    return _wrap_label(raw, tei, trailing, after)


_TAG_RE = re.compile(r'<[^>]+>')
_TAG_NAME_RE = re.compile(r'^</?(\w+)')
_SKIP_TAGS = _TEI_ELEMENTS | {'i'}


def _convert_upright_labels(inner):
    """Convert bare (upright) grammar labels in text segments of a foreign span.

    Only processes text that is NOT inside an already-converted TEI element.
    """
    tokens = []
    pos = 0
    for m in _TAG_RE.finditer(inner):
        if m.start() > pos:
            tokens.append(('text', inner[pos:m.start()]))
        tokens.append(('tag', m.group()))
        pos = m.end()
    if pos < len(inner):
        tokens.append(('text', inner[pos:]))

    result = []
    changed = False
    skip_depth = 0  # track nesting inside TEI elements and <i> tags
    for tok_type, tok_val in tokens:
        if tok_type == 'tag':
            tag_m = _TAG_NAME_RE.match(tok_val)
            if tag_m and tag_m.group(1) in _SKIP_TAGS:
                if tok_val.startswith('</'):
                    skip_depth -= 1
                else:
                    skip_depth += 1
            result.append(tok_val)
            continue

        # Skip text inside TEI elements and <i> tags
        if skip_depth > 0:
            result.append(tok_val)
            continue

        # Replace known upright patterns in text
        new_val = tok_val
        for pattern, repl_fmt in _UPRIGHT_PATTERNS:
            new_text = pattern.sub(repl_fmt, new_val)
            if new_text != new_val:
                changed = True
                new_val = new_text
        result.append(new_val)

    return ''.join(result), changed


# Upright patterns: (compiled regex, tei tag name, replacement format)
_UPRIGHT_PATTERNS = [
    # Multi-word patterns first (longer matches first)
    (re.compile(r'\bp\. tr\. gr\.'), r'<iType>p. tr. gr.</iType>'),
    (re.compile(r'\bs\. p\. et s\.'), r'<iType>s. p. et s.</iType>'),
    (re.compile(r'\bv\. gr\.'), r'<gram type="etym">v. gr.</gram>'),
    # Bare single-word labels (typesetter errors — should be italic).
    # Lookbehind excludes word chars and hyphens to avoid matching inside
    # compound words like "Semi-Dep."
    (re.compile(r'(?<![<\w-])Dep\.(?!\w)'), r'<subc>Dep.</subc>'),
    (re.compile(r'(?<![<\w-])Frequ\.(?!\w)'), r'<subc>Frequ.</subc>'),
    (re.compile(r'(?<![<\w-])frequ\.(?!\w)'), r'<subc>frequ.</subc>'),
    (re.compile(r'(?<![<\w-])Inchoat\.(?!\w)'), r'<subc>Inchoat.</subc>'),
    (re.compile(r'(?<![<\w-])Inch\.(?!\w)'), r'<subc>Inch.</subc>'),
    (re.compile(r'(?<![<\w-])part\.(?!\w)'), r'<lbl>part.</lbl>'),
]


_CONJ_NUMBER_RE = re.compile(
    r'(?<=[, ])( ?)([1-4])(\.?)(?=\s*$|\s*[:;,]?\s*<(?:'
    + '|'.join(_TEI_ELEMENTS) + r')\b)')


def _convert_conj_number(inner):
    """Convert conjugation numbers (1-4) in a foreign span.

    Matches at end of span, or before punctuation followed by a TEI element.
    The period after the digit is optional (some entries have '2' not '2.').
    """
    m = _CONJ_NUMBER_RE.search(inner)
    if not m:
        return inner, False

    space = m.group(1)
    num = m.group(2)
    dot = m.group(3)
    return (inner[:m.start()] + space + f'<iType>{num}{dot}</iType>'
            + inner[m.end():], True)


def _split_foreign_wrapper(inner):
    """Split <foreign> wrapper: TEI elements go outside, Latin text stays inside."""
    # Find all TEI elements in the inner content
    parts = []
    last_end = 0
    for m in _TEI_TAG_RE.finditer(inner):
        before = inner[last_end:m.start()]
        if before:
            parts.append(('text', before))
        parts.append(('tei', m.group()))
        last_end = m.end()
    trailing = inner[last_end:]
    if trailing:
        parts.append(('text', trailing))

    # If no TEI elements found, return wrapped as-is
    if not any(ptype == 'tei' for ptype, _ in parts):
        return f'<foreign>{inner}</foreign>'

    # Rebuild: wrap text parts in <foreign> if they have foreign letters
    result = []
    for i, (ptype, pcontent) in enumerate(parts):
        if ptype == 'tei':
            result.append(pcontent)
        elif _has_foreign_letters(pcontent):
            # Trim trailing separator chars if followed by a TEI element
            if i + 1 < len(parts) and parts[i + 1][0] == 'tei':
                m = re.search(r'[,;:\s]+$', pcontent)
                if m:
                    result.append(f'<foreign>{pcontent[:m.start()]}</foreign>')
                    result.append(m.group())
                else:
                    result.append(f'<foreign>{pcontent}</foreign>')
            else:
                result.append(f'<foreign>{pcontent}</foreign>')
        else:
            result.append(pcontent)

    return ''.join(result)


def convert_homograph_number(content):
    """Convert <foreign>I.</foreign> at entry start to <hom>I.</hom>.

    Roman numeral (or digit) wrapped in <foreign> at the beginning of an
    entry content marks a homograph (e.g., "I. Mannus" vs. "II. Mannus").
    """
    return re.sub(
        r'^(\s*)<foreign>([IVX]+|\d+)\.</foreign>',
        r'\1<hom>\2.</hom>',
        content)


def convert_grammar_labels(content):
    """Convert grammatical labels inside <foreign> from <i> to TEI elements."""

    def _process_span(match):
        inner = match.group(1)
        original = match.group(0)

        # Step A: Convert italic labels
        # Match <i>...</i> possibly followed by a single char (for period absorption)
        new_inner = re.sub(r'<i>([^<]*)</i>(.?)',
                           _convert_italic_label, inner)
        made_changes = (new_inner != inner)
        inner = new_inner

        # Step B: Convert upright labels
        inner, upright_changed = _convert_upright_labels(inner)
        made_changes = made_changes or upright_changed

        # Step C: Convert conjugation numbers — only if italic or upright
        # labels already matched. Otherwise a citation like "Pn. ep. VI. 2."
        # would have its trailing "2." mistaken for a conjugation number.
        if made_changes:
            inner, _ = _convert_conj_number(inner)

        if not made_changes:
            return original

        # Step D: Split/remove <foreign> wrapper
        return _split_foreign_wrapper(inner)

    content = re.sub(r'<foreign>(.*?)</foreign>', _process_span,
                     content, flags=re.DOTALL)

    # Convert bare conjugation numbers after </orth>, e.g. "</orth>, 3.:" ->
    # "</orth>, <iType>3.</iType>:". Also handles parenthetical content with
    # inline tags (like <foreign>) between </orth> and the number.
    # Skip if the digit is inside a <foreign> tag (those are handled later
    # by convert_inflection_conj_numbers which also splits the wrapper).
    def _bare_conj(m):
        prefix = m.group(1)
        if prefix.count('<foreign') > prefix.count('</foreign'):
            return m.group(0)
        return f'{prefix}<iType>{m.group(2)}{m.group(3)}</iType>{m.group(4)}'

    content = re.sub(
        r'(</orth>(?:(?!<b>|<sense|</entry|<iType).)*?)([1-4])(\.?)(\s*:)',
        _bare_conj, content, flags=re.DOTALL)

    return content


def convert_inflection_conj_numbers(content):
    """Convert conjugation numbers inside <foreign> spans that directly
    follow </orth>, e.g. "</orth> <foreign>ui, 1.</foreign>:" ->
    "</orth> <foreign>ui</foreign>, <iType>1.</iType>:". Citation spans
    elsewhere (e.g. "Pn. ep. VI. 2.") are not touched because they don't
    follow </orth>. Must run AFTER normalize_foreign_boundaries so that
    trailing punctuation inside <foreign> has been trimmed out.
    """
    def _convert(m):
        prefix, inner, sep, num, dot, trailing = m.groups()
        if inner:
            return (f'{prefix}<foreign>{inner}</foreign>{sep}'
                    f'<iType>{num}{dot}</iType>{trailing}')
        return f'{prefix}{sep.lstrip()}<iType>{num}{dot}</iType>{trailing}'

    # Loop: each pass converts one trailing number per <foreign>, so
    # entries with multiple conjugation numbers (e.g. "bui, 2., 3.") need
    # repeated application to catch the earlier digits. The final group
    # captures optional trailing punctuation ("3.;" — see Transfundo) that
    # should be moved outside the new <iType>.
    pattern = r'(</orth>[, ]*)<foreign>([^<]*?)([,\s]+)([1-4])(\.?)([;,]?)</foreign>'
    prev = None
    while prev != content:
        prev = content
        content = re.sub(pattern, _convert, content)
    return content


# --- Inflection form conversion ---

def _normalize_for_lookup(s):
    """Strip diacritics and normalize j/v/æ/œ for Collatinus lookup."""
    s = remove_accents(s)
    return s.lower().replace('j', 'i').replace('v', 'u').replace('æ', 'ae').replace('œ', 'oe')


def _build_collatinus_cache(forms):
    """Batch-lemmatize forms via Collatinus, return {form: set_of_lemma_keys}."""
    import json
    import urllib.request

    cache = {}
    forms = sorted(set(forms))
    batch_size = 500
    for i in range(0, len(forms), batch_size):
        batch = forms[i:i + batch_size]
        text = ' '.join(batch)
        req = urllib.request.Request(
            'http://localhost:8080/api/lemmatize/text',
            data=json.dumps({'text': text, 'lang': 'en'}).encode(),
            headers={'Content-Type': 'application/json'},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            for r in data['results']:
                token = r['token'].lower()
                lemmas = {a['lemma']['key'] for a in r['analyses']}
                if lemmas:
                    cache[token] = lemmas
        except Exception as e:
            print(f"  WARNING: Collatinus batch {i // batch_size + 1} failed: {e}")
    return cache


def _norm_lemma_key(key):
    """Normalize a Collatinus lemma key for comparison (strip homonym number)."""
    return _normalize_for_lookup(key.rstrip('0123456789'))


def _validate_form(hw_norm, hw_lemmas, part_norm, cache):
    """Check if part shares a lemma with hw via reconstruction or direct lookup."""
    # Build normalized key set for the headword, including the headword itself
    # as a pseudo-lemma (handles cases where Collatinus resolves to a different
    # homonym or variant, e.g. Aonides→Aonides2, Africa→africum).
    hw_keys = {_norm_lemma_key(k) for k in hw_lemmas}
    hw_keys.add(hw_norm)

    def _check(lemmas):
        return bool(hw_keys & {_norm_lemma_key(k) for k in lemmas})

    # Direct lookup of the ending
    part_lemmas = cache.get(part_norm, set())
    if _check(part_lemmas):
        return True
    # Reconstructions: try stripping 1-5 chars from hw and appending ending
    for strip in range(1, min(6, len(hw_norm))):
        recon = hw_norm[:len(hw_norm) - strip] + part_norm
        recon_lemmas = cache.get(recon, set())
        if _check(recon_lemmas):
            return True
    return False


_INFLECTION_GRAM_TAGS = r'gen|pos|iType|subc|lbl|number'
_INFLECTION_RE = re.compile(
    r'(</orth>)([,\s:]*\)?[,\s:]*(?:<cb[^/]*/>[,\s]*)*)<foreign>([^<]+)</foreign>'
    r'([,\s]*<(?:' + _INFLECTION_GRAM_TAGS + r')'  # grammar tag
    r'|[,\s]*(?:och\s|l\.\s)'                         # Swedish connective
    r'|[,\s]*<(?:orth|form)'                           # next headword/form
    r'|\s*[:(])')                                       # colon or paren boundary
# Secondary: alternative forms connected by 'l.'/'och' after a <form>
_ALT_FORM_RE = re.compile(
    r'(</form>)([,\s]*(?:l\.|och)\s*)<foreign>([^<]+)</foreign>')
# Inflection endings always start lowercase (with or without diacritics)
# or with '-' (comparative forms like -ior). This filters out grammar labels
# and Latin words that aren't endings.
_INFLECTION_START_RE = re.compile(
    r'[a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿāăēĕīĭōŏūŭȳ\-]')
# Grammar labels/descriptions that look like inflections (lowercase) but aren't.
# These slip through the lowercase guard because they start with a lowercase letter
# or are abbreviations. Checked per comma-separated part.
# Map non-inflection content to the TEI element it should become instead.
# These are grammar labels/descriptions that appear inside <foreign> spans
# after </orth> but aren't inflectional forms.
_LABEL_INSTEAD_OF_FORM = {
    # Gender labels
    'c.': 'gen', 'c.:': 'gen', 'n.': 'gen', 'm.': 'gen',
    'f.': 'gen', 'comm.': 'gen',
    # Number labels
    'pl.': 'number',
    # POS labels
    'interj.': 'pos', 'pronom.:': 'pos', 'præp.': 'pos', 'pron.': 'pos',
    'interjection': 'pos',
    'verbum defectivum': 'pos', 'interjectio gr.': 'pos',
    'particula interrogandi': 'pos', 'adverb. temporale': 'pos',
    'nom. numerale indecl.': 'pos',
    'particula inseparabilis': 'pos', 'particula demonstrandi': 'pos',
    # Case labels
    'nom.': 'case', 'abl.': 'case',
    # Compound labels
    's. s.': 'lbl', 's.s.': 'lbl', 'act.': 'lbl', 'num. indecl.': 'lbl',
    'p. p.': 'lbl', 'pt. pf.': 'lbl', 'pron. poss.': 'lbl',
    'rom. n. pr.': 'lbl', 'def.': 'lbl', 'indcl.': 'lbl',
    's. p.': 'lbl', 'adv. interr.': 'lbl',
    # Inflection type
    's. p. et sup.': 'iType',
    # Etymology
    'v. etrusca': 'gram', 'v. gr.': 'gram',
}
# Content that should not become <form> but doesn't map to a TEI element either.
# Leaked connectives, non-inflection words, mixed content, derivational suffixes.
_NOT_INFLECTION = {
    # Leaked connectives
    'l.', 'l', 'och', 'ac',
    # Full Latin words (not endings)
    'flumen', 'ager', 'lacus', 'scalae',
    # Derivational suffixes (not inflections)
    '-tiuncula', '-tor', '-litas',
    # Citation/definition text and parsing artifacts
    'pro levi', 'senes appellabantur', 'a e',
    # Reference
    'fr. IV.',
}
_CONJ_WITH_COLON_RE = re.compile(r'^([1-4])\.:$')


def _prescan_inflection_forms(entries):
    """Collect all forms needed for Collatinus batch validation."""
    forms = set()
    for entry in entries:
        for m in _INFLECTION_RE.finditer(entry['content']):
            foreign = m.group(3)
            if '(' in foreign:
                continue
            # Find headword: search backwards for nearest <orth>
            orth_m = list(re.finditer(
                r'<orth[^>]*>(.*?)</orth>', entry['content'][:m.end()]))
            if not orth_m:
                continue
            hw = re.sub(r'<[^>]*>', '', orth_m[-1].group(1)).strip()
            hw_norm = _normalize_for_lookup(hw)
            forms.add(hw_norm)
            for part in (p.strip() for p in foreign.split(',') if p.strip()):
                part_norm = _normalize_for_lookup(part)
                forms.add(part_norm)
                for strip in range(1, min(6, len(hw_norm))):
                    forms.add(hw_norm[:len(hw_norm) - strip] + part_norm)
    return forms


def _split_paren_segments(text):
    """Split text into segments outside and inside parentheses.

    Returns list of (is_paren, content) tuples preserving original text.
    E.g. "(esculus), i" → [(True,"(esculus)"), (False,", i")]
    """
    segments = []
    depth = 0
    start = 0
    for i, c in enumerate(text):
        if c == '(':
            if depth == 0 and i > start:
                segments.append((False, text[start:i]))
            if depth == 0:
                paren_start = i
            depth += 1
        elif c == ')' and depth > 0:
            depth -= 1
            if depth == 0:
                segments.append((True, text[paren_start:i + 1]))
                start = i + 1
    if start < len(text):
        segments.append((False, text[start:]))
    return segments


def convert_inflection_forms(content, collatinus_cache, stats):
    """Convert <foreign> inflection spans after </orth> to <form> elements."""
    # Pre-find orth positions for headword lookup
    orth_ends = []
    for om in re.finditer(r'<orth[^>]*>(.*?)</orth>', content):
        hw = re.sub(r'<[^>]*>', '', om.group(1)).strip()
        orth_ends.append((om.end(), hw))

    def _classify(parts, hw_norm, hw_lemmas):
        if hw_lemmas is not None:
            valid = all(
                _validate_form(hw_norm, hw_lemmas,
                               _normalize_for_lookup(p), collatinus_cache)
                for p in parts)
            if valid:
                stats['validated'] += len(parts)
            else:
                stats['suspicious'] += len(parts)
                for p in parts:
                    stats['suspicious_items'].append(p)
        else:
            stats['unconfirmed'] += len(parts)

    _BARE_CONJ_RE = re.compile(r'^[1-4]\.?$')

    def _wrap_part(part):
        """Wrap a part in <form> or the appropriate TEI tag."""
        # Normalize internal newlines for label lookup
        part_key = re.sub(r'\s+', ' ', part)
        tei = _LABEL_INSTEAD_OF_FORM.get(part_key)
        if tei:
            content = part.rstrip(':')
            colon = ':' if part.endswith(':') else ''
            return f'<{tei}>{content}</{tei}>{colon}'
        cm = _CONJ_WITH_COLON_RE.match(part)
        if cm:
            return f'<iType>{cm.group(1)}.</iType>:'
        if _BARE_CONJ_RE.match(part):
            n = part.rstrip('.')
            return f'<iType>{n}.</iType>'
        if not _is_inflection(part):
            return part
        return f'<form>{part}</form>'

    _GRAM_PREFIX_RE = re.compile(
        r'^(?:pl|gen|voc|neutr|adv|nom|abl|dat|acc)\.\s')
    _LEAKED_SUFFIX_RE = re.compile(r'\s(?:l\.|och|\d\.)$')

    def _is_inflection(part):
        part_key = re.sub(r'\s+', ' ', part)
        if _LABEL_INSTEAD_OF_FORM.get(part_key) is not None:
            return False
        if _CONJ_WITH_COLON_RE.match(part) or _BARE_CONJ_RE.match(part):
            return False
        if not _INFLECTION_START_RE.match(part.lstrip()):
            return False
        if part in _NOT_INFLECTION:
            return False
        # Multi-word content with 3+ words is likely citation text
        if len(part.split()) >= 3:
            return False
        # Reject content with semicolons or colons (grammar notes, leaked text)
        if ';' in part or ':' in part:
            return False
        # Grammar label prefix (pl. -li, gen. Nostri, voc. -thū, etc.)
        if _GRAM_PREFIX_RE.match(part):
            return False
        # Leaked trailing connective or conj number (ŏnis l., ĭtus 2.)
        if _LEAKED_SUFFIX_RE.search(part):
            return False
        return True

    def _replace(m):
        foreign_content = m.group(3)

        # Find headword for this position
        target = m.start() + len('</orth>')
        hw_text = None
        for end_pos, hw in orth_ends:
            if end_pos == target:
                hw_text = hw
                break
        if not hw_text:
            return m.group(0)

        hw_norm = _normalize_for_lookup(hw_text)
        hw_lemmas = collatinus_cache.get(hw_norm)

        # No parentheses — simple case
        if '(' not in foreign_content:
            parts = [p.strip() for p in foreign_content.split(',')
                     if p.strip()]
            infl_parts = [p for p in parts if _is_inflection(p)]
            if not infl_parts:
                return m.group(0)
            _classify(infl_parts, hw_norm, hw_lemmas)
            formed = ', '.join(_wrap_part(p) for p in parts)
            return f'{m.group(1)}{m.group(2)}{formed}{m.group(4)}'

        # Parenthetical content — extract endings from non-paren segments
        segments = _split_paren_segments(foreign_content)
        non_paren_text = ''.join(s for is_p, s in segments if not is_p)
        endings = [p.strip() for p in non_paren_text.split(',') if p.strip()]
        infl_endings = [e for e in endings if _is_inflection(e)]

        if not infl_endings:
            stats['skipped'] += 1
            stats['skipped_items'].append(foreign_content)
            return m.group(0)

        _classify(infl_endings, hw_norm, hw_lemmas)

        # Rebuild: paren segments stay as <foreign>, endings become <form>
        result_parts = []
        for is_paren, seg in segments:
            if is_paren:
                result_parts.append(f'<foreign>{seg}</foreign>')
            else:
                # Split this text segment at commas into endings
                pieces = seg.split(',')
                rebuilt = []
                for piece in pieces:
                    stripped = piece.strip()
                    if stripped:
                        # Preserve whitespace around the ending
                        before = piece[:len(piece) - len(piece.lstrip())]
                        after = piece[len(piece.rstrip()):]
                        rebuilt.append(f'{before}{_wrap_part(stripped)}{after}')
                    else:
                        rebuilt.append(piece)
                result_parts.append(','.join(rebuilt))

        inner = ''.join(result_parts)
        return f'{m.group(1)}{m.group(2)}{inner}{m.group(4)}'

    content = _INFLECTION_RE.sub(_replace, content)

    # Convert alternative forms connected by 'l.'/'och' after a <form>
    def _replace_alt(m):
        foreign_content = m.group(3)
        if '(' in foreign_content:
            return m.group(0)
        parts = [p.strip() for p in foreign_content.split(',') if p.strip()]
        infl_parts = [p for p in parts if _is_inflection(p)]
        if not infl_parts:
            return m.group(0)
        stats['unconfirmed'] += len(infl_parts)
        formed = ', '.join(_wrap_part(p) for p in parts)
        return f'{m.group(1)}{m.group(2)}{formed}'

    content = _ALT_FORM_RE.sub(_replace_alt, content)
    return content


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
        content = flip_spans_to_foreign(content)
        content = fix_tag_nesting(content)
        content = normalize_foreign_boundaries(content)

        # Grammar label conversion is restricted to the headword area
        # (before the first <sense>). Inside senses, abbreviations like
        # "med abl.:" are usage/construction notes, not headword morphology,
        # and should keep their original <i>/<foreign> markup.
        sense_pos = content.find('<sense')
        if sense_pos >= 0:
            head = convert_grammar_labels(content[:sense_pos])
            content = head + content[sense_pos:]
        else:
            content = convert_grammar_labels(content)

        content = normalize_foreign_boundaries(content)
        content = convert_inflection_conj_numbers(content)
        # Wrap bare conjugation numbers after grammar tags (e.g. Dep. 1. → Dep. <iType>1.</iType>)
        content = re.sub(r'(</subc>) ([1-4])\.', r'\1 <iType>\2.</iType>', content)
        content = convert_homograph_number(content)
        content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)

        # Clean up <orth> boundaries: move punctuation and parentheses
        # outside the tag. Hyphens stay inside (morphological markers).
        # Move <cb/> from inside <orth> to just before it (the existing
        # entry-boundary normalization will then push it between entries).
        content = re.sub(
            r'(<orth[^>]*>(?:<[bu]>)?)(<cb[^/]*/>) ?',
            r'\2\1', content)
        # Trailing ,;: — may be bare or inside </b></u>
        content = re.sub(
            r'([,;:])((?:</[bu]>)*</orth>)', r'\2\1', content)
        # Leading (
        content = re.sub(
            r'(<orth[^>]*>(?:<[bu]>)?)\(', r'(\1', content)
        # Trailing )
        content = re.sub(
            r'\)((?:</[bu]>)*</orth>)', r'\1)', content)

        # Normalize mixed <b>+<u> markup in orth tags
        content = normalize_mixed_markup(content)

        # Extract explicit homograph number from prefix before <orth>
        explicit_num = None
        orth_pos = content.find('<orth')
        prefix = content[:orth_pos] if orth_pos >= 0 else ''
        num_match = re.match(
            r'^\s*(?:<hom>)?([IVX]+|\d+)\.(?:</hom>)?\s*', prefix)
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

    # --- Convert inflection forms to <form> elements ---
    forms_to_check = _prescan_inflection_forms(entries)
    print(f"  Checking {len(forms_to_check)} forms against Collatinus...")
    collatinus_cache = _build_collatinus_cache(forms_to_check)
    print(f"  Collatinus cache: {len(collatinus_cache)} forms lemmatized")
    infl_stats = {
        'validated': 0, 'unconfirmed': 0, 'suspicious': 0, 'skipped': 0,
        'suspicious_items': [], 'skipped_items': [],
    }
    for entry in entries:
        entry['content'] = convert_inflection_forms(
            entry['content'], collatinus_cache, infl_stats)
    print(f"  Inflection forms: validated={infl_stats['validated']}, "
          f"unconfirmed={infl_stats['unconfirmed']}, "
          f"suspicious={infl_stats['suspicious']}, "
          f"skipped={infl_stats['skipped']}")

    from collections import Counter
    for category in ('suspicious', 'skipped'):
        counts = Counter(infl_stats[f'{category}_items'])
        with open(f'inflection_{category}.txt', 'w', encoding='utf-8') as f:
            for item, cnt in counts.most_common():
                f.write(f'{cnt:4d}  {item}\n')
        print(f"  Wrote inflection_{category}.txt ({len(counts)} unique)")

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

        result_parts.append(f'<entry{attrs}>\n{entry["content"]}</entry>')
        entry_count += 1
        type_counts[entry['type']] += 1
        last_end = entry['end']

    result_parts.append(html[last_end:])

    print(f"  Entry types: {dict(type_counts)}")

    xml = ''.join(result_parts)

    # Pull boundary <cb/> tags into the following entry so every <cb/>
    # lives inside an <entry> (simpler DB shredding downstream).
    xml = re.sub(
        r'<cb\b([^/]*)/>\s*(</entry>\s*)?(<entry\b[^>]*>)',
        lambda m: f'{m.group(2) or ""}{m.group(3)}\n<cb{m.group(1)}/>',
        xml,
    )

    return xml, entry_count


html = convert_fodt_files()
html = postprocess(html)

xml_body, entry_count = convert_to_xml(html)

with open('cavallinlatin.xml', 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n')
    f.write('<dictionary>\n')
    f.write(xml_body.strip())
    f.write('\n</dictionary>\n')

print(f"  Wrote {entry_count} entries to cavallinlatin.xml")

# Validate final XML and check ID uniqueness
from xml.etree.ElementTree import parse as _parse_xml
_tree = _parse_xml('cavallinlatin.xml')
_ids = [e.get('id') for e in _tree.iter('entry') if e.get('id') is not None]
_dupes = [i for i in set(_ids) if _ids.count(i) > 1]
if _dupes:
    print(f"  ERROR: duplicate IDs: {_dupes}")
else:
    print(f"  XML well-formed; {len(_ids)} unique IDs")
