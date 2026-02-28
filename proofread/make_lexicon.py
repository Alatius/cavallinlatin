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
    </style>
  </head>
  <body>""")
    lexicon_file.write(html)
    lexicon_file.write("\n</body>\n</html>\n")
