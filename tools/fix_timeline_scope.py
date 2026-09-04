from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

anchor = 'function detectDisarmedPhysicalMovement(data){\n'
if anchor not in s:
    raise SystemExit('detector anchor not found')

before = s.split(anchor, 1)[0]
if 'function timelineSeconds(t){' not in before:
    helper = r'''// Global Timeline time parser used by analysis helpers outside renderResults().
function timelineSeconds(t){
  const m=String(t||'').match(/(-?)(\d+):(\d+(?:\.\d+)?)/);
  if(!m)return null;
  const v=(+m[2])*60+(+m[3]);
  return m[1]==='-'?-v:v;
}

'''
    s = s.replace(anchor, helper + anchor, 1)

p.write_text(s, encoding='utf-8')
print('global timelineSeconds helper ensured')
