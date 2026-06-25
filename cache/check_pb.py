with open('web/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
print('Count of player-bar:', html.count('id="player-bar"'))
