import re
with open('web/static/js/dom.js', 'r', encoding='utf-8') as f:
    dom_js = f.read()

with open('web/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

dom_map = {}
for match in re.finditer(r'(\w+):\s*\$\("([^"]+)"\)', dom_js):
    dom_map[match.group(1)] = match.group(2)

missing = []
for var_name, id_str in dom_map.items():
    if f'id="{id_str}"' not in html and f"id='{id_str}'" not in html:
        missing.append(id_str)

print('Missing IDs:', missing)
