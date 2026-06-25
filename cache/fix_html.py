import re

with open('web/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

def safe_replace(pattern, repl, name):
    global content
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, repl, content, count=1, flags=re.DOTALL)
        print(f'{name} replaced successfully.')
    else:
        print(f'{name} NOT FOUND.')

with open('docs/BAGAS_FM_AGENT_PLAYBOOK.md', 'r', encoding='utf-8') as f:
    playbook = f.read()

# Phase 3
m3 = re.search(r'## PHASE 3 — HOME TAB HTML.*?```html\n(.*?)```', playbook, re.DOTALL)
if m3:
    safe_replace(r'<section id="tab-home".*?</section>', m3.group(1), 'Phase 3 (Home Tab)')

# Phase 6
m6 = re.search(r'\*\*Update nav HTML di index\.html\*\*.*?```html\n(.*?)```', playbook, re.DOTALL)
if m6:
    safe_replace(r'<nav class="navrow" id="nav-bar">.*?</nav>', m6.group(1), 'Phase 6 (Nav Bar)')

# Phase 7.1
m7 = re.search(r'### 7.1 — Update Search Tab HTML.*?```html\n(.*?)```', playbook, re.DOTALL)
if m7:
    safe_replace(r'<section id="tab-search" class="tab-panel">.*?</section>', m7.group(1), 'Phase 7.1 (Search Tab)')

# Phase 8.1
m8 = re.search(r'### 8.1 — Update Radio Tab HTML.*?```html\n(.*?)```', playbook, re.DOTALL)
if m8:
    safe_replace(r'<section id="tab-radio" class="tab-panel">.*?</section>', m8.group(1), 'Phase 8.1 (Radio Tab)')

# Phase 10.1
m10 = re.search(r'### 10.1 — Update Discover Tab HTML.*?```html\n(.*?)```', playbook, re.DOTALL)
if m10:
    safe_replace(r'<section id="tab-discover" class="tab-panel">.*?</section>', m10.group(1), 'Phase 10.1 (Discover Tab)')

# Phase 12
m12_1 = re.search(r'\*\*Cari\*\* `<meta name="theme-color" content="#0d0d1c">` dan ganti dengan:.*?```html\n(.*?)```', playbook, re.DOTALL)
if m12_1:
    safe_replace(r'<meta name="theme-color" content="#0d0d1c">', m12_1.group(1), 'Phase 12 (Theme Color)')

m12_2 = re.search(r'\*\*Ganti\*\* `<title>bagas.fm — Music Player</title>` dengan:.*?```html\n(.*?)```', playbook, re.DOTALL)
if m12_2:
    safe_replace(r'<title>bagas.fm — Music Player</title>', m12_2.group(1), 'Phase 12 (Title)')

with open('web/static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
