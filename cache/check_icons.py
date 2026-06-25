import re
with open('web/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

print('Home icon:', re.search(r'<i class="ti ti-home.*?>', html).group(0))
print('Next icon:', re.search(r'<i class="ti ti-player-skip-forward.*?>', html).group(0))
print('Prev icon:', re.search(r'<i class="ti ti-player-skip-back.*?>', html).group(0))
