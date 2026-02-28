import re
import unicodedata


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
    html = re.sub(r" *<br/>\n([A-ZĀĂĒĔĪĬŌŎŪŬ]\S*)", lambda x: (" " + x.group(1)) if x.group(1)[-1] == ';' else x.group(0), html)

    # Locate headwords
    html = re.sub(r"^(<p>[IV]+\.\s+)(\S+)", lambda x: "#" + clean(x.group(2)) + "# " + x.group(0), html, flags=re.MULTILINE)
    html = re.sub(r"^(<[pbu]>\S+)", lambda x: "#" + clean(x.group(1)) + "# " + x.group(0), html, flags=re.MULTILINE)
    html = re.sub(r"<br/>\n([A-ZĀĂĒĔĪĬŌŎŪŬ]\S*)", lambda x: ("<br/>\n#" + clean(x.group(1)) + "# " + x.group(1)) if not is_sense_number(x.group(1)) else x.group(0), html)
    html = re.sub(r"^(#[^#]*# )(<p>)", "\\2\\1", html, flags=re.MULTILINE)

    return html
