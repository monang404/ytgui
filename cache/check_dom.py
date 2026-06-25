import re

with open('web/static/js/dom.js', 'r', encoding='utf-8') as f:
    dom_js = f.read()

with open('web/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# get mapping from dom variable to id
dom_map = {}
for match in re.finditer(r'([a-zA-Z0-9_]+):\s*\$\([\'"]([^\'"]+)[\'"]\)', dom_js):
    dom_map[match.group(1)] = match.group(2)

missing = []
for var, element_id in dom_map.items():
    if f'id="{element_id}"' not in html and f"id='{element_id}'" not in html:
        missing.append((var, element_id))

print('Missing elements in index.html:', missing)
