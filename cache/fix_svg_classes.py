with open('web/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
import re
html = re.sub(r'<svg class="ti ti-home"', '<svg class="svg-filled-icon nav-icon-svg"', html)
html = re.sub(r'<svg class="ti ti-player-skip-back"', '<svg class="svg-filled-icon player-icon-svg"', html)
html = re.sub(r'<svg class="ti ti-player-skip-forward"', '<svg class="svg-filled-icon player-icon-svg"', html)
with open('web/static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('Fixed SVG classes')
