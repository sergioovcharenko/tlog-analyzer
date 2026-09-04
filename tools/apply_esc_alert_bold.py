from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

css = '.esc-fault-alert-bold{font-weight:800}'
if css not in s:
    anchor = '.ai-jump{display:inline-block;width:100%;cursor:pointer}'
    if anchor not in s:
        raise SystemExit('CSS anchor not found')
    s = s.replace(anchor, anchor + '\n' + css, 1)

needle = r'class=\"ai-jump\" data-jump-time=\"${firstAnomalyTime}\"'
replacement = r'class=\"ai-jump esc-fault-alert-bold\" data-jump-time=\"${firstAnomalyTime}\"'
if replacement not in s:
    if needle not in s:
        raise SystemExit('ESC alert anchor not found')
    s = s.replace(needle, replacement, 1)

p.write_text(s, encoding='utf-8')
print('ESC alert bold patch applied')
