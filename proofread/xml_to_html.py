"""Convert cavallinlatin.xml to cavallinlatin.html for browser viewing."""

import re


def xml_to_html(xml_path='cavallinlatin.xml', html_path='cavallinlatin.html'):
    with open(xml_path, encoding='utf-8') as f:
        xml = f.read()

    # Extract content between <dictionary> tags
    m = re.search(r'<dictionary>\s*(.*?)\s*</dictionary>', xml, re.DOTALL)
    if not m:
        raise ValueError('No <dictionary> element found')
    body = m.group(1)

    # Convert <entry ...>...</entry> to <p>...</p>, preserving attributes
    body = re.sub(r'<entry([^>]*)>', r'<p\1>', body)
    body = body.replace('</entry>', '</p>')

    # Unescape &amp; back to & (HTML handles bare & in text fine)
    body = body.replace('&amp;', '&')

    entry_count = body.count('<p')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write('''<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Latinskt-svenskt lexicon</title>
    <link rel="stylesheet" href="cavallinlatin.css">
    <script>
      (function() {
        var w = localStorage.getItem('image-panel-width');
        if (w) document.write('<style>#image-panel{width:' + parseInt(w) + 'px}</style>');
      })();
    </script>
  </head>
  <body>
<div id="content">

''')
        f.write(body)
        f.write('''

</div>
<div id="resize-handle"></div>
<div id="image-panel">
  <div id="image-panel-header">
    <span id="image-panel-label"></span>
  </div>
  <div id="image-panel-img-container">
    <img id="image-panel-img">
  </div>
</div>
<script src="cavallinlatin.js"></script>
</body>
</html>''')

    print(f'  Wrote {entry_count} entries to {html_path}')


if __name__ == '__main__':
    xml_to_html()
