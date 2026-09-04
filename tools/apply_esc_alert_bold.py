from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

css = '.esc-fault-alert-bold{font-weight:800}'
if css not in s:
    anchor = '.ai-jump{display:inline-block;width:100%;cursor:pointer}'
    if anchor not in s:
        raise SystemExit('CSS anchor not found')
    s = s.replace(anchor, anchor + '\n' + css, 1)

lines = s.splitlines()
found = False
for i, line in enumerate(lines):
    if 'alerts.push(`<span class=' in line and '${firstAnomalyTime}' in line and 'Можливі причини' in line:
        found = True
        if 'esc-fault-alert-bold' not in line:
            lines[i] = line.replace('ai-jump', 'ai-jump esc-fault-alert-bold', 1)
        break

if not found:
    raise SystemExit('ESC alert line not found')

s = '\n'.join(lines) + ('\n' if s.endswith('\n') else '')
p.write_text(s, encoding='utf-8')
print('ESC alert bold patch applied')
