from fodt_to_html import convert_fodt_files
from postprocess import postprocess

html = convert_fodt_files()
html = postprocess(html)

html = html.replace('!!!', '')

with open('cavallinlatin.html', 'w') as lexicon_file:
    lexicon_file.write("""<!doctype html>
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
""")
    lexicon_file.write(html)
    lexicon_file.write("""
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
</html>
""")
