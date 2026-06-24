import os

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple replacements
    content = content.replace('from web.server import create_app', 'from server.app import create_app')
    content = content.replace('from web.server import _state_to_dict', 'from server.serializers import state_to_dict as _state_to_dict')
    content = content.replace('from web.server import ConnectionManager', 'from server.handlers.websocket import ConnectionManager')
    content = content.replace('patch("web.server.get_metrics_content")', 'patch("server.handlers.http.get_metrics_content")')
    content = content.replace('di module web.server', 'di module server.handlers.http')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for root, _, files in os.walk('tests'):
    for file in files:
        if file.endswith('.py'):
            replace_in_file(os.path.join(root, file))
print('Done!')
