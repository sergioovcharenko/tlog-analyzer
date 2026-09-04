from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

css = '.esc-fault-alert-bold{font-weight:800}'
if css not in s:
    anchor = '.ai-jump{display:inline-block;width:100%;cursor:pointer}'
    if anchor not in s:
        raise SystemExit('CSS anchor not found')
    s = s.replace(anchor, anchor + '\n' + css, 1)

old = 'alerts.push(`<span class=\\"ai-jump\\" data-jump-time=\\"${firstAnomalyTime}\\">${text} Можливі причини: двигун, ESC, силове з\'єднання або живлення; TLOG не встановлює конкретну фізичну причину. Натисніть, щоб перейти до Timeline.</span>`);'
new = 'alerts.push(`<span class=\\"ai-jump esc-fault-alert-bold\\" data-jump-time=\\"${firstAnomalyTime}\\">${text} Можливі причини: двигун, ESC, силове з\'єднання або живлення; TLOG не встановлює конкретну фізичну причину. Натисніть, щоб перейти до Timeline.</span>`);'
if 'class=\\"ai-jump esc-fault-alert-bold\\"' not in s:
    if old not in s:
        raise SystemExit('ESC alert anchor not found')
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('ESC alert bold patch applied')
