import re
import json


def strip_html(text):
    return re.sub(r'<[^>]*>', '', text)


def score_paragraph(content, all_headwords):
    """Compute reference-likelihood score for a paragraph's inner content."""
    # Extract first orth text
    orth_m = re.search(r'<orth[^>]*>(.*?)</orth>', content)
    headword_html = orth_m.group(1) if orth_m else ''
    headword = strip_html(headword_html).rstrip(',')

    text = strip_html(content)
    text_length = len(text)

    # Features
    has_se_span = bool(re.search(r'<span>se</span>', content))
    has_bare_se = bool(re.search(r'</orth>\s*se\s+[A-Z]', content))
    has_ol = '<ol' in content
    orth_count = len(re.findall(r'<orth', content))

    span_contents = re.findall(r'<span>(.*?)</span>', content)
    span_count = len(span_contents)
    ref_connectives = {'se', 'o.', 'under', 'och', 'äfwen', 'eller'}
    only_se_spans = (span_count > 0 and
                     all(s.strip() in ref_connectives for s in span_contents))

    has_bold_orth = '<b>' in headword_html or '<b ' in headword_html
    has_underline_orth = '<u>' in headword_html

    has_definition_span = False
    for sc in span_contents:
        if sc.strip() in ref_connectives:
            continue
        if '<b>' in sc or len(strip_html(sc)) > 10:
            has_definition_span = True
            break

    citation_pattern = r'(?<![A-Za-z])(C\.|L\.|Vg\.|Hor\.|Sa\.|Juv\.|Pn\.|Ov\.|Vr\.|Pl\.|Tc\.|Cs\.|Sen\.|Liv\.|Cic\.)(?![A-Za-z])'
    has_citations = bool(re.search(citation_pattern, text))

    collector_entry = orth_count >= 2 and has_se_span and not has_definition_span

    hw_clean = re.sub(r'\W', '', headword.lower())
    duplicate_headword = len(all_headwords.get(hw_clean, [])) > 1 if hw_clean else False

    headword_ellipsis = headword.endswith('…')

    # Scoring
    score = 0
    if headword_ellipsis:
        score += 60
    elif has_se_span and only_se_spans:
        score += 50
    elif has_bare_se and not has_definition_span:
        score += 40
    elif collector_entry:
        score += 30
    elif has_se_span:
        score += 20

    if text_length < 80:
        score += 10
    if not has_bold_orth and not has_underline_orth:
        score += 5

    if has_ol:
        score -= 30
    if has_underline_orth:
        score -= 20
    if has_citations:
        score -= 15
    if has_definition_span:
        score -= 10
    if text_length > 300:
        score -= 10

    features = {
        'has_se_span': has_se_span,
        'has_bare_se': has_bare_se,
        'has_ol': has_ol,
        'span_count': span_count,
        'only_se_spans': only_se_spans,
        'text_length': text_length,
        'orth_count': orth_count,
        'has_bold_orth': has_bold_orth,
        'has_underline_orth': has_underline_orth,
        'has_definition_span': has_definition_span,
        'has_citations': has_citations,
        'collector_entry': collector_entry,
        'duplicate_headword': duplicate_headword,
        'headword_ellipsis': headword_ellipsis,
    }

    return score, headword, features


def prune_reference_entries(html):
    """Score paragraphs by likelihood of being cross-reference entries.
    Removes those with score >= 30. Writes analysis to JSON/TXT files."""

    # Split HTML into paragraph and non-paragraph chunks
    parts = re.split(r'(<p>.*?</p>)', html, flags=re.DOTALL)

    # First pass: collect all headwords for duplicate detection
    all_headwords = {}
    for part in parts:
        m = re.match(r'^<p>(.*)</p>$', part, re.DOTALL)
        if not m:
            continue
        orth_m = re.search(r'<orth[^>]*>(.*?)</orth>', m.group(1))
        if orth_m:
            hw = re.sub(r'\W', '', strip_html(orth_m.group(1)).rstrip(',').lower())
            if hw:
                all_headwords.setdefault(hw, []).append(True)

    # Second pass: score each paragraph, keep or discard
    output_parts = []
    results = []
    removed = 0

    for part in parts:
        m = re.match(r'^<p>(.*)</p>$', part, re.DOTALL)
        if not m:
            output_parts.append(part)
            continue

        content = m.group(1)
        score, headword, features = score_paragraph(content, all_headwords)

        results.append({
            'score': score,
            'headword': headword,
            'paragraph_preview': content[:200],
            'features': features,
        })

        if score >= 30:
            removed += 1
        else:
            if ('<span>se</span>' in content or '...' in content) and \
            '<ol' not in content and '<b>' not in content and \
            'Duini' not in content and \
            'Dīlectus' not in content and \
            'Mĕro' not in content and \
            'Trĭnundĭnum' not in content and \
            'Oenus' not in content and \
            'Adordior' not in content and \
            'Patella' not in content and \
            'Axilla' not in content:
                pass
            else:
                output_parts.append(part)

    results.sort(key=lambda x: (-x['score'], x['headword']))

    with open('reference_candidates.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    with open('reference_candidates.txt', 'w') as f:
        for r in results:
            preview = strip_html(r['paragraph_preview'])[:80]
            f.write(f"{r['score']:4d}  {r['headword']:30s}  {preview}\n")

    return ''.join(output_parts)
