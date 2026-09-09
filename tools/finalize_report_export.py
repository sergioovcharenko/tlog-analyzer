from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

css_start='/* REPORT_EXPORT_V1 */'
css_end='/* GRAPH ATTITUDE VIEWER */'
if css_start not in s or css_end not in s:
    raise SystemExit('report CSS markers missing')

css='''/* REPORT_EXPORT_V1 */
.report-export{position:relative;display:inline-flex;justify-content:flex-end;margin:0 0 18px;float:right}
#reportButton{height:40px;padding:0 16px;border:1px solid #38bdf8;border-radius:8px;background:#082f49;color:#e0f2fe;font-weight:900;cursor:pointer}
#reportButton:disabled{opacity:.45;cursor:not-allowed}
.report-menu{position:absolute;right:0;top:calc(100% + 6px);z-index:9200;min-width:190px;padding:6px;border:1px solid var(--border-color);border-radius:8px;background:var(--bg-card);box-shadow:0 12px 30px rgba(0,0,0,.35)}
.report-menu[hidden]{display:none!important}
.report-menu button{width:100%;text-align:left;border:0;background:transparent;color:var(--text-main);padding:10px 11px;border-radius:6px;cursor:pointer;font-weight:700}
.report-menu button:hover{background:rgba(56,189,248,.10)}
@media(max-width:760px){.report-menu{position:fixed;left:12px;right:12px;bottom:12px;top:auto;min-width:0}.report-export{float:none;width:100%;justify-content:flex-end}}
'''
pre,sep,rest=s.partition(css_start)
if not sep: raise SystemExit('report CSS start marker missing')
_,sep,post=rest.partition(css_end)
if not sep: raise SystemExit('report CSS end marker missing')
s=pre+css+'\n'+css_end+post

js_start='// REPORT_EXPORT_V1'
js_end='function getVoltageClass(v){'
if js_start not in s or js_end not in s:
    raise SystemExit('report JS markers missing')

