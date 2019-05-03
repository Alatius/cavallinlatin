#!/user/bin/python3

import glob
import re

lexicon = []
for file_name in sorted(glob.glob('cavallinlatin-?-??.terese')):
    with open(file_name, 'r') as terese_file:
        terese = terese_file.read()
    for rtml in re.findall('<rtml>(.*?)\s*</rtml>', terese, flags=re.DOTALL):
        lexicon.append(rtml)
lexicon = '\n'.join(lexicon)

# Normalisera spärrad-taggen
lexicon = re.sub('(-?)<sp>(.*?)</sp>(\w*-?)', '<sp>\\1\\2\\3</sp>', lexicon, flags=re.DOTALL)

# Undvik brott i stil(ar) över radslut
n = 1
while n > 0:
    lexicon, n = re.subn('</(?P<pre>[^>]*)>(?P<mid>-?\n)<(?P=pre)>', '\\g<mid>', lexicon, flags=re.DOTALL)

# Av-avstava (bör förfinas!)
lexicon = re.sub(' (\S*\w)-\n(\w)', '\n\\1\\2', lexicon)

# Justera fraktur:
lexicon = re.sub('</b></s>([ \n,-]*)<s><b>', '\\1', lexicon, flags=re.DOTALL)
lexicon = re.sub('</s>([ \n,:;.()=-]*)<s>', '\\1', lexicon, flags=re.DOTALL)
lexicon = re.sub('([(][ \n=]*)<s>', '<s>\\1', lexicon, flags=re.DOTALL)
lexicon = re.sub('</s>([ \n=,;.:)-]*[,;.:)-](?=[\n ]))', '\\1</s>', lexicon, flags=re.DOTALL)


lexicon = lexicon.replace('ſ', 's').replace('ß', 'ss').replace('ỳ', 'y̆').replace('Ỳ', 'Y̆')

with open('lexicon.txt', 'w') as lexicon_file:
    lexicon_file.write(lexicon)

lexicon = '<p>' + lexicon.replace('\n\n', '</p>\n\n<p>') + '</p>'
lexicon = lexicon.replace('sp>', 'u>')
lexicon = lexicon.replace('s>', 'span>')

for (first, second) in [('I', 'II'), ('1', '2'), ('a', 'b')]:
    lexicon = re.sub('(\s%s\.\s(.(?!<p>))*?\s—\s%s\.\s)' % (first, second), ' —\\1', lexicon, flags=re.DOTALL)
lexicon = re.sub('\s—\s', '<br/>', lexicon)
lexicon = re.sub('\s<u>', '<br/><u>', lexicon)


with open('lexicon.html', 'w') as lexicon_file:
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
    lexicon_file.write(lexicon)
    lexicon_file.write("\n</body>\n</html>\n")

