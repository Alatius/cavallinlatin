import glob
import hashlib
import os
import pickle
import re
from difflib import SequenceMatcher

_ALIGNMENT_CACHE = os.path.join(os.path.dirname(__file__), '.alignment_cache.pkl')


class AlignmentResult:
    __slots__ = ('html_to_rtml', 'rtml_dashes', 'html_plain_map',
                 'source_map', 'rtml_text')

    def __init__(self):
        self.html_to_rtml = []
        self.rtml_dashes = frozenset()
        self.html_plain_map = []
        self.source_map = []
        self.rtml_text = ''


def strip_tags_with_positions(text):
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


def clean_html_text(html):
    """Clean HTML for alignment: strip tags, collapse whitespace.
    Returns (clean_text, mapping_to_original)."""
    text, mapping = strip_tags_with_positions(html)

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


def load_rtml_unified():
    """Load rtml from all .terese files once.

    Returns (rtml_text, source_map) where:
    - rtml_text: tag-stripped plain text from all pages
    - source_map: per-character (tiff_filename, top_pixel) for rtml_text
    """
    rtml_text_parts = []
    source_maps = []

    for path in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "*.terese"))):
        with open(path, encoding="utf-8") as f:
            text = f.read()

        for page_m in re.finditer(
            r'<page\s+path="([^"]*)"[^>]*>\s*<rtml>\n?(.*?)\n?</rtml>\s*(.*?)\s*</page>',
            text, re.DOTALL
        ):
            tiff_path = page_m.group(1)
            tiff_filename = os.path.basename(tiff_path)
            rtml_content = page_m.group(2)
            box_section = page_m.group(3)

            # Build plain text and source map directly from boxes
            raw_chars = []
            raw_source = []
            for bm in re.finditer(r'<box\s+c="([^"]*)"[^>]*t="(\d+)"[^>]*/>', box_section):
                char = bm.group(1)
                if char == '\\n':
                    char = '\n'
                elif char == '&amp;':
                    char = '&'
                elif char == '&lt;':
                    char = '<'
                elif char == '&gt;':
                    char = '>'
                elif char == '&quot;':
                    char = '"'
                top = int(bm.group(2))
                # Expand multi-character boxes and convert ſ→s
                for ch in char:
                    if ch == 'ſ':
                        ch = 's'
                    raw_chars.append(ch)
                    raw_source.append((tiff_filename, top))

            # Process line breaks: dehyphenate, convert single \n to space,
            # collapse \n\n to single \n
            plain_chars = []
            page_source = []
            i = 0
            while i < len(raw_chars):
                if raw_chars[i] == '-' and i + 1 < len(raw_chars) and raw_chars[i + 1] == '\n':
                    # Remove hyphen + newline (dehyphenate)
                    i += 2
                elif raw_chars[i] == '\n' and i + 1 < len(raw_chars) and raw_chars[i + 1] == '\n':
                    # Paragraph break: collapse to single \n
                    plain_chars.append('\n')
                    page_source.append(raw_source[i])
                    i += 2
                elif raw_chars[i] == '\n':
                    # Single newline: replace with space
                    plain_chars.append(' ')
                    page_source.append(raw_source[i])
                    i += 1
                else:
                    plain_chars.append(raw_chars[i])
                    page_source.append(raw_source[i])
                    i += 1

            rtml_text_parts.append(''.join(plain_chars))
            source_maps.append(page_source)

    # Concatenate all pages
    combined_text = ''.join(rtml_text_parts)
    combined_source = []
    for smap in source_maps:
        combined_source.extend(smap)

    return combined_text, combined_source