js=r'''// REPORT_EXPORT_V1
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
  const source=String(selectedFile?.name||'').replace(/\.tlog$/i,'').replace(/[^a-zA-Z0-9._-]+/g,'-').replace(/^-+|-+$/g,'');
  return `TLOG_Report_${date}${source?`_${source}`:''}`;
}

function escapeReportHtml(value){
  return String(value??'—')
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;')
    .replaceAll("'",'&#39;');
}

function reportArmStateTimes(timeline){
  const rows=Array.isArray(timeline)?timeline:[];
  const arm=rows.find(row=>String(row?.eventType||'').toUpperCase()==='ARM');
  const disarm=[...rows].reverse().find(row=>String(row?.eventType||'').toUpperCase()==='DISARM');
  return {arm:safeReportText(arm?.time),disarm:safeReportText(disarm?.time)};
}

function buildReportModel(data){
  const f=data?.flight||{};
  const b=data?.battery||{};
  const r=data?.radio||{};
  const v=data?.video||{};
  const h=data?.health||{};
  const ai=data?.ai||{};
  const reconstruction=data?.ai_reconstruction||data?.aiReconstruction||{};
  const esc=Array.isArray(h.esc)?h.esc:[];
  const vtx=summarizeVtxFrequencySelectionsAllDbm(data?.timeline,v?.frequencyDbmStats);
  const board=Array.isArray(data?.board_messages)?data.board_messages:(Array.isArray(data?.boardMessages)?data.boardMessages:[]);
  const engine=summarizeEngineLoad(data?.timeline);
  const graph=data?.graph_data||{};
  const armState=reportArmStateTimes(data?.timeline);
  const radioDbm=Array.isArray(graph.radio_dbm)?graph.radio_dbm:[];
  const linkLostSamples=radioDbm.reduce((n,x)=>n+(Number(x)===-128?1:0),0);
  const safe={
    title:'AI — TLOG Analyzer',
    subtitle:'Звіт аналізу польоту',
    sourceFile:safeReportText(selectedFile?.name),
    generatedAt:new Date().toLocaleString('uk-UA'),
    flight:{
      duration:safeReportText(f.durationText),
      modes:safeReportText(f.modes),
      armTime:armState.arm,
      disarmTime:armState.disarm,
      maxAltitude:reportNumber(f.maxAltitude,1,'м'),
      maxDistance:reportNumber(f.maxDistance,1,'м'),
      totalDistance:reportNumber(f.totalDistance,1,'м')
    },
    battery:{
      armVoltage:reportNumber(b.armVoltage,2,'V'),
      minVoltage:reportNumber(b.minVoltage,2,'V'),
      voltageSag:reportNumber(b.voltageSag,2,'V'),
      maxCurrent:reportNumber(b.maxCurrent,1,'A')
    },
    radio:{
      minRssi:safeReportText(r.rssi),
      avgDbm:reportNumber(r.avgDbm,1,'dBm'),
      worstDbm:reportNumber(r.worstDbm,0,'dBm'),
      dbmSampleCount:Number.isFinite(+r.dbmSampleCount)?+r.dbmSampleCount:0,
      linkLostSamples
    },
    health:{
      fcTemp:safeReportText(h.maxTemp),
      escMax:esc.map(e=>Number.isFinite(+e?.maxTemp)?+e.maxTemp:null),
      engineLoad:engine?engine.avg:null,
      engineLoadMin:engine?engine.min:null,
      engineLoadMax:engine?engine.max:null,
      engineLoadSamples:engine?engine.samples:0
    },
    vtx,
    boardMessages:board,
    ai,
    reconstruction
  };
  delete safe.plotToken;
  delete safe._mavlinkPlotPromise;
  return safe;
}

function reportMetric(label,value){
  return `<div class="metric"><span>${escapeReportHtml(label)}</span><b>${escapeReportHtml(value)}</b></div>`;
}

function reportListHtml(value){
  const arr=Array.isArray(value)?value:(value&&typeof value==='object'?Object.values(value):value?[value]:[]);
  return arr.filter(x=>x!==null&&x!==undefined&&x!=='').map(item=>{
    if(typeof item==='string')return `<li>${escapeReportHtml(item)}</li>`;
    return `<li>${escapeReportHtml(item?.text??item?.message??item?.analysisText??'—')}</li>`;
  }).join('');
}

function reportBoardMessages(model){
  const severityClass=s=>{
    const v=String(s||'').toLowerCase();
    if(v==='error'||v==='critical')return 'critical';
    if(v==='warning'||v==='warn')return 'warning';
    return 'info';
  };
  const rows=(Array.isArray(model?.boardMessages)?model.boardMessages:[]).map((row,index)=>({row,index}));
  rows.sort((a,b)=>{
    const at=Number(a.row?.time_ms),bt=Number(b.row?.time_ms);
    if(Number.isFinite(at)&&Number.isFinite(bt))return at-bt;
    if(Number.isFinite(at))return -1;
    if(Number.isFinite(bt))return 1;
    return a.index-b.index;
  });
  if(!rows.length)return '<tr><td colspan="4">—</td></tr>';
  return rows.map(({row})=>{
    const severity=row?.severity??row?.level??'info';
    const raw=row?.text??row?.message??row?.systemText??row?.system_text??'—';
    const explanation=row?.analysisText??row?.analysis??row?.explanation??'';
    return `<tr class="event-row event-${severityClass(severity)}"><td>${escapeReportHtml(row?.time??row?.timeText??'—')}</td><td>${escapeReportHtml(severity)}</td><td>${escapeReportHtml(raw)}</td><td>${explanation?escapeReportHtml(explanation):'—'}</td></tr>`;
  }).join('');
}

const REPORT_VTX_MATRIX={
  'K1':[5180,5520,5700],
  'K2':[5240,5580,5765],
  'K3':[5300,5640,5825],
};

function reportVtxMatrix(model){
  const items=new Map((model?.vtx?.frequencies||[]).map(item=>[Number(item.frequency),item]));
  const best=Number(model?.vtx?.stableFrequency);
  const worst=Number(model?.vtx?.worstFrequency);
  return Object.entries(REPORT_VTX_MATRIX).map(([k,freqs])=>`<tr><th>${k}</th>${freqs.map(freq=>{
    const item=items.get(freq)||{};
    const avg=Number.isFinite(+item.avgDbm)?`${(+item.avgDbm).toFixed(1)} dBm`:'dBm —';
    const samples=Number.isFinite(+item.dbmSamples)?+item.dbmSamples:0;
    const switches=Number.isFinite(+item.switches)?+item.switches:0;
    const cls=freq===best?'vtx-best':(freq===worst?'vtx-worst':'');
    return `<td class="${cls}"><b>${freq} — ${switches}</b><small>${escapeReportHtml(avg)} • ${samples} відліків</small></td>`;
  }).join('')}</tr>`).join('');
}

function reportAiConclusion(model){
  const recon=model?.reconstruction||{};
  const ai=model?.ai||{};
  // Preserve existing "Gyros inconsistent" finding text when it is already present in AI/board analysis.
  const sections=[];
  const scenario=recon.dominant_scenario??recon.dominantScenario;
  if(scenario)sections.push(reportMetric('Сценарій',safeReportText(scenario)));
  const blocks=[
    ['Що сталося',recon.what_happened??recon.whatHappened??ai.findings],
    ['Ймовірна послідовність',recon.likely_sequence??recon.likelySequence],
    ['Дії пілота',recon.pilot_actions??recon.pilotActions],
    ['Можливі альтернативи',recon.possible_alternatives??recon.possibleAlternatives],
    ['Докази',recon.evidence],
  ];
  blocks.forEach(([title,value])=>{const body=reportListHtml(value);if(body)sections.push(`<h3>${escapeReportHtml(title)}</h3><ul>${body}</ul>`);});
  if(recon.confidence)sections.push(reportMetric('Confidence',safeReportText(recon.confidence)));
  return sections.length?sections.join(''):'<div class="muted">AI-висновок у цьому аналізі відсутній.</div>';
}

function buildReportHtml(data,chartImages={}){
  const model=buildReportModel(data);
  const chartHtml=Object.entries(chartImages||{})
    .filter(([,src])=>typeof src==='string'&&src.startsWith('data:image/'))
    .map(([name,src])=>`<div class="chart"><h3>${escapeReportHtml(name)}</h3><img class="chart-image" src="${src}" alt="${escapeReportHtml(name)}"></div>`).join('');
  const engine=model.health.engineLoad===null?'—':`${model.health.engineLoad.toFixed(1)} %`;
  return `<!DOCTYPE html><html lang="uk"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeReportHtml(reportFileBaseName())}</title><style>
  body{margin:0;background:#eef2f7;color:#111827;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1050px;margin:auto;padding:28px}.head,.section{background:#fff;border:1px solid #dbe2ea;border-radius:12px;padding:18px;margin-bottom:14px}.head h1{margin:0 0 3px;font-size:23px}.muted{color:#64748b;font-size:12px}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:9px}.metric{border:1px solid #e2e8f0;border-radius:8px;padding:10px}.metric span{display:block;color:#64748b;font-size:10px;text-transform:uppercase}.metric b{font-size:17px}.vtx{width:100%;border-collapse:collapse}.vtx th,.vtx td,.events th,.events td{border:1px solid #e2e8f0;padding:8px;text-align:left}.vtx td small{display:block;color:#64748b}.vtx-best{background:#dcfce7}.vtx-worst{background:#fee2e2}.events{width:100%;border-collapse:collapse;font-size:12px}.event-critical{background:#fef2f2}.event-warning{background:#fffbeb}.chart img{width:100%;max-height:320px;object-fit:contain}.chart{break-inside:avoid;margin-top:12px}.section h2{margin:0 0 12px;font-size:17px}.section ul{margin:6px 0 0;padding-left:20px}@media print{body{background:#fff!important;color:#111!important}.report-actions{display:none!important}.section,.metric,.event-row,.chart{break-inside:avoid}@page{size:auto;margin:12mm}.wrap{padding:0}.head,.section{box-shadow:none}}
  </style></head><body><div class="wrap"><div class="head"><h1>${escapeReportHtml(model.title)}</h1><div><b>${escapeReportHtml(model.subtitle)}</b></div><div class="muted">${escapeReportHtml(model.sourceFile)} • ${escapeReportHtml(model.generatedAt)} • ${escapeReportHtml(model.flight.duration)}</div></div>
  <div class="section"><h2>Основні показники</h2><div class="metrics">${reportMetric('Тривалість',model.flight.duration)}${reportMetric('ARM',model.flight.armTime)}${reportMetric('DISARM',model.flight.disarmTime)}${reportMetric('Режими',model.flight.modes)}${reportMetric('MAX ALT',model.flight.maxAltitude)}${reportMetric('MAX дальність',model.flight.maxDistance)}${reportMetric('Дистанція',model.flight.totalDistance)}${reportMetric('ARM Voltage',model.battery.armVoltage)}${reportMetric('MIN Voltage',model.battery.minVoltage)}${reportMetric('Просадка',model.battery.voltageSag)}${reportMetric('MAX Current',model.battery.maxCurrent)}${reportMetric('FC Temp',model.health.fcTemp)}${reportMetric('Engine Load AVG',engine)}</div></div>
  <div class="section"><h2>Зв’язок</h2><div class="metrics">${reportMetric('MIN RSSI',model.radio.minRssi)}${reportMetric('AVG dBm',model.radio.avgDbm)}${reportMetric('Worst dBm',model.radio.worstDbm)}${reportMetric('dBm samples',model.radio.dbmSampleCount)}${reportMetric('-128 dBm',model.radio.linkLostSamples)}</div></div>
  <div class="section"><h2>VTX</h2><table class="vtx"><thead><tr><th></th><th>5.2 GHz</th><th>5.5 GHz</th><th>5.8 GHz</th></tr></thead><tbody>${reportVtxMatrix(model)}</tbody></table></div>
  <div class="section"><h2>Критичні події</h2><table class="events"><thead><tr><th>Час</th><th>Рівень</th><th>Повідомлення</th><th>Пояснення</th></tr></thead><tbody>${reportBoardMessages(model)}</tbody></table></div>
  <div class="section"><h2>AI-висновок</h2>${reportAiConclusion(model)}</div>
  ${chartHtml?`<div class="section"><h2>Графіки</h2>${chartHtml}</div>`:''}</div></body></html>`;
}

function renderReportChart(title,series,width=1000,height=320){
  const clean=(Array.isArray(series)?series:[]).map(item=>({
    label:safeReportText(item?.label),
    points:(Array.isArray(item?.points)?item.points:[]).map(p=>({x:Number(p?.x),y:Number(p?.y)})).filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y))
  })).filter(item=>item.points.length);
  if(!clean.length)return null;
  const all=clean.flatMap(item=>item.points);
  let minX=Math.min(...all.map(p=>p.x)),maxX=Math.max(...all.map(p=>p.x));
  let minY=Math.min(...all.map(p=>p.y)),maxY=Math.max(...all.map(p=>p.y));
  if(minX===maxX){minX-=1;maxX+=1}if(minY===maxY){minY-=1;maxY+=1}
  const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;const c=canvas.getContext('2d');if(!c)return null;
  c.fillStyle='#fff';c.fillRect(0,0,width,height);c.fillStyle='#111827';c.font='bold 20px sans-serif';c.fillText(title,20,28);
  const left=58,right=20,top=44,bottom=34,w=width-left-right,h=height-top-bottom;
  c.strokeStyle='#e2e8f0';c.lineWidth=1;for(let i=0;i<=5;i++){const y=top+h*i/5;c.beginPath();c.moveTo(left,y);c.lineTo(left+w,y);c.stroke()}
  c.strokeStyle='#94a3b8';c.strokeRect(left,top,w,h);
  const palette=['#2563eb','#dc2626','#16a34a','#d97706','#7c3aed'];
  clean.forEach((item,idx)=>{c.beginPath();c.strokeStyle=palette[idx%palette.length];c.lineWidth=2;item.points.forEach((p,i)=>{const x=left+(p.x-minX)/(maxX-minX)*w;const y=top+(1-(p.y-minY)/(maxY-minY))*h;if(i===0)c.moveTo(x,y);else c.lineTo(x,y)});c.stroke();c.fillStyle=palette[idx%palette.length];c.font='13px sans-serif';c.fillText(item.label,left+idx*170,height-10)});
  return canvas.toDataURL('image/png');
}

function reportSeriesFromGraph(graph,timeKey,valueKey,label){
  const times=Array.isArray(graph?.[timeKey])?graph[timeKey]:[];
  const values=Array.isArray(graph?.[valueKey])?graph[valueKey]:[];
  const points=[];for(let i=0;i<Math.min(times.length,values.length);i++){const x=Number(times[i]),y=Number(values[i]);if(Number.isFinite(x)&&Number.isFinite(y))points.push({x,y});}
  return {label,points};
}

function buildReportChartImages(data){
  const graph=data?.graph_data||{};
  const images={};
  const add=(name,series)=>{const image=renderReportChart(name,series);if(image)images[name]=image;};
  add('Висота',[reportSeriesFromGraph(graph,'altitude_time_ms','altitude_m','Висота')]);
  add('Батарея',[reportSeriesFromGraph(graph,'voltage_time_ms','voltage_v','Напруга'),reportSeriesFromGraph(graph,'current_time_ms','current_a','Струм')]);
  add('Зв’язок',[reportSeriesFromGraph(graph,'radio_time_ms','radio_dbm','dBm'),reportSeriesFromGraph(graph,'rssi_time_ms','rssi_pct','RSSI')]);
  add('Engine Load',[reportSeriesFromGraph(graph,'engine_load_time_ms','engine_load_pct','Engine Load')]);
  // Vibration time-series are not currently present in graph_data; per report spec, omit that chart rather than inventing samples from max-only health values.
  return images;
}

async function getCurrentReportHtml(){
  const data=window.__lastAnalysisResult;
  if(!data)throw new Error('Спочатку виконай аналіз TLOG.');
  const charts=buildReportChartImages(data);
  return buildReportHtml(data,charts);
}

async function createReportBlob(){
  const html=await getCurrentReportHtml();
  return new Blob([html],{type:'text/html;charset=utf-8'});
}

async function downloadReportHtml(){
  const blob=await createReportBlob();
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download=reportFileBaseName()+'.html';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);
}

async function openReportForPrint(){
  const printWindow=window.open('','_blank');
  if(!printWindow)throw new Error('Не вдалося відкрити вікно друку. Дозволь спливаючі вікна або збережи HTML.');
  try{
    const html=await getCurrentReportHtml();
    printWindow.document.open();printWindow.document.write(html);printWindow.document.close();
    await new Promise(resolve=>{if(printWindow.document.readyState==='complete')resolve();else printWindow.addEventListener('load',resolve,{once:true});});
    printWindow.focus();printWindow.print();
  }catch(e){try{printWindow.close();}catch(_){ }throw e;}
}

async function shareReport(){
  const blob=await createReportBlob();
  const file=new File([blob],`${reportFileBaseName()}.html`,{type:'text/html'});
  if(navigator.share&&navigator.canShare?.({files:[file]})){
    await navigator.share({title:'AI — TLOG Analyzer',text:'Звіт аналізу польоту',files:[file]});return;
  }
  if(navigator.share){await navigator.share({title:'AI — TLOG Analyzer',text:'Звіт аналізу польоту'});return;}
  await downloadReportHtml();
  throw new Error('Пряме системне поширення не підтримується цим браузером. HTML-звіт збережено.');
}

function showReportError(error){
  if(error?.name==='AbortError')return;
  UI.error.textContent='❌ '+(error?.message||error);
  UI.error.style.display='block';
}

function wireReportExportControls(){
  const main=document.getElementById('reportButton'),menu=document.getElementById('reportMenu');if(!main||!menu)return;
  if(main.dataset.wired==='1')return;main.dataset.wired='1';
  main.addEventListener('click',e=>{e.stopPropagation();if(!main.disabled)menu.hidden=!menu.hidden;});
  const bind=(id,action)=>document.getElementById(id)?.addEventListener('click',async()=>{closeReportMenu();try{await action();}catch(e){showReportError(e);}});
  bind('reportHtmlButton',downloadReportHtml);
  bind('reportPdfButton',openReportForPrint);
  bind('reportPrintButton',openReportForPrint);
  bind('reportShareButton',shareReport);
  document.addEventListener('click',e=>{if(!document.getElementById('reportExport')?.contains(e.target))closeReportMenu();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeReportMenu();});
}
setTimeout(wireReportExportControls,0);
'''
pre,sep,rest=s.partition(js_start)
if not sep: raise SystemExit('report JS start marker missing')
_,sep,post=rest.partition(js_end)
if not sep: raise SystemExit('report JS end marker missing')
s=pre+js+'\n'+js_end+post

p.write_text(s,encoding='utf-8')
print('report export finalized')
