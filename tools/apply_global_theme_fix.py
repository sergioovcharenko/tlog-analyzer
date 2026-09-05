from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "index.html"
MARKER = "<!-- GLOBAL_THEME_SWITCH_FIX_V1 -->"

html = PATH.read_text(encoding="utf-8")
if MARKER in html:
    print("global theme switch fix already applied")
    raise SystemExit(0)

header_anchor = '''  <button class="btn-reset" id="resetBtn">📂 ВИБРАТИ НОВИЙ ЛОГ</button>\n</div>'''
header_replacement = '''  <div class="header-actions">\n    <div class="tlog-theme-switch" id="globalThemeSwitch" role="group" aria-label="Тема інтерфейсу">\n      <button type="button" data-theme-choice="dark" onclick="setTlogTheme('dark')">● Темна</button>\n      <button type="button" data-theme-choice="light" onclick="setTlogTheme('light')">○ Світла</button>\n    </div>\n    <button class="btn-reset" id="resetBtn">📂 ВИБРАТИ НОВИЙ ЛОГ</button>\n  </div>\n</div>'''
if header_anchor not in html:
    raise SystemExit("header anchor not found")
html = html.replace(header_anchor, header_replacement, 1)

css = '''\n/* GLOBAL_THEME_SWITCH_FIX_V1 */\n.header-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end}\n#globalThemeSwitch{display:inline-flex;flex:0 0 auto}\n#globalThemeSwitch button{cursor:pointer}\n@media(max-width:767px){.header{padding:14px 16px;gap:10px}.header-actions{gap:6px}#globalThemeSwitch button{min-height:40px}}\n'''
style_anchor = "\n</style>"
if style_anchor not in html:
    raise SystemExit("style anchor not found")
html = html.replace(style_anchor, css + style_anchor, 1)
html = html.replace("<body>", "<body>\n" + MARKER, 1)

PATH.write_text(html, encoding="utf-8")
print("global theme switch fix applied")
