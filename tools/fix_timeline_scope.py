from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

# 1) Keep the global timeline parser available to global detectors.
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

# 2) Restore analysis objects that the TX16 patch accidentally removed from renderResults().
combined = '  const combinedAiAlerts=[\n'
if combined not in s:
    raise SystemExit('combinedAiAlerts anchor not found')

render_start = s.find('function renderResults(data){')
combined_pos = s.find(combined, render_start)
if render_start < 0 or combined_pos < 0:
    raise SystemExit('renderResults block not found')
render_prefix = s[render_start:combined_pos]

restore = '''  const disarmedMovement=detectDisarmedPhysicalMovement(data);
  if(disarmedMovement.events.length){
    data.timeline=[...(Array.isArray(data.timeline)?data.timeline:[]),...disarmedMovement.events]
      .sort((a,b)=>(timelineSeconds(a?.time)??0)-(timelineSeconds(b?.time)??0));
  }

  const escPowertrain=buildEscPowertrainAlerts(data.timeline);
  if(escPowertrain.events.length){
    data.timeline=[...(Array.isArray(data.timeline)?data.timeline:[]),...escPowertrain.events]
      .sort((a,b)=>(timelineSeconds(a?.time)??0)-(timelineSeconds(b?.time)??0));
  }

  const maxCurrentRow=(Array.isArray(data.timeline)?data.timeline:[])
    .filter(row=>typeof row?.curr==='number'&&Number.isFinite(row.curr))
    .reduce((best,row)=>(!best||row.curr>best.curr)?row:best,null);
  const highCurrentAlerts=[];
  if(maxCurrentRow&&maxCurrentRow.curr>80){
    const time=maxCurrentRow.time||'';
    const jumpAttr=time?` data-jump-time=\"${time}\"`:'';
    highCurrentAlerts.push(`<span class=\"ai-jump\" data-attention-severity=\"attention\"${jumpAttr}>⚡ <b>ВИСОКЕ СПОЖИВАННЯ СТРУМУ:</b> максимум ${maxCurrentRow.curr.toFixed(1)} A${time?` о ${time}`:''}. Порогове значення уваги: &gt;80 A.${time?' Натисніть, щоб перейти до Timeline.':''}</span>`);
  }

'''

missing = []
if 'const disarmedMovement=detectDisarmedPhysicalMovement(data);' not in render_prefix:
    missing.append('disarmedMovement')
if 'const escPowertrain=buildEscPowertrainAlerts(data.timeline);' not in render_prefix:
    missing.append('escPowertrain')
if 'const highCurrentAlerts=[];' not in render_prefix:
    missing.append('highCurrentAlerts')

if missing:
    s = s[:combined_pos] + restore + s[combined_pos:]
    print('restored renderResults prerequisites:', ', '.join(missing))
else:
    print('renderResults prerequisites already present')

p.write_text(s, encoding='utf-8')
