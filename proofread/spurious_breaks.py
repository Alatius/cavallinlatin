import bisect
import glob
import hashlib
import json
import os
import re
import unicodedata
from difflib import SequenceMatcher


def _load_rtml():
    """Load and concatenate rtml content from all .terese files."""
    rtml_parts = []
    for path in sorted(glob.glob("../*.terese")):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for m in re.finditer(r'<rtml>\n?(.*?)\n?</rtml>', text, re.DOTALL):
            rtml_parts.append(m.group(1))
    return "\n".join(rtml_parts)


def _strip_tags_with_positions(text):
    """Strip tags from text, returning (clean_text, mapping) where mapping[i]
    gives the position in the original text for clean_text[i]."""
    result = []
    mapping = []
    i = 0
    while i < len(text):
        if text[i] == '<':
            end = text.find('>', i)
            if end == -1:
                result.append(text[i])
                mapping.append(i)
                i += 1
            else:
                i = end + 1
        else:
            result.append(text[i])
            mapping.append(i)
            i += 1
    return ''.join(result), mapping


def _clean_rtml(rtml):
    """Clean rtml for alignment: strip tags, remove hyphens at line breaks,
    collapse whitespace. Returns (clean_text, mapping_to_original)."""
    text, mapping = _strip_tags_with_positions(rtml)

    result = []
    result_map = []
    i = 0
    while i < len(text):
        if text[i] == '-' and i + 1 < len(text) and text[i + 1] == '\n':
            # Remove hyphens at line breaks: "hy-\nphens" → "hyphens"
            i += 2
            while i < len(text) and text[i] == ' ':
                i += 1
        elif text[i] == '\n':
            result.append(' ')
            result_map.append(mapping[i])
            i += 1
        elif text[i] == ' ' and result and result[-1] == ' ':
            i += 1
        else:
            result.append(text[i])
            result_map.append(mapping[i])
            i += 1
    return ''.join(result), result_map


def _clean_html_text(html):
    """Clean HTML for alignment: strip tags, collapse whitespace.
    Returns (clean_text, mapping_to_original)."""
    text, mapping = _strip_tags_with_positions(html)

    result = []
    result_map = []
    for i, ch in enumerate(text):
        if ch in (' ', '\n', '\t'):
            if result and result[-1] != ' ':
                result.append(' ')
                result_map.append(mapping[i])
        else:
            result.append(ch)
            result_map.append(mapping[i])
    return ''.join(result), result_map


def _normalize_with_mapping(text):
    """Normalize text for alignment with position tracking.
    Returns (normalized_text, mapping) where mapping[i] gives the index
    in the input text for normalized_text[i]."""
    result = []
    mapping = []
    expansions = {'æ': 'ae', 'œ': 'oe', 'ß': 'ss'}
    for i, ch in enumerate(text):
        lower = ch.lower()
        if lower == 'ſ':
            lower = 's'
        if lower in expansions:
            for c in expansions[lower]:
                result.append(c)
                mapping.append(i)
            continue
        nfkd = unicodedata.normalize('NFKD', lower)
        for c in nfkd:
            if not unicodedata.category(c).startswith('Mn'):
                result.append(c)
                mapping.append(i)
    return ''.join(result), mapping


_CACHE_FILE = os.path.join(os.path.dirname(__file__), '.dash_break_cache.json')


