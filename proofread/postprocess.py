import re
import unicodedata

from text_alignment import compute_full_alignment
from spurious_breaks import remove_spurious_breaks
from sense_processing import split_paragraphs_at_orths, convert_senses_to_lists
from orth_sources import compute_orth_sources, apply_orth_attrs


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
    html = html.replace('C<i>', '<i>C')
    html = html.replace('<i>:</i>', ':')
    html = html.replace('<i>;</i>', ';')
    html = re.sub(',([a-z])', r', \1', html)
    html = re.sub(r' (aa|bb|cc|dd|ee)\. ', r'<br/>\n\1. ', html)

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
    JOIN_ABBREVS = {'l.', 'o.', 'wanl.', 'absol.', 'spec.', 'arch.', 'obr.', 'urspr.'}
    GRAMMAR = {'pl.', 'm.', 'Subst.', 'plur.', 'Dep.', 'subst.', 'f.', 'part.',
               'Abl.', 'Acc.', 'abl.', 'n.', 'pt.', 'pr.', 'p.', 'comp.', 'Comp.', 'dep.',
               'pf.', 'Superl.', 'neutr.'}

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
        # Word is = ( → JOIN
        if word in ('=', '('):
            return m.group(1) + ' ' + m.group(2)
        # Ends with ) but not ). or ?) → JOIN
        if word.endswith(')') and not word.endswith(').') and not word.endswith('?)'):
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

    alignment = compute_full_alignment(html)
    orth_attrs = compute_orth_sources(html, alignment)
    html = remove_spurious_breaks(html, alignment)
    html = apply_orth_attrs(html, orth_attrs)

    html = split_paragraphs_at_orths(html)

    html = convert_senses_to_lists(html)

    return html
