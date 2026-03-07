import bisect
import glob
import hashlib
import os
import pickle
import re
import unicodedata
from difflib import SequenceMatcher

_ALIGNMENT_CACHE = os.path.join(os.path.dirname(__file__), '.alignment_cache.pkl')


class AlignmentResult:
    __slots__ = ('para_alignments', 'matching_blocks', 'html_norm_to_html',
                 'rtml_norm_map', 'source_map')

    def __init__(self):
        self.para_alignments = []
        self.matching_blocks = []
        self.html_norm_to_html = []
        self.rtml_norm_map = []
        self.source_map = []


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


def clean_rtml(rtml):
    """Clean rtml for alignment: strip tags, remove hyphens at line breaks,
    collapse whitespace. Returns (clean_text, mapping_to_original)."""
    text, mapping = strip_tags_with_positions(rtml)

    result = []
    result_map = []
    i = 0
    while i < len(text):
        if text[i] == '-' and i + 1 < len(text) and text[i + 1] == '\n':
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


def normalize_with_mapping(text):
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


def load_rtml_unified():
    """Load rtml from all .terese files once.

    Returns (rtml_raw, rtml_text, source_map) where:
    - rtml_raw: concatenated rtml content WITH tags (paragraphs joined by \\n)
    - rtml_text: tag-stripped plain text
    - source_map: per-character (tiff_filename, top_pixel) for rtml_text
    """
    rtml_raw_parts = []
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

            # Collect raw rtml content
            rtml_raw_parts.append(rtml_content)

            # Parse boxes for source map
            boxes = []
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
                boxes.append((char, top))

            # Strip tags from rtml_content to get plain text
            plain, _ = strip_tags_with_positions(rtml_content)

            box_idx = 0
            # Skip leading boundary newline box if present
            if box_idx < len(boxes) and boxes[box_idx][0] == '\n':
                box_idx += 1

            # Build source map for this page's plain text
            page_source = []
            for ch in plain:
                if box_idx < len(boxes):
                    page_source.append((tiff_filename, boxes[box_idx][1]))
                    box_idx += 1
                else:
                    page_source.append((tiff_filename, 0))

            rtml_text_parts.append(plain)
            source_maps.append(page_source)

    # Join raw parts with \n
    rtml_raw = "\n".join(rtml_raw_parts)

    # Join text parts with synthetic newlines
    combined_text_parts = []
    combined_source = []
    for i, (part, smap) in enumerate(zip(rtml_text_parts, source_maps)):
        if i > 0:
            combined_text_parts.append("\n")
            combined_source.append((None, 0))
        combined_text_parts.append(part)
        combined_source.extend(smap)

    return rtml_raw, "".join(combined_text_parts), combined_source


