with open('web/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
print('vinyl-cover:', 'id="vinyl-cover"' in html)
print('np-thumb-icon:', 'id="np-thumb-icon"' in html)
print('np-eq-anim:', 'id="np-eq-anim"' in html)
