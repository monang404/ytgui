with open('web/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
m = re.search(r'(<div class="pbar" id="player-bar">.*?)<!-- \S', html, re.DOTALL)
if m:
    with open('cache/pb_html.txt', 'w', encoding='utf-8') as f:
        f.write(m.group(1))
