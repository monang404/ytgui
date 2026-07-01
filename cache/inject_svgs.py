import urllib.request
import re

def get_svg(name, class_name):
    url = f'https://raw.githubusercontent.com/tabler/tabler-icons/master/icons/filled/{name}.svg'
    svg = urllib.request.urlopen(url).read().decode('utf-8')
    svg = re.sub(r'<!--.*?-->\n*', '', svg, flags=re.DOTALL)
    svg = svg.replace('<svg', f'<svg class="{class_name}" ', 1)
    return svg

with open('web/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

home_svg = get_svg('home', 'ti ti-home')
html = re.sub(r'<i class="ti ti-home".*?>\s*</i>', home_svg, html)

prev_svg = get_svg('player-skip-back', 'ti ti-player-skip-back')
html = re.sub(r'<i class="ti ti-player-skip-back".*?>\s*</i>', prev_svg, html)

next_svg = get_svg('player-skip-forward', 'ti ti-player-skip-forward')
html = re.sub(r'<i class="ti ti-player-skip-forward".*?>\s*</i>', next_svg, html)

with open('web/static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('SVGs injected into index.html!')
