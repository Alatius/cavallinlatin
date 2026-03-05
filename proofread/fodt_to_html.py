import glob
from lxml import etree
import re


html_tags = {
    ('p', 'style-name="P2"'): "p",
    ('span', 'style-name="T1"'): "t1#",
    ('span', 'style-name="Fraktur"'): "span",
    ('line-break', ''): "br",
    ('p', 'style-name="P1"'): "p",
    ('span', 'style-name="T2"'): "t2#",
    ('soft-page-break', ''): "br",
    ('span', 'style-name="T4"'): "t4#",
    ('s', ''): "s",
    ('span', 'style-name="T3"'): "t3#",
    ('span', 'style-name="T6"'): "t6#",
    ('span', 'style-name="T5"'): "t5#",
    ('span', 'style-name="T7"'): "t7#",
    ('span', 'style-name="T8"'): "t8#",
    ('p', 'style-name="P3"'): "p",
    ('span', 'style-name="T9"'): "t9#",
}


def extract_html(element, num):
    html = []

    tag = element.tag.replace(
        '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}', ''
    )

    if tag in ['p', 'span', 'line-break', 's', 'soft-page-break', '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}text']:
        attributes_str = ', '.join([f'{key}="{element.attrib[key]}"' for key in sorted(element.attrib)]).replace(
            '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}', ''
        )

        html_tag = html_tags.get((tag, attributes_str), '')

        html_tag = html_tag.replace('#', '-' + str(num))

        if html_tag:
            html.append('<' + html_tag + '>')

        if element.text:
            html.append(element.text)

        for child in element:
            html.append(extract_html(child, num))

        if html_tag:
            html.append('</' + html_tag + '>')

    if element.tail:
        html.append(element.tail)

    return ''.join(html)


