from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

css_anchor = '.esc-fault-alert-bold{font-weight:800}'
css = r'''
.attention-summary-item{list-style:none;margin-left:-20px}
.attention-summary{
  border:1px solid var(--border-color);
  border-radius:8px;
  background:#0f141c;
  overflow:hidden
}
.attention-summary>summary{
  cursor:pointer;
  padding:11px 13px;
  font-weight:800;
  color:#f8fafc;
  user-select:none
}
.attention-summary[open]>summary{border-bottom:1px solid var(--border-color)}
.attention-groups{display:grid;gap:8px;padding:10px}
.attention-section{
  border:1px solid var(--border-color);
  border-radius:7px;
  overflow:hidden;
  background:rgba(15,20,28,.72)
}
.attention-section>summary{
  cursor:pointer;
  padding:8px 10px;
  font-weight:800;
  user-select:none
}
.attention-items{margin:0;padding:6px 10px 8px 30px;line-height:1.45}
.attention-items li{margin:3px 0;padding:4px 6px;border-radius:5px}
.attention-critical{border-left:4px solid #ef4444}
.attention-critical>summary{color:#fca5a5}
.attention-critical .ai-clickable{background:rgba(239,68,68,.07)}
.attention-attention{border-left:4px solid #f97316}
.attention-attention>summary{color:#fdba74}
.attention-attention .ai-clickable{background:rgba(249,115,22,.07)}
.attention-warning{border-left:4px solid #eab308}
.attention-warning>summary{color:#fde047}
.attention-warning .ai-clickable{background:rgba(234,179,8,.06)}
.attention-info{border-left:4px solid #3b82f6}
.attention-info>summary{color:#93c5fd}
.attention-info .ai-clickable{background:rgba(59,130,246,.05)}
'''.strip()

if '.attention-summary{' not in s:
    if css_anchor not in s:
        raise SystemExit('CSS anchor not found')
    s = s.replace(css_anchor, css_anchor + '\n' + css, 1)

helper = r'''
function attentionSeverityForAlert(alertHtml){
  const raw=String(alertHtml||'');
  const explicit=raw.match(/data-attention-severity=["'](critical|attention|warning|info)["']/i);
  if(explicit)return explicit[1].toLowerCase();

  const text=raw.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim();
  if(
    /ЙМОВІРНА НЕСПРАВНІСТЬ MOTOR\/ESC/i.test(text)||
    /Критичний кут нахилу БПЛА/i.test(text)||
    /Лог закінчився при ARMED/i.test(text)||
    /ЛОГ ОБІРВАВСЯ ПРИ ARMED/i.test(text)
  )return 'critical';

  if(/Potential Thrust Loss/i.test(text)||/SH натиснуто без дозволу/i.test(text))return 'warning';

  if(/EMERGENCY STOP/i.test(text)&&/не зафіксовано/i.test(text))return 'info';
  if(/SC \+ SF/i.test(text)&&/не зафіксовано/i.test(text))return 'info';

  if(
    /ВИСОКЕ СПОЖИВАННЯ СТРУМУ/i.test(text)||
    /Підсумок системи скиду/i.test(text)||
    /СКИД/i.test(text)||
    /EMERGENCY STOP/i.test(text)
  )return 'attention';

  return 'info';
}

function attentionAlertListItem(alertHtml){
  const raw=String(alertHtml||'');
  const explicit=raw.match(/data-jump-time=["']([^"']+)["']/i);
  const plain=raw.replace(/<[^>]+>/g,' ');
  const fallback=plain.match(/-?\d{2}:\d{2}\.\d{3}/);
  const jumpTime=explicit?.[1]||fallback?.[0]||'';
  return `<li class="${jumpTime?'ai-clickable':''}" ${jumpTime?`data-jump-time="${jumpTime}" title="Перейти до рядка Timeline"`:''}>${raw}</li>`;
}

function buildAttentionSummaryHtml(alerts){
  const groups={critical:[],attention:[],warning:[],info:[]};
  (Array.isArray(alerts)?alerts:[]).forEach(alert=>{
    groups[attentionSeverityForAlert(alert)].push(attentionAlertListItem(alert));
  });

  const total=Object.values(groups).reduce((sum,items)=>sum+items.length,0);
  const config=[
    ['critical','🔴 Критичне'],
    ['attention','🟠 Увага'],
    ['warning','🟡 Попередження'],
    ['info','🔵 Інформація']
  ];
  const sections=config
    .filter(([key])=>groups[key].length)
    .map(([key,label])=>`<details class="attention-section attention-${key}" ${(key==='critical'||key==='attention')?'open':''}><summary>${label} — ${groups[key].length}</summary><ul class="attention-items">${groups[key].join('')}</ul></details>`)
    .join('');

  return `<li class="attention-summary-item"><details class="attention-summary"><summary>⚠️ <b>На що звернути увагу</b> — ${total} подій</summary><div class="attention-groups">${sections}</div></details></li>`;
}

'''

render_anchor = 'function renderResults(data){'
if 'function buildAttentionSummaryHtml' not in s:
    if render_anchor not in s:
        raise SystemExit('renderResults anchor not found')
    s = s.replace(render_anchor, helper + render_anchor, 1)

combined_old = r'''  const combinedAiAlerts=[
    ...(data.ai?.alerts||[]),
    ...buildTx16ActivationAlerts(data.timeline),
    ...disarmedMovement.alerts,
    ...escPowertrain.alerts
  ];

  document.getElementById('aiAlerts').innerHTML=combinedAiAlerts
    .map(x=>{
      const explicit=String(x).match(/data-jump-time=["']([^"']+)["']/i);
      const plain=String(x).replace(/<[^>]+>/g,' ');
      const fallback=plain.match(/-?\d{2}:\d{2}\.\d{3}/);
      const jumpTime=explicit?.[1]||fallback?.[0]||'';
      return `<li class="${jumpTime?'ai-clickable':''}" ${jumpTime?`data-jump-time="${jumpTime}" title="Перейти до рядка Timeline"`:''}>${x}</li>`;
    })
    .join('');'''

combined_new = r'''  const maxCurrentRow=(Array.isArray(data.timeline)?data.timeline:[])
    .filter(row=>typeof row?.curr==='number'&&Number.isFinite(row.curr))
    .reduce((best,row)=>(!best||row.curr>best.curr)?row:best,null);
  const highCurrentAlerts=[];
  if(maxCurrentRow&&maxCurrentRow.curr>80){
    const time=maxCurrentRow.time||'';
    const jumpAttr=time?` data-jump-time="${time}"`:'';
    highCurrentAlerts.push(`<span class="ai-jump" data-attention-severity="attention"${jumpAttr}>⚡ <b>ВИСОКЕ СПОЖИВАННЯ СТРУМУ:</b> максимум ${maxCurrentRow.curr.toFixed(1)} A${time?` о ${time}`:''}. Порогове значення уваги: &gt;80 A.${time?' Натисніть, щоб перейти до Timeline.':''}</span>`);
  }

  const combinedAiAlerts=[
    ...highCurrentAlerts,
    ...(data.ai?.alerts||[]),
    ...buildTx16ActivationAlerts(data.timeline),
    ...disarmedMovement.alerts,
    ...escPowertrain.alerts
  ];

  document.getElementById('aiAlerts').innerHTML=buildAttentionSummaryHtml(combinedAiAlerts);'''

if 'buildAttentionSummaryHtml(combinedAiAlerts' not in s:
    if combined_old not in s:
        raise SystemExit('combined AI alerts block not found')
    s = s.replace(combined_old, combined_new, 1)

p.write_text(s, encoding='utf-8')
print('Attention summary patch applied')
