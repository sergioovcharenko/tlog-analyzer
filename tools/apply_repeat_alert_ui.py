from pathlib import Path
import re

html_path = Path('index.html')
backend_path = Path('backend/main.py')
html = html_path.read_text(encoding='utf-8')
backend = backend_path.read_text(encoding='utf-8')

# ------------------------------------------------------------------
# 1) Radio/VTX wording: use physical switch names instead of CH7/CH8.
# ------------------------------------------------------------------
backend = backend.replace('CH7/CH8/VTX', 'SA/SB/VTX')
backend = backend.replace('CH7/CH8 —', 'SA/SB —')
backend = backend.replace('parts.append(f"CH7 {int(round(ch7))} us")', 'parts.append(f"SA {int(round(ch7))} us")')
backend = backend.replace('parts.append(f"CH8 {int(round(ch8))} us")', 'parts.append(f"SB {int(round(ch8))} us")')

# ------------------------------------------------------------------
# 2) ESC alert: only the problem title is bold, not the whole paragraph.
# ------------------------------------------------------------------
old_esc = '''      const text=`🔴 ЙМОВІРНА НЕСПРАВНІСТЬ MOTOR/ESC ${motor}: ${evidence.join('; ')}. Вперше помітно ${phase} (${firstAnomalyTime}), тривалість підтвердженої аномалії ≈ ${firstConfirmed.duration.toFixed(1)} с. Одиничний RPM=0 без стійкості/підтвердження струмом не вважається відмовою.`;\n      alerts.push(`<span class="ai-jump esc-fault-alert-bold" data-jump-time="${firstAnomalyTime}">${text} Можливі причини: двигун, ESC, силове з'єднання або живлення; TLOG не встановлює конкретну фізичну причину. Натисніть, щоб перейти до Timeline.</span>`);'''
new_esc = '''      const escTitle=`🔴 ЙМОВІРНА НЕСПРАВНІСТЬ MOTOR/ESC ${motor}:`;\n      const escDetails=`${evidence.join('; ')}. Вперше помітно ${phase} (${firstAnomalyTime}), тривалість підтвердженої аномалії ≈ ${firstConfirmed.duration.toFixed(1)} с. Одиничний RPM=0 без стійкості/підтвердження струмом не вважається відмовою.`;\n      const text=`${escTitle} ${escDetails}`;\n      alerts.push(`<span class="ai-jump" data-jump-time="${firstAnomalyTime}"><b>${escTitle}</b> ${escDetails} Можливі причини: двигун, ESC, силове з'єднання або живлення; TLOG не встановлює конкретну фізичну причину. Натисніть, щоб перейти до Timeline.</span>`);'''
if old_esc not in html:
    raise SystemExit('ESC alert block not found')
html = html.replace(old_esc, new_esc, 1)
html = html.replace('.esc-fault-alert-bold{font-weight:800}\n', '')

# ------------------------------------------------------------------
# 3) Replace global severity accordion with per-item coloring and
#    dropdowns only for repeated alert types.
# ------------------------------------------------------------------
html = re.sub(
    r'\.attention-summary-item\{.*?\.attention-info \.ai-clickable\{background:rgba\(59,130,246,\.05\)\}\n',
    '',
    html,
    count=1,
    flags=re.S,
)

css_anchor = '.ai-jump{display:inline-block;width:100%;cursor:pointer}'
css = r'''
.vtx-switch-label{color:#60a5fa;font-weight:800}
.ai-list li.alert-critical{border-left:3px solid #ef4444;background:rgba(239,68,68,.07)}
.ai-list li.alert-attention{border-left:3px solid #f97316;background:rgba(249,115,22,.07)}
.ai-list li.alert-warning{border-left:3px solid #eab308;background:rgba(234,179,8,.06)}
.ai-list li.alert-info{border-left:3px solid #3b82f6;background:rgba(59,130,246,.04)}
.repeat-alert-group-item{list-style:none;margin-left:-20px}
.repeat-alert-group{
  border:1px solid var(--border-color);
  border-radius:7px;
  overflow:hidden;
  background:#0f141c;
}
.repeat-alert-group>summary{cursor:pointer;padding:8px 10px;font-weight:800;user-select:none}
.repeat-alert-items{margin:0;padding:5px 10px 8px 30px;line-height:1.45}
.repeat-alert-items li{margin:3px 0;padding:4px 6px;border-radius:5px}
.repeat-critical{border-left:4px solid #ef4444}.repeat-critical>summary{color:#fca5a5}
.repeat-attention{border-left:4px solid #f97316}.repeat-attention>summary{color:#fdba74}
.repeat-warning{border-left:4px solid #eab308}.repeat-warning>summary{color:#fde047}
.repeat-info{border-left:4px solid #3b82f6}.repeat-info>summary{color:#93c5fd}
'''.strip()
if '.repeat-alert-group{' not in html:
    if css_anchor not in html:
        raise SystemExit('AI CSS anchor not found')
    html = html.replace(css_anchor, css_anchor + '\n' + css, 1)