def compute_full_alignment(html):
    """Compute alignment between HTML and rtml source.

    Returns an AlignmentResult with para_alignments (for spurious break
    detection) and matching_blocks/norm maps/source_map (for orth source
    attribution). Results are cached to disk as a pickle.
    """
    html_hash = hashlib.sha256(html.encode()).hexdigest()

    try:
        with open(_ALIGNMENT_CACHE, 'rb') as f:
            cache = pickle.load(f)
        if cache.get('html_hash') == html_hash:
            return cache['result']
    except (FileNotFoundError, pickle.UnpicklingError, KeyError, EOFError):
        pass

    rtml_raw, rtml_text, source_map = load_rtml_unified()

    result = AlignmentResult()
    result.source_map = source_map

    # --- Prepare rtml paragraphs ---
    rtml_paras = []
    for para in re.split(r'\n\n+', rtml_raw):
        if not para.strip():
            continue
        clean, _ = clean_rtml(para)
        norm, norm_to_clean = normalize_with_mapping(clean)
        hw_m = re.match(r'[a-z]+', norm)
        hw = hw_m.group(0) if hw_m else ''
        dashes = frozenset(i for i, ch in enumerate(clean) if ch == '—')
        rtml_paras.append((hw, norm, norm_to_clean, dashes))

    # --- Prepare HTML paragraphs ---
    para_matches = list(re.finditer(r'<p>(.*?)</p>', html, re.DOTALL))
    html_paras = []
    for pm in para_matches:
        content = pm.group(1)
        clean, clean_to_html = clean_html_text(content)
        clean_to_html_abs = [pm.start(1) + p for p in clean_to_html]
        norm, norm_to_clean = normalize_with_mapping(clean)
        hw_m = re.match(r'[a-z]+', norm)
        hw = hw_m.group(0) if hw_m else ''
        html_paras.append((hw, norm, norm_to_clean, clean_to_html_abs,
                           pm.start(1), pm.end(1)))

    # --- Greedy headword alignment ---
    aligned = []
    ri = 0
    for hi, hp in enumerate(html_paras):
        h_hw = hp[0]
        if not h_hw:
            continue
        for j in range(ri, min(ri + 20, len(rtml_paras))):
            if rtml_paras[j][0] == h_hw:
                aligned.append((hi, j))
                ri = j + 1
                break

    # --- Build global norm sequences for orth_sources ---
    # Normalize full rtml_text
    rtml_norm, rtml_norm_map = normalize_with_mapping(rtml_text)
    result.rtml_norm_map = rtml_norm_map

    # Normalize full html plain text
    html_plain, html_plain_map = clean_html_text(html)
    html_norm, html_norm_to_plain = normalize_with_mapping(html_plain)
    html_norm_to_html = [html_plain_map[j] for j in html_norm_to_plain]
    result.html_norm_to_html = html_norm_to_html

    # Build rtml_raw paragraph bounds and mapping for global block offsets
    rtml_raw_para_bounds = []
    prev_end = 0
    for m in re.finditer(r'\n\n+', rtml_raw):
        para = rtml_raw[prev_end:m.start()]
        if para.strip():
            rtml_raw_para_bounds.append((prev_end, m.start()))
        prev_end = m.end()
    last_para = rtml_raw[prev_end:]
    if last_para.strip():
        rtml_raw_para_bounds.append((prev_end, len(rtml_raw)))

    # Mapping: raw position → rtml_text position
    _, raw_pos_for_rtml_text = strip_tags_with_positions(rtml_raw)

    # --- Per-paragraph alignment ---
    matching_blocks = []

    for hi, rj in aligned:
        _, h_norm, h_n2c, h_c2h, h_start, h_end = html_paras[hi]
        _, r_norm, r_n2c, r_dashes = rtml_paras[rj]

        # For spurious_breaks: SequenceMatcher on per-paragraph cleaned norms
        sm = SequenceMatcher(None, h_norm, r_norm, autojunk=False)
        h_to_r = {}
        for block in sm.get_matching_blocks():
            for k in range(block.size):
                h_to_r[block.a + k] = block.b + k

        result.para_alignments.append(
            (h_to_r, r_dashes, h_norm, h_n2c, h_c2h, h_start, h_end, r_n2c)
        )

        # For orth_sources: SequenceMatcher on slices of global norm sequences
        # (different from above because global rtml_norm doesn't have hyphen removal)
        hn_start = bisect.bisect_left(html_norm_to_html, h_start)
        hn_end = bisect.bisect_right(html_norm_to_html, h_end - 1)
        if hn_start >= hn_end:
            continue

        if rj >= len(rtml_raw_para_bounds):
            continue
        rp_start_raw, rp_end_raw = rtml_raw_para_bounds[rj]
        rp_start = bisect.bisect_left(raw_pos_for_rtml_text, rp_start_raw)
        rp_end = bisect.bisect_left(raw_pos_for_rtml_text, rp_end_raw)
        rn_start = bisect.bisect_left(rtml_norm_map, rp_start)
        rn_end = bisect.bisect_right(rtml_norm_map, rp_end - 1)
        if rn_start >= rn_end:
            continue

        h_slice = html_norm[hn_start:hn_end]
        r_slice = rtml_norm[rn_start:rn_end]
        sm2 = SequenceMatcher(None, h_slice, r_slice, autojunk=False)
        for block in sm2.get_matching_blocks():
            if block.size > 0:
                matching_blocks.append(
                    (hn_start + block.a, rn_start + block.b, block.size)
                )

    matching_blocks.sort()
    result.matching_blocks = matching_blocks

    with open(_ALIGNMENT_CACHE, 'wb') as f:
        pickle.dump({'html_hash': html_hash, 'result': result}, f, protocol=pickle.HIGHEST_PROTOCOL)

    return result