def convert_fodt_files():
    namespace = {'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'}

    html = []
    for num, fodt_file in enumerate(sorted(glob.glob("*.fodt"))):
        xml_tree = etree.parse(fodt_file)
        office_text_elements = xml_tree.xpath('//office:text', namespaces=namespace)

        for office_text in office_text_elements:
            html.append(extract_html(office_text, num))
            html.append('<fodtbreak/>')

    html = ''.join(html)

    html = html.replace("<br></br>", "<br/>\n")
    html = html.replace("t1-0>", "b>")
    html = html.replace("t2-0>", "u>")
    html = html.replace("t3-0>", "b>")
    html = html.replace("t4-0>", "i>")
    html = html.replace("<t6-0>", "").replace("</t6-0>", "")

    html = html.replace("t1-1>", "b>")
    html = html.replace("t2-1>", "b>")
    html = html.replace("t3-1>", "i>")
    html = html.replace("t4-1>", "i>")
    html = html.replace("<t5-1>", "").replace("</t5-1>", "")
    html = html.replace("t6-1>", "u>")
    html = html.replace("<t7-1>", "").replace("</t7-1>", "")

    html = html.replace("t1-2>", "u>")
    html = html.replace("t2-2>", "i>")
    html = html.replace("t3-2>", "b>")
    html = html.replace("<t4-2>", "").replace("</t4-2>", "")
    html = html.replace("<t5-2>", "").replace("</t5-2>", "")


    html = html.replace("<t4-3>", "").replace("</t4-3>", "")
    html = html.replace("t1-3>", "u>")
    html = html.replace("t2-3>", "i>")
    html = html.replace("t3-3>", "b>")
    #html = html.replace("t4-3>", "b>")

    html = html.replace("t1-4>", "b>")
    html = html.replace("t2-4>", "b>")
    html = html.replace("t3-4>", "i>")
    html = html.replace("t4-4>", "u>")
    html = html.replace("t5-4>", "b>")
    html = html.replace("<t6-4>", "").replace("</t6-4>", "")
    html = html.replace("<t7-4>", "").replace("</t7-4>", "")
    html = html.replace("<t8-4>", "").replace("</t8-4>", "")

    html = html.replace("t1-5>", "u>")
    html = html.replace("t2-5>", "b>")
    html = html.replace("t3-5>", "i>")
    html = html.replace("<t4-5>", "").replace("</t4-5>", "")

    html = html.replace("t1-6>", "b>")
    html = html.replace("t2-6>", "u>")
    html = html.replace("t3-6>", "b>")
    html = html.replace("t4-6>", "i>")
    html = html.replace("<t5-6>", "").replace("</t5-6>", "")

    html = html.replace("t1-7>", "u>")
    html = html.replace("t2-7>", "b>")
    html = html.replace("t3-7>", "i>")
    html = html.replace("t4-7>", "b>")
    html = html.replace("t5-7>", "b>")
    html = html.replace("<t6-7>", "").replace("</t6-7>", "")
    html = html.replace("<t7-7>", "").replace("</t7-7>", "")

    html = html.replace("t1-8>", "b>")
    html = html.replace("t2-8>", "i>")
    html = html.replace("t3-8>", "u>")
    html = html.replace("t4-8>", "b>")

    html = html.replace("t1-9>", "i>")
    html = html.replace("t2-9>", "u>")
    html = html.replace("t3-9>", "b>")

    html = html.replace("t1-10>", "u>")
    html = html.replace("t2-10>", "b>")
    html = html.replace("t3-10>", "i>")
    html = html.replace("<t4-10>", "").replace("</t4-10>", "")

    html = html.replace("t1-11>", "b>")
    html = html.replace("t2-11>", "u>")
    html = html.replace("t3-11>", "i>")
    html = html.replace("t4-11>", "span>")
    html = html.replace("<t5-11>", "").replace("</t5-11>", "")

    html = html.replace("t1-12>", "b>")
    html = html.replace("t2-12>", "i>")
    html = html.replace("t3-12>", "i>")
    html = html.replace("t4-12>", "u>")
    html = html.replace("t5-12>", "b>")
    html = html.replace("<t6-12>", "").replace("</t6-12>", "")

    html = html.replace("t1-13>", "b>")
    html = html.replace("t2-13>", "u>")
    html = html.replace("t3-13>", "u>")
    html = html.replace("t4-13>", "b>")
    html = html.replace("t5-13>", "i>")
    html = html.replace("t6-13>", "i>")
    html = html.replace("t7-13>", "i>")
    html = html.replace("<t8-13>", "").replace("</t8-13>", "")
    html = html.replace("<t9-13>", "").replace("</t9-13>", "")

    html = html.replace("t1-14>", "i>")
    html = html.replace("t2-14>", "b>")
    html = html.replace("t3-14>", "b>")
    html = html.replace("t4-14>", "u>")
    html = html.replace("<t5-14>", "").replace("</t5-14>", "")

    html = html.replace("t1-15>", "b>")
    html = html.replace("t2-15>", "b>")
    html = html.replace("t3-15>", "i>")
    html = html.replace("t4-15>", "u>")

    html = html.replace("t1-16>", "b>")
    html = html.replace("t2-16>", "u>")
    html = html.replace("t3-16>", "i>")
    html = html.replace("<t4-16>", "").replace("</t4-16>", "")

    html = html.replace("t1-17>", "u>")
    html = html.replace("t2-17>", "i>")
    html = html.replace("t3-17>", "b>")

    html = html.replace("t1-18>", "b>")
    html = html.replace("t2-18>", "b>")
    html = html.replace("t3-18>", "u>")
    html = html.replace("t4-18>", "u>")
    html = html.replace("t5-18>", "i>")
    html = html.replace("<t6-18>", "").replace("</t6-18>", "")

    html = html.replace("t1-19>", "b>")
    html = html.replace("t2-19>", "u>")
    html = html.replace("t3-19>", "u>")
    html = html.replace("t4-19>", "u>")
    html = html.replace("t5-19>", "i>")
    html = html.replace("<t6-19>", "").replace("</t6-19>", "")

    html = html.replace("t1-20>", "u>")
    html = html.replace("t2-20>", "i>")
    html = html.replace("t3-20>", "b>")

    html = html.replace("t1-21>", "u>")
    html = html.replace("t2-21>", "b>")
    html = html.replace("t3-21>", "u>")
    html = html.replace("t4-21>", "i>")
    html = html.replace("t5-21>", "b>")

    html = html.replace("t1-22>", "b>")
    html = html.replace("t2-22>", "i>")
    html = html.replace("t3-22>", "u>")
    html = html.replace("<t4-22>", "").replace("</t4-22>", "")

    html = html.replace("t1-23>", "b>")
    html = html.replace("t2-23>", "b>")
    html = html.replace("t3-23>", "i>")
    html = html.replace("<t4-23>", "").replace("</t4-23>", "")
    html = html.replace("t5-23>", "u>")
    html = html.replace("t6-23>", "u>")

    html = html.replace("t1-24>", "b>")
    html = html.replace("t2-24>", "u>")
    html = html.replace("t3-24>", "i>")
    html = html.replace("<t4-24>", "").replace("</t4-24>", "")
    html = html.replace("<t5-24>", "").replace("</t5-24>", "")

    html = html.replace("t1-25>", "b>")
    html = html.replace("t2-25>", "i>")
    html = html.replace("t3-25>", "u>")
    html = html.replace("<t4-25>", "").replace("</t4-25>", "")

    html = html.replace("t1-26>", "b>")
    html = html.replace("t2-26>", "u>")
    html = html.replace("t3-26>", "i>")


    html = html.replace("</span><span>", "")
    html = html.replace("</b><b>", "")
    html = html.replace("</i><i>", "")
    html = html.replace("</u><u>", "")
    html = html.replace("   <p>", "\n<p>")

    html = html.replace("<br/>\n<b><br/>\n", "</p>\n\n<p><b>")

    html = re.sub(r'-</span></p>\s*<fodtbreak/>\s*<p><span>', '', html)
    html = re.sub(r'</b></span></p>\s*<fodtbreak/>\s*<p><span><b>', ' ', html)
    html = re.sub(r'</span></p>\s*<fodtbreak/>\s*<p><span>', ' ', html)
    html = re.sub(r'</p>\s*<fodtbreak/>\s*<p><br/>\n', r'</p>\n\n<p>', html)
    html = re.sub(r'</p>\s*<fodtbreak/>\s*(<p>(I\. )?<b>)', r'</p>\n\n\1', html)
    html = re.sub(r' —</p>\s*<fodtbreak/>\s*<p>', '<br/>\n', html)
    html = re.sub(r'-</p>\s*<fodtbreak/>\s*<p>', '', html)
    html = re.sub(r'</p>\s*<fodtbreak/>\s*<p>', ' ', html)
    html = html.replace('<fodtbreak/>', '')
    
    return html