def _compute_dash_break_positions(html):
    """Compute absolute HTML positions of <br/> tags that correspond to
    em-dashes in the rtml source. This is the expensive operation."""
    rtml = _load_rtml()

    # Split rtml into paragraphs and prepare each
    rtml_paras = []
    for para in re.split(r'\n\n+', rtml):
        if not para.strip():
            continue
        clean, _ = _clean_rtml(para)
        norm, norm_to_clean = _normalize_with_mapping(clean)
        hw_m = re.match(r'[a-z]+', norm)
        hw = hw_m.group(0) if hw_m else ''
        dashes = frozenset(i for i, ch in enumerate(clean) if ch == '—')
        rtml_paras.append((hw, norm, norm_to_clean, dashes))

    # Prepare HTML paragraphs
    para_matches = list(re.finditer(r'<p>(.*?)</p>', html, re.DOTALL))
    html_paras = []
    for pm in para_matches:
        content = pm.group(1)
        clean, clean_to_html = _clean_html_text(content)
        clean_to_html_abs = [pm.start(1) + p for p in clean_to_html]
        norm, norm_to_clean = _normalize_with_mapping(clean)
        hw_m = re.match(r'[a-z]+', norm)
        hw = hw_m.group(0) if hw_m else ''
        html_paras.append((hw, norm, norm_to_clean, clean_to_html_abs,
                           pm.start(1), pm.end(1)))

    # Align paragraphs greedily by headword
    aligned = []
    ri = 0
    for hi, (h_hw, _, _, _, _, _) in enumerate(html_paras):
        if not h_hw:
            continue
        for j in range(ri, min(ri + 20, len(rtml_paras))):
            if rtml_paras[j][0] == h_hw:
                aligned.append((hi, j))
                ri = j + 1
                break

    # For each aligned pair, find which breaks correspond to dashes
    dash_break_positions = set()

    for hi, rj in aligned:
        h_hw, h_norm, h_n2c, h_c2h, h_start, h_end = html_paras[hi]
        r_hw, r_norm, r_n2c, r_dashes = rtml_paras[rj]

        if not r_dashes:
            continue

        sm = SequenceMatcher(None, h_norm, r_norm, autojunk=False)
        h_to_r = {}
        for block in sm.get_matching_blocks():
            for k in range(block.size):
                h_to_r[block.a + k] = block.b + k

        para_html = html[h_start:h_end]
        for bm in re.finditer(r' *<br/>\n', para_html):
            break_end_abs = h_start + bm.end()

            ci = bisect.bisect_left(h_c2h, break_end_abs)
            if ci >= len(h_c2h):
                continue

            ni = bisect.bisect_left(h_n2c, ci)
            if ni >= len(h_norm):
                continue

            ri_pos = h_to_r.get(ni)
            if ri_pos is None:
                for delta in range(1, 4):
                    if (ni + delta) in h_to_r:
                        ri_pos = h_to_r[ni + delta]
                        break
                    if (ni - delta) in h_to_r:
                        ri_pos = h_to_r[ni - delta]
                        break
            if ri_pos is None:
                continue

            if ri_pos >= len(r_n2c):
                continue
            r_ci = r_n2c[ri_pos]

            if any((r_ci + offset) in r_dashes for offset in range(-2, 3)):
                dash_break_positions.add(h_start + bm.start())

    return dash_break_positions


def _get_dash_break_positions(html):
    """Get dash break positions, using a cache file to avoid recomputation."""
    html_hash = hashlib.sha256(html.encode()).hexdigest()

    # Try loading from cache
    try:
        with open(_CACHE_FILE) as f:
            cache = json.load(f)
        if cache.get('html_hash') == html_hash:
            return set(cache['positions'])
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass

    # Compute and save to cache
    positions = _compute_dash_break_positions(html)
    with open(_CACHE_FILE, 'w') as f:
        json.dump({'html_hash': html_hash, 'positions': sorted(positions)}, f)

    return positions


def remove_spurious_breaks(html):
    """Remove <br/> tags that don't correspond to em-dashes in the rtml source."""
    dash_break_positions = _get_dash_break_positions(html)

    SENSE_RE = re.compile(r'^(?:[0-9]+\.|[IVX]+\.|[a-z]\.|[A-Z]\.|[αβγδεζηθ]\.)')

    def replace_break(m):
        after = html[m.end():m.end() + 30]
        if SENSE_RE.match(after):
            return m.group(0)
        if after.startswith('<orth>'):
            return m.group(0)
        if m.start() in dash_break_positions:
            return ' —' +m.group(0)
        return ' '

    html = re.sub(r' *<br/>\n', replace_break, html)

    return html
