with open('web/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
import re
matches = re.findall(r'id=["\']np-title["\']', html)
print('Count of id=np-title:', len(matches))
