from pathlib import Path

path = Path('index.html')
html = path.read_text(encoding='utf-8')
old = '<title>AI — TLOG Analyzer v1.3.3 «3D Lazy FIX»</title>'
new = '<title>AI — TLOG Analyzer</title>'
if old in html:
    html = html.replace(old, new, 1)
elif new not in html:
    raise SystemExit('page title anchor not found')
path.write_text(html, encoding='utf-8')
print('Clean page title applied')