def global_align(seq_a, seq_b, anchor_len=20, step=100):
    """Align two long, similar sequences using anchor-based chunking.

    Finds dense anchor points (exact matching substrings) between the two
    sequences, then uses SequenceMatcher on the gap regions between anchors.

    Returns a_to_b where a_to_b[i] = index in seq_b aligned to position i
    in seq_a (or -1 for gap).
    """
    n = len(seq_a)
    m = len(seq_b)

    if n == 0:
        return []
    if m == 0:
        return [-1] * n

    a_to_b = [-1] * n

    # Phase 1: Find anchors by scanning seq_a at regular intervals
    # and finding exact matches in seq_b near the expected position.
    anchors = []  # list of (a_pos, b_pos, length)
    search_radius = 200  # how far from expected position to search in seq_b

    ai = 0
    drift = 0  # accumulated offset between a and b positions
    while ai + anchor_len <= n:
        pattern = seq_a[ai:ai + anchor_len]
        expected_bi = ai + drift
        found = False

        bi = -1
        for offset in range(search_radius + 1):
            for sign in (0, 1, -1) if offset == 0 else (1, -1):
                candidate = expected_bi + sign * offset
                if candidate < 0 or candidate + anchor_len > m:
                    continue
                if seq_b[candidate:candidate + anchor_len] == pattern:
                    bi = candidate
                    break
            if bi >= 0:
                break

        if bi >= 0:
            # Extend the match as far as possible
            end_a = ai + anchor_len
            end_b = bi + anchor_len
            while end_a < n and end_b < m and seq_a[end_a] == seq_b[end_b]:
                end_a += 1
                end_b += 1
            # Extend backward
            start_a = ai
            start_b = bi
            while start_a > 0 and start_b > 0 and seq_a[start_a - 1] == seq_b[start_b - 1]:
                if anchors and start_a - 1 < anchors[-1][0] + anchors[-1][2]:
                    break
                start_a -= 1
                start_b -= 1

            length = end_a - start_a
            # Check non-overlap with previous anchor
            if anchors:
                prev_a, prev_b, prev_len = anchors[-1]
                if start_a < prev_a + prev_len or start_b < prev_b + prev_len:
                    trim = max(prev_a + prev_len - start_a,
                               prev_b + prev_len - start_b)
                    start_a += trim
                    start_b += trim
                    length -= trim

            if length >= anchor_len:
                anchors.append((start_a, start_b, length))
                drift = start_b - start_a
                ai = start_a + length
                found = True

        if not found:
            ai += step

    # Phase 2: Record anchor matches in a_to_b
    for a_start, b_start, length in anchors:
        for k in range(length):
            a_to_b[a_start + k] = b_start + k

    # Phase 3: Align gap regions between anchors using SequenceMatcher
    gaps = []  # (a_start, a_end, b_start, b_end)
    prev_a_end = 0
    prev_b_end = 0
    for a_start, b_start, length in anchors:
        if a_start > prev_a_end or b_start > prev_b_end:
            gaps.append((prev_a_end, a_start, prev_b_end, b_start))
        prev_a_end = a_start + length
        prev_b_end = b_start + length
    # Tail gap
    if prev_a_end < n or prev_b_end < m:
        gaps.append((prev_a_end, n, prev_b_end, m))

    for ga_start, ga_end, gb_start, gb_end in gaps:
        chunk_a = seq_a[ga_start:ga_end]
        chunk_b = seq_b[gb_start:gb_end]
        if not chunk_a or not chunk_b:
            continue
        sm = SequenceMatcher(None, chunk_a, chunk_b, autojunk=False)
        for block in sm.get_matching_blocks():
            for k in range(block.size):
                a_to_b[ga_start + block.a + k] = gb_start + block.b + k

    return a_to_b


def compute_full_alignment(html):
    """Compute global alignment between HTML and rtml source.

    Returns an AlignmentResult with html_to_rtml mapping, rtml_dashes,
    and norm maps/source_map for orth source attribution.
    Results are cached to disk as a pickle.
    """
    html_hash = hashlib.sha256(html.encode()).hexdigest()

    try:
        with open(_ALIGNMENT_CACHE, 'rb') as f:
            cache = pickle.load(f)
        if cache.get('html_hash') == html_hash:
            return cache['result']
    except (FileNotFoundError, pickle.UnpicklingError, KeyError, EOFError):
        pass

    rtml_text, source_map = load_rtml_unified()

    result = AlignmentResult()
    result.source_map = source_map
    result.rtml_text = rtml_text

    # Compute rtml dash positions directly in box text
    rtml_dashes = frozenset(i for i, ch in enumerate(rtml_text) if ch == '—')
    result.rtml_dashes = rtml_dashes

    # Clean HTML: strip tags, collapse whitespace
    html_plain, html_plain_map = clean_html_text(html)
    result.html_plain_map = html_plain_map

    # Global alignment directly between cleaned texts
    print(f"  Aligning {len(html_plain)} html chars with {len(rtml_text)} rtml chars...")
    html_to_rtml = global_align(html_plain, rtml_text)
    result.html_to_rtml = html_to_rtml

    with open(_ALIGNMENT_CACHE, 'wb') as f:
        pickle.dump({'html_hash': html_hash, 'result': result}, f, protocol=pickle.HIGHEST_PROTOCOL)

    return result
