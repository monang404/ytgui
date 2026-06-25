import re

# 1. Update index.html classes for icons
with open('web/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('ti-home"', 'ti-home-filled"')
html = html.replace('ti-player-skip-forward"', 'ti-player-skip-forward-filled"')
html = html.replace('ti-player-skip-back"', 'ti-player-skip-back-filled"')

with open('web/static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# 2. Append CSS for colors to player.css to override base.css
css_append = """
/* Hover & active colors for player controls */
.btn-prev, .btn-next {
    color: #fff !important;
}
.btn-prev:hover, .btn-next:hover,
.btn-shuffle:hover, .btn-repeat:hover {
    color: var(--accent) !important;
}
"""

with open('web/static/css/player.css', 'a', encoding='utf-8') as f:
    f.write(css_append)

print("Icons and CSS updated!")
