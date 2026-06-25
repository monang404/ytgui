css_append = """
/* SVG Icon overrides */
.nav-btn svg {
  width: 26px;
  height: 26px;
  margin-bottom: 4px;
}

.nav-btn:active svg {
  transform: scale(0.92);
}

.btn-prev svg, .btn-next svg {
  width: 22px;
  height: 22px;
}
"""

with open('web/static/css/base.css', 'a', encoding='utf-8') as f:
    f.write(css_append)

print("CSS appended to base.css")
