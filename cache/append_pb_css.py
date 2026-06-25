with open('web/static/css/player.css', 'a', encoding='utf-8') as f:
    f.write('\n/* Transparent player bar on home tab */\n')
    f.write('body[data-active-tab="home"] #player-bar {\n')
    f.write('    background: transparent;\n')
    f.write('    border: none;\n')
    f.write('    padding-top: 10px;\n')
    f.write('    padding-bottom: 20px;\n')
    f.write('}\n')
print('Appended transparent background CSS to player.css!')
