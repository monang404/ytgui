with open('server/handlers/websocket.py', 'r', encoding='utf-8') as f:
    code = f.read()
import re
print(re.search(r'elif action == "discover":.*?ensure_ascii=False\)\)', code, re.DOTALL).group(0))
