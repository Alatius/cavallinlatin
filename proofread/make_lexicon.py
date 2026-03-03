from fodt_to_html import convert_fodt_files
from postprocess import postprocess

html = convert_fodt_files()
html = postprocess(html)

with open('cavallinlatin.html', 'w') as lexicon_file:
    lexicon_file.write("""<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Latinskt-svenskt lexicon</title>
    <style>
span { background-color: #ceebfd; }
ol.sense-Roman { list-style-type: upper-roman; }
ol.sense-Alpha { list-style-type: upper-alpha; }
ol.sense-decimal { list-style-type: decimal; }
ol.sense-alpha { list-style-type: lower-alpha; }
ol.sense-greek { list-style-type: lower-greek; }
ol.sense-roman { list-style-type: lower-roman; }
ol.sense-double-alpha { list-style-type: lower-alpha; }
    </style>
  </head>
  <body>""")
    lexicon_file.write(html)
    lexicon_file.write("\n</body>\n</html>\n")
