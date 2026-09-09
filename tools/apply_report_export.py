from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

CSS='''
/* REPORT_EXPORT_V1 */
.report-export{position:relative;display:flex;justify-content:flex-end;margin:0 0 18px}
#reportButton{height:40px;padding:0 16px;border:1px solid #38bdf8;border-radius:8px;background:#082f49;color:#e0f2fe;font-weight:900;cursor:pointer}
#reportButton:disabled{opacity:.45;cursor:not-allowed}
.report-menu{position:absolute;right:0;top:46px;z-index:4000;min-width:190px;padding:6px;border:1px solid var(--border-color);border-radius:8px;background:var(--bg-card);box-shadow:0 12px 30px rgba(0,0,0,.35)}
.report-menu[hidden]{display:none!important}
.report-menu button{width:100%;text-align:left;border:0;background:transparent;color:var(--text-main);padding:10px 11px;border-radius:6px;cursor:pointer;font-weight:700}
.report-menu button:hover{background:rgba(56,189,248,.10)}
'''
if '/* REPORT_EXPORT_V1 */' not in s:
    anchor='/* GRAPH ATTITUDE VIEWER */'
    if anchor not in s: raise SystemExit('CSS anchor missing')
    s=s.replace(anchor,CSS+'\n'+anchor,1)

CONTROLS='''
<div class="report-export" id="reportExport">
  <button id="reportButton" type="button" disabled>📄 ЗВІТ</button>
  <div id="reportMenu" class="report-menu" hidden>
    <button id="reportPdfButton" type="button">Зберегти PDF</button>
    <button id="reportHtmlButton" type="button">Зберегти HTML</button>
    <button id="reportShareButton" type="button">Поділитися</button>
    <button id="reportPrintButton" type="button">Друк</button>
  </div>
</div>
'''
if 'id="reportButton"' not in s:
    anchor='<div class="results" id="results">'
    if anchor not in s: raise SystemExit('results anchor missing')
    s=s.replace(anchor,anchor+'\n'+CONTROLS,1)

