import os
import re

for root, _, files in os.walk('tests'):
    for file in files:
        if not file.endswith('.py'):
            continue
        filepath = os.path.join(root, file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        orig = content
        
        # We need to fix the bad replacement first!
        content = content.replace(r'\"\\n\".join([p.read_text', r'"\n".join([p.read_text')
        content = content.replace(r'\"\n\".join([p.read_text', r'"\n".join([p.read_text')
        content = content.replace(r'\"\\n\"', r'"\n"')
        content = content.replace(r'\"\n\"', r'"\n"')

        if orig != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Fixed {filepath}')