helper_pattern = re.compile(r'function attentionSeverityForAlert\(alertHtml\)\{.*?\nfunction renderResults\(data\)\{', re.S)
helper = r'''function attentionSeverityForAlert(alertHtml){
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
  if(/ВИСОКЕ СПОЖИВАННЯ СТРУМУ/i.test(text))return 'attention';
  if(/EMERGENCY STOP/i.test(text)&&!/не зафіксовано/i.test(text))return 'attention';
  if(/СКИД/i.test(text)&&!/не зафіксовано/i.test(text))return 'attention';
  return 'info';
}

function styleKnownAlertLabels(alertHtml){
  let raw=String(alertHtml||'');
  raw=raw.replace(/SA\/SB\/VTX/g,'@@SA_SB_VTX@@');
  raw=raw.replace(/\bSA\b/g,'<span class="vtx-switch-label">SA</span>');
  raw=raw.replace(/\bSB\b/g,'<span class="vtx-switch-label">SB</span>');
  raw=raw.replace(/@@SA_SB_VTX@@/g,'<span class="vtx-switch-label">SA/SB/VTX</span>');
  return raw;
}

function attentionAlertListItem(alertHtml,severity='info'){
  const raw=styleKnownAlertLabels(alertHtml);
  const explicit=raw.match(/data-jump-time=["']([^"']+)["']/i);
  const plain=raw.replace(/<[^>]+>/g,' ');
  const fallback=plain.match(/-?\d{2}:\d{2}\.\d{3}/);
  const jumpTime=explicit?.[1]||fallback?.[0]||'';
  const classes=[jumpTime?'ai-clickable':'',`alert-${severity}`].filter(Boolean).join(' ');
  return `<li class="${classes}" ${jumpTime?`data-jump-time="${jumpTime}" title="Перейти до рядка Timeline"`:''}>${raw}</li>`;
}

function repeatedAlertKey(alertHtml){
  const raw=String(alertHtml||'');
  const text=raw.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim();
  if(/Potential Thrust Loss/i.test(text))return 'potential-thrust-loss';
  const bold=raw.match(/<b>(.*?)<\/b>/i);
  if(!bold)return null;
  const label=bold[1].replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').replace(/:\s*$/,'').trim().toLowerCase();
  return label||null;
}

function repeatedAlertLabel(alertHtml){
  const raw=String(alertHtml||'');
  const text=raw.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim();
  if(/Potential Thrust Loss/i.test(text))return '⚠️ Potential Thrust Loss';
  const bold=raw.match(/<b>(.*?)<\/b>/i);
  return bold?bold[1].replace(/<[^>]+>/g,' ').replace(/:\s*$/,'').trim():'Повторювані події';
}

function repeatedAlertCountWord(n){
  const n10=n%10,n100=n%100;
  if(n10===1&&n100!==11)return 'подія';
  if(n10>=2&&n10<=4&&(n100<12||n100>14))return 'події';
  return 'подій';
}

function buildRepeatedAlertListHtml(alerts){
  const entries=(Array.isArray(alerts)?alerts:[]).map((alert,index)=>({
    alert,index,key:repeatedAlertKey(alert),severity:attentionSeverityForAlert(alert)
  }));
  const counts={};
  entries.forEach(e=>{if(e.key)counts[e.key]=(counts[e.key]||0)+1;});
  const seen=new Set();
  const rank={info:0,warning:1,attention:2,critical:3};
  const out=[];

  entries.forEach(entry=>{
    if(entry.key&&counts[entry.key]>1){
      if(seen.has(entry.key))return;
      seen.add(entry.key);
      const group=entries.filter(e=>e.key===entry.key);
      if(group.length>1){
        const severity=group.reduce((best,e)=>rank[e.severity]>rank[best]?e.severity:best,'info');
        const children=group.map(e=>attentionAlertListItem(e.alert,e.severity)).join('');
        const label=repeatedAlertLabel(group[0].alert);
        out.push(`<li class="repeat-alert-group-item"><details class="repeat-alert-group repeat-${severity}"><summary>${label} — ${group.length} ${repeatedAlertCountWord(group.length)}</summary><ul class="repeat-alert-items">${children}</ul></details></li>`);
        return;
      }
    }
    out.push(attentionAlertListItem(entry.alert,entry.severity));
  });
  return out.join('');
}

function renderResults(data){'''
if not helper_pattern.search(html):
    raise SystemExit('Old attention helper block not found')
html = helper_pattern.sub(lambda m: helper, html, count=1)

old_render = "document.getElementById('aiAlerts').innerHTML=buildAttentionSummaryHtml(combinedAiAlerts);"
new_render = "document.getElementById('aiAlerts').innerHTML=buildRepeatedAlertListHtml(combinedAiAlerts);"
if old_render not in html:
    raise SystemExit('Old grouped alert render call not found')
html = html.replace(old_render, new_render, 1)

html_path.write_text(html, encoding='utf-8')
backend_path.write_text(backend, encoding='utf-8')
print('Repeat-only alert UI patch applied')
