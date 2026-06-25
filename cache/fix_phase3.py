import re

with open('docs/BAGAS_FM_AGENT_PLAYBOOK.md', 'r', encoding='utf-8') as f:
    playbook = f.read()

# Get all HTML blocks under PHASE 3
m_phase3 = re.search(r'## PHASE 3(.*?)## PHASE 4', playbook, re.DOTALL | re.IGNORECASE)
if m_phase3:
    blocks = re.findall(r'```html\n(.*?)```', m_phase3.group(1), re.DOTALL)
    if len(blocks) >= 2:
        correct_block = blocks[1] # The second one is 'Ganti SELURUH blok section#tab-home dengan ini:'
        
        with open('web/static/index.html', 'r', encoding='utf-8') as f:
            html = f.read()
            
        # Replace the botched tab-home
        new_html = re.sub(r'<section id="tab-home" class="tab-panel active full-player-view">.*?</section>', correct_block, html, count=1, flags=re.DOTALL)
        
        with open('web/static/index.html', 'w', encoding='utf-8') as f:
            f.write(new_html)
        print('Successfully applied correct Phase 3 HTML!')
    else:
        print('Less than 2 blocks found in Phase 3.')
else:
    print('Phase 3 section not found in playbook.')
