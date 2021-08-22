#!/user/bin/python3

import glob
import re

lexicon = []
for file_name in sorted(glob.glob('cavallinlatin-?-??.terese')):
    with open(file_name, 'r') as terese_file:
        terese = terese_file.read()
    for page in re.findall('<page .*?</page>', terese, flags=re.DOTALL):
        boxtext = ''.join(re.findall('<box c="(.*?)"', page, flags=re.DOTALL)).replace('\\n', '\n')
        rtmls = re.findall(r'<rtml>(.*?)\s*</rtml>', page, flags=re.DOTALL)
        assert len(rtmls) == 1
        #assert re.sub('<.*?>', '', rtmls[0]).strip() == boxtext.strip()
        #assert len(boxtext) > len(rtmls) - 10
        lexicon.append(rtmls[0])
lexicon = '\n'.join(lexicon)

# Versfötter
lexicon = re.sub('([⏑—]) ([⏑—])', '\\1\\2', lexicon)
lexicon = re.sub('([⏑—]) ([⏑—])', '\\1\\2', lexicon)

# Normalisera spärrad-taggen
lexicon = re.sub(r'(-?)<sp>(.*?)</sp>(\w*-?)', '<sp>\\1\\2\\3</sp>', lexicon, flags=re.DOTALL)

# Undvik brott i stil(ar) över radslut
n = 1
while n > 0:
    lexicon, n = re.subn('</(?P<pre>[^>]*)>(?P<mid>-?\n)<(?P=pre)>', '\\g<mid>', lexicon, flags=re.DOTALL)

# Justera fraktur:
lexicon = re.sub('</b></s><b>([ \n,-]*)<s>((.(?!/s>))*)</s></b>', '\\1\\2</b></s>', lexicon, flags=re.DOTALL)
lexicon = re.sub('</b></s>([ \n,-]*)<s><b>', '\\1', lexicon, flags=re.DOTALL)
lexicon = re.sub('</s>([ \n,:;.()=0-9-]*)<s>', '\\1', lexicon, flags=re.DOTALL)
lexicon = re.sub('([(][ \n=]*)<s>', '<s>\\1', lexicon, flags=re.DOTALL)
lexicon = re.sub('</s>([ \n=,;.:)-]*[,;.:)-](?=[\n ]))', '\\1</s>', lexicon, flags=re.DOTALL)

with open('lexicon.txt', 'w') as lexicon_file:
    lexicon_file.write(lexicon)

# Av-avstava (bör förfinas!)
#avstavade = set([x.replace('\n', '').lower() for x in re.findall(r'\w+-\n\w+', lexicon)])
#lowerlex = lexicon.lower()
#for a in avstavade:
#    if a in lowerlex and re.search(r'\b%s\b' % a, lowerlex):
#        print(a)
lexicon = re.sub(r' (\S*\w)-\n(\w)', '\n\\1\\2', lexicon)

lexicon = lexicon \
    .replace('ßſ', 'ss') \
    .replace('ſ', 's') \
    .replace('ß', 'ss') \
    .replace('ỳ', 'y̆') \
    .replace('Ỳ', 'Y̆')

lexicon = '<p>' + lexicon.replace('\n\n', '</p>\n\n<p>') + '</p>'
lexicon = lexicon.replace('sp>', 'u>')
lexicon = lexicon.replace('s>', 'span>')

for (first, second) in [('I', 'II'), ('1', '2'), ('a', 'b')]:
    lexicon = re.sub(r'(\s%s\.\s(.(?!<p>))*?\s—\s%s\.\s)' % (first, second), ' —\\1', lexicon, flags=re.DOTALL)
lexicon = re.sub(r'\n—\s|\s—\n', '\n<br/>', lexicon)
lexicon = re.sub(r'\s—\s', '<br/>', lexicon)
lexicon = re.sub(r'\n<u>', '\n<br/><u>', lexicon)
lexicon = re.sub(r'\s<u>', '<br/><u>', lexicon)

lexicon = re.sub(r'(<span>(.(?!</span>))*)(<br/>[0-9]+\.\s)', '\\1</span>\\3<span>', lexicon, flags=re.DOTALL)

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

