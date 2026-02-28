from fodt_to_html import convert_fodt_files
from postprocess import postprocess_and_write

html = convert_fodt_files()
postprocess_and_write(html)