JS='''
// REPORT_EXPORT_V1
function closeReportMenu(){
  const menu=document.getElementById('reportMenu');
  if(menu)menu.hidden=true;
}

function setReportControlsEnabled(enabled){
  const button=document.getElementById('reportButton');
  if(!button)return;
  button.disabled=!enabled;
  if(!enabled)closeReportMenu();
}

function safeReportText(value){
  if(value===null||value===undefined)return '—';
  const text=String(value).trim();
  return text&&text!=='null'&&text!=='undefined'?text:'—';
}

function reportNumber(value,digits=1,unit=''){
  const n=Number(value);
  return Number.isFinite(n)?`${n.toFixed(digits)}${unit?` ${unit}`:''}`:'—';
}

function reportFileBaseName(){
  const stamp=new Date();
  const pad=n=>String(n).padStart(2,'0');
  const date=`${stamp.getFullYear()}-${pad(stamp.getMonth()+1)}-${pad(stamp.getDate())}_${pad(stamp.getHours())}-${pad(stamp.getMinutes())}`;
  const source=String(selectedFile?.name||'').replace(/\\.tlog$/i,'').replace(/[^a-zA-Z0-9._-]+/g,'-').replace(/^-+|-+$/g,'');
  return `TLOG_Report_${date}${source?`_${source}`:''}`;
}

function escapeReportHtml(value){
  return String(value??'—').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
}

function buildReportModel(data){
  const f=data?.flight||{};
  const b=data?.battery||{};
  const r=data?.radio||{};
  const v=data?.video||{};
  const h=data?.health||{};
  const ai=data?.ai||{};
  const recon=data?.ai_reconstruction||data?.aiReconstruction||{};
  const esc=Array.isArray(h.esc)?h.esc:[];
  const vtx=summarizeVtxFrequencySelectionsAllDbm(data?.timeline,v?.frequencyDbmStats);
  const board=Array.isArray(data?.board_messages)?data.board_messages:(Array.isArray(data?.boardMessages)?data.boardMessages:[]);
  const safe={
    title:'AI — TLOG Analyzer',subtitle:'Звіт аналізу польоту',sourceFile:safeReportText(selectedFile?.name),generatedAt:new Date().toLocaleString('uk-UA'),
    flight:{duration:safeReportText(f.durationText),modes:safeReportText(f.modes),maxAltitude:reportNumber(f.maxAltitude,1,'м'),maxDistanceHome:reportNumber(f.maxDistanceFromHome??f.maxDistanceHome,1,'м'),totalDistance:reportNumber(f.totalDistance,1,'м')},
    battery:{armVoltage:reportNumber(b.armVoltage,2,'V'),minVoltage:reportNumber(b.minVoltage,2,'V'),voltageSag:reportNumber(b.voltageSag,2,'V'),maxCurrent:reportNumber(b.maxCurrent,1,'A')},
    radio:{minRssi:safeReportText(r.minRssi??r.rssi),avgDbm:reportNumber(r.avgDbm,1,'dBm'),worstDbm:reportNumber(r.worstDbm,0,'dBm'),dbmSampleCount:Number.isFinite(+r.dbmSampleCount)?+r.dbmSampleCount:0},
    health:{fcTemp:safeReportText(h.maxTemp),escMax:esc.map(e=>Number.isFinite(+e?.maxTemp)?+e.maxTemp:null),engineLoad:Number.isFinite(+h.engineLoadAvg)?+h.engineLoadAvg:null},
    vtx,boardMessages:board,ai,reconstruction:recon
  };
  delete safe.plotToken;
  delete safe._mavlinkPlotPromise;
  return safe;
}

function reportMetric(label,value){return `<div class="metric"><span>${escapeReportHtml(label)}</span><b>${escapeReportHtml(value)}</b></div>`;}
function reportList(value){
  const arr=Array.isArray(value)?value:(value&&typeof value==='object'?Object.values(value):value?[value]:[]);
  return arr.filter(Boolean).map(x=>`<li>${escapeReportHtml(typeof x==='string'?x:(x?.text??x?.message??JSON.stringify(x)))}</li>`).join('');
}
function reportBoardRows(board){
  return (Array.isArray(board)?board:[]).map(row=>`<tr><td>${escapeReportHtml(row?.time??row?.timeText??'—')}</td><td>${escapeReportHtml(row?.severity??row?.level??'—')}</td><td>${escapeReportHtml(row?.text??row?.message??row?.systemText??'—')}</td></tr>`).join('');
}
function reportVtxMatrix(vtx){
  const items=new Map((vtx?.frequencies||[]).map(x=>[Number(x.frequency),x]));
  const rows=[[5180,5520,5700],[5240,5580,5765],[5300,5640,5825]];
  return rows.map((freqs,i)=>`<tr><th>K${i+1}</th>${freqs.map(freq=>{const x=items.get(freq)||{};const avg=Number.isFinite(+x.avgDbm)?`${(+x.avgDbm).toFixed(1)} dBm`:'dBm —';return `<td><b>${freq} — ${Number.isFinite(+x.switches)?+x.switches:0}</b><small>${escapeReportHtml(avg)}</small></td>`}).join('')}</tr>`).join('');
}

function buildReportHtml(data,chartImages={}){
  const m=buildReportModel(data);
  const recon=m.reconstruction||{};
  const ai=m.ai||{};
  const charts=Object.entries(chartImages||{}).filter(([,src])=>typeof src==='string'&&src.startsWith('data:image/')).map(([name,src])=>`<div class="chart"><h3>${escapeReportHtml(name)}</h3><img src="${src}" alt="${escapeReportHtml(name)}"></div>`).join('');
  return `<!DOCTYPE html><html lang="uk"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeReportHtml(reportFileBaseName())}</title><style>
  body{margin:0;background:#eef2f7;color:#111827;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1050px;margin:auto;padding:28px}.head,.section{background:#fff;border:1px solid #dbe2ea;border-radius:12px;padding:18px;margin-bottom:14px}.head h1{margin:0 0 3px;font-size:23px}.muted{color:#64748b;font-size:12px}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:9px}.metric{border:1px solid #e2e8f0;border-radius:8px;padding:10px}.metric span{display:block;color:#64748b;font-size:10px;text-transform:uppercase}.metric b{font-size:17px}.vtx{width:100%;border-collapse:collapse}.vtx th,.vtx td,table.events th,table.events td{border:1px solid #e2e8f0;padding:8px;text-align:left}.vtx td small{display:block;color:#64748b}.events{width:100%;border-collapse:collapse;font-size:12px}.chart img{width:100%;max-height:320px;object-fit:contain}.chart{break-inside:avoid;margin-top:12px}.section h2{margin:0 0 12px;font-size:17px}.section ul{margin:6px 0 0;padding-left:20px}@media print{body{background:#fff!important;color:#111!important}.report-actions{display:none!important}.section,.metric,.event-row,.chart{break-inside:avoid}@page{size:auto;margin:12mm}.wrap{padding:0}.head,.section{box-shadow:none}}
  </style></head><body><div class="wrap"><div class="head"><h1>${escapeReportHtml(m.title)}</h1><div><b>${escapeReportHtml(m.subtitle)}</b></div><div class="muted">${escapeReportHtml(m.sourceFile)} • ${escapeReportHtml(m.generatedAt)} • ${escapeReportHtml(m.flight.duration)}</div></div>
  <div class="section"><h2>Основні показники</h2><div class="metrics">${reportMetric('Тривалість',m.flight.duration)}${reportMetric('Режими',m.flight.modes)}${reportMetric('MAX ALT',m.flight.maxAltitude)}${reportMetric('MAX від дому',m.flight.maxDistanceHome)}${reportMetric('Дистанція',m.flight.totalDistance)}${reportMetric('ARM Voltage',m.battery.armVoltage)}${reportMetric('MIN Voltage',m.battery.minVoltage)}${reportMetric('Просадка',m.battery.voltageSag)}${reportMetric('MAX Current',m.battery.maxCurrent)}${reportMetric('FC Temp',m.health.fcTemp)}${reportMetric('Engine Load',m.health.engineLoad===null?'—':`${m.health.engineLoad.toFixed(1)} %`)}</div></div>
  <div class="section"><h2>Зв’язок</h2><div class="metrics">${reportMetric('RSSI MIN',m.radio.minRssi)}${reportMetric('AVG dBm',m.radio.avgDbm)}${reportMetric('Worst dBm',m.radio.worstDbm)}${reportMetric('dBm samples',m.radio.dbmSampleCount)}</div></div>
  <div class="section"><h2>VTX</h2><table class="vtx"><thead><tr><th></th><th>5.2 GHz</th><th>5.5 GHz</th><th>5.8 GHz</th></tr></thead><tbody>${reportVtxMatrix(m.vtx)}</tbody></table></div>
  <div class="section"><h2>Критичні події</h2><table class="events"><thead><tr><th>Час</th><th>Рівень</th><th>Повідомлення</th></tr></thead><tbody>${reportBoardRows(m.boardMessages)||'<tr><td colspan="3">—</td></tr>'}</tbody></table></div>
  <div class="section"><h2>AI-висновок</h2>${reportMetric('Сценарій',safeReportText(recon.dominant_scenario??recon.dominantScenario))}<h3>Що сталося</h3><ul>${reportList(recon.what_happened??recon.whatHappened??ai.findings)}</ul><h3>Ймовірна послідовність</h3><ul>${reportList(recon.likely_sequence??recon.likelySequence)}</ul><h3>Дії пілота</h3><ul>${reportList(recon.pilot_actions??recon.pilotActions)}</ul><h3>Можливі альтернативи</h3><ul>${reportList(recon.possible_alternatives??recon.possibleAlternatives)}</ul><h3>Докази</h3><ul>${reportList(recon.evidence)}</ul>${reportMetric('Confidence',safeReportText(recon.confidence))}</div>
  ${charts?`<div class="section"><h2>Графіки</h2>${charts}</div>`:''}</div></body></html>`;
}

function drawReportSeries(title,times,series){
  const usable=(Array.isArray(series)?series:[]).filter(s=>Array.isArray(s?.values)&&s.values.some(v=>Number.isFinite(+v)));
  if(!usable.length)return null;
  const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=360;const c=canvas.getContext('2d');if(!c)return null;
  c.fillStyle='#fff';c.fillRect(0,0,canvas.width,canvas.height);c.fillStyle='#111827';c.font='bold 22px sans-serif';c.fillText(title,22,30);
  const vals=usable.flatMap(s=>s.values.map(Number).filter(Number.isFinite));let min=Math.min(...vals),max=Math.max(...vals);if(min===max){min-=1;max+=1}
  const left=55,right=20,top=48,bottom=35,w=canvas.width-left-right,h=canvas.height-top-bottom;c.strokeStyle='#cbd5e1';c.strokeRect(left,top,w,h);
  const palette=['#2563eb','#dc2626','#16a34a','#d97706','#7c3aed'];
  usable.forEach((s,si)=>{const v=s.values.map(x=>Number.isFinite(+x)?+x:null);c.beginPath();c.strokeStyle=palette[si%palette.length];c.lineWidth=2;let started=false;v.forEach((x,i)=>{if(x===null)return;const px=left+(v.length<=1?0:(i/(v.length-1))*w),py=top+(1-(x-min)/(max-min))*h;if(!started){c.moveTo(px,py);started=true}else c.lineTo(px,py)});c.stroke();c.fillStyle=palette[si%palette.length];c.font='14px sans-serif';c.fillText(s.label||`Series ${si+1}`,left+si*180,canvas.height-10)});
  return canvas.toDataURL('image/png');
}

function buildReportChartImages(data){
  const t=data?.telemetry||data?.graph||data?.mavlink_plot||{};
  const images={};
  const add=(name,times,series)=>{const img=drawReportSeries(name,times,series);if(img)images[name]=img;};
  add('Висота',t.alt_time_ms||t.time_ms,[{label:'Altitude',values:t.altitude||t.relative_alt||[]}]);
  add('Батарея',t.battery_time_ms||t.time_ms,[{label:'Voltage',values:t.voltage||[]},{label:'Current',values:t.current||[]}]);
  add('Зв’язок',t.radio_time_ms||t.time_ms,[{label:'dBm',values:t.radio_dbm||[]},{label:'RSSI',values:t.rssi_pct||[]}]);
  add('Вібрації',t.vibration_time_ms||t.time_ms,[{label:'X',values:t.vib_x||[]},{label:'Y',values:t.vib_y||[]},{label:'Z',values:t.vib_z||[]}]);
  add('Engine Load',t.engine_load_time_ms||t.time_ms,[{label:'Engine Load',values:t.engine_load||[]}]);
  return images;
}

function downloadReportHtml(){
  const data=window.__lastAnalysisResult;if(!data)return;
  const html=buildReportHtml(data,buildReportChartImages(data));const blob=new Blob([html],{type:'text/html;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=reportFileBaseName()+'.html';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);closeReportMenu();
}
function openReportPrint(){
  const data=window.__lastAnalysisResult;if(!data)return;
  const html=buildReportHtml(data,buildReportChartImages(data));const w=window.open('','_blank');if(!w){alert('Браузер заблокував вікно звіту. Дозволь спливаючі вікна або збережи HTML.');return;}w.document.open();w.document.write(html);w.document.close();w.addEventListener('load',()=>setTimeout(()=>w.print(),200),{once:true});closeReportMenu();
}
async function shareReport(){
  const data=window.__lastAnalysisResult;if(!data)return;
  const html=buildReportHtml(data,buildReportChartImages(data));const blob=new Blob([html],{type:'text/html;charset=utf-8'});const file=new File([blob],reportFileBaseName()+'.html',{type:'text/html'});
  try{if(navigator.share&&navigator.canShare&&navigator.canShare({files:[file]})){await navigator.share({title:'TLOG Analyzer — звіт',files:[file]});}
    else if(navigator.share){await navigator.share({title:'TLOG Analyzer — звіт',text:'Звіт аналізу TLOG. HTML-файл можна зберегти окремо.'});}
    else{downloadReportHtml();alert('Пряме системне поширення не підтримується цим браузером. HTML-звіт збережено.');}}
  catch(e){if(e?.name!=='AbortError')alert('Не вдалося поділитися звітом: '+(e?.message||e));}finally{closeReportMenu();}
}

function wireReportExportControls(){
  const main=document.getElementById('reportButton'),menu=document.getElementById('reportMenu');if(!main||!menu)return;
  if(main.dataset.wired==='1')return;main.dataset.wired='1';
  main.addEventListener('click',e=>{e.stopPropagation();if(!main.disabled)menu.hidden=!menu.hidden;});
  document.getElementById('reportHtmlButton')?.addEventListener('click',downloadReportHtml);
  document.getElementById('reportPdfButton')?.addEventListener('click',openReportPrint);
  document.getElementById('reportPrintButton')?.addEventListener('click',openReportPrint);
  document.getElementById('reportShareButton')?.addEventListener('click',shareReport);
  document.addEventListener('click',e=>{if(!document.getElementById('reportExport')?.contains(e.target))closeReportMenu();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeReportMenu();});
}
setTimeout(wireReportExportControls,0);
'''
if '// REPORT_EXPORT_V1' not in s:
    anchor='function getVoltageClass(v){'
    if anchor not in s: raise SystemExit('JS anchor missing')
    s=s.replace(anchor,JS+'\n'+anchor,1)

# Ensure report state resets with form.
reset_marker='window.__lastAnalysisResult=null;'
if reset_marker in s and 'window.__lastAnalysisResult=null;\n  setReportControlsEnabled(false);' not in s:
    s=s.replace(reset_marker,reset_marker+'\n  setReportControlsEnabled(false);',1)

# Ensure successful render enables report controls.
render_marker='function renderResults(data){'
if render_marker in s and 'function renderResults(data){\n  window.__lastAnalysisResult=data;\n  setReportControlsEnabled(true);' not in s:
    s=s.replace(render_marker,render_marker+'\n  window.__lastAnalysisResult=data;\n  setReportControlsEnabled(true);',1)

p.write_text(s,encoding='utf-8')
print('report export patch applied')
