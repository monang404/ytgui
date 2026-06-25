import re

with open('web/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

m_pb = re.search(r'(<!-- ═══ Player Bar ═══ -->\s*<div class="pbar" id="player-bar">.*?(?=<!-- ═══ Navigation Bar ═══ -->))', html, re.DOTALL)

if not m_pb:
    m_pb = re.search(r'(<!-- . Player Bar . -->\s*<div class="pbar" id="player-bar">.*?(?=<!-- . Navigation Bar . -->))', html, re.DOTALL)

if m_pb:
    pb_html = m_pb.group(1)
    # remove it from original
    html = html.replace(pb_html, '')
    
    # insert it into tab-home before home-recent-section
    target = r'<!-- ══ Recently Played ══ -->'
    if target in html:
        html = html.replace(target, pb_html + '\n    ' + target)
        with open('web/static/index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print('Moved player-bar inside tab-home!')
    else:
        print('Could not find Recently Played marker')
else:
    print('player-bar not found')
