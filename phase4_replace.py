import os

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    orig = content
    content = content.replace('from plugins.', 'from plugins.')
    content = content.replace('import plugins.', 'import plugins.')
    content = content.replace('engine.queue_manager', 'engine.queue_manager')
    content = content.replace('engine.radio_engine', 'engine.radio_engine')
    
    # Check for direct 'from plugins import'
    content = content.replace('from plugins import', 'from plugins import')
    content = content.replace('plugins/notifications', 'plugins/notifications')
    
    # specific termux import
    content = content.replace('plugins.notifications', 'plugins.notifications')
    
    if content != orig:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, _, files in os.walk('.'):
    if '.git' in root or '.pytest_cache' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            replace_in_file(os.path.join(root, file))
print('Done!')
