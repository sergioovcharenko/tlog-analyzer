from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "index.html"
MARKER = "/* DASHBOARD_LAYOUT_V2 */"

html = PATH.read_text(encoding="utf-8")
if MARKER in html:
    print("dashboard layout v2 already applied")
    raise SystemExit(0)


def require_replace(source: str, old: str, new: str, label: str, count: int = 1) -> str:
    found = source.count(old)
    if found < count:
        raise SystemExit(f"anchor not found for {label}: expected >= {count}, got {found}")
    return source.replace(old, new, count)

# Theme tokens in existing root block.
root_anchor = "  --video:#f59e0b;\n}"
root_replacement = """  --video:#f59e0b;
  --panel-bg:#121820;
  --panel-bg-2:#0f141c;
  --input-bg:#0d131a;
  --graph-bg:#0b1017;
  --graph-grid:rgba(148,163,184,.14);
  --shadow-color:rgba(0,0,0,.28);
}
"""
html = require_replace(html, root_anchor, root_replacement, "root theme tokens")

css = r'''

/* DASHBOARD_LAYOUT_V2 */
[data-tlog-theme="light"]{
  --bg-main:#eef3f8;
  --bg-card:#ffffff;
  --bg-header:#f8fafc;
  --panel-bg:#ffffff;
  --panel-bg-2:#f1f5f9;
  --input-bg:#ffffff;
  --border-color:#cbd5e1;
  --border-highlight:#94a3b8;
  --text-main:#0f172a;
  --text-muted:#475569;
  --graph-bg:#ffffff;
  --graph-grid:rgba(51,65,85,.16);
  --shadow-color:rgba(15,23,42,.10);
}
html,body{max-width:100%;overflow-x:hidden}
#graphViewerOverlay{background:var(--bg-main)!important;color:var(--text-main)!important}
.graph-viewer-shell{max-width:1760px!important}
.graph-viewer-toolbar{background:var(--panel-bg)!important;border-color:var(--border-color)!important;box-shadow:0 8px 24px var(--shadow-color)}
.graph-viewer-toolbar button,.graph-viewer-toolbar select{background:var(--input-bg)!important;color:var(--text-main)!important;border-color:var(--border-highlight)!important}
.graph-viewer-title{color:var(--text-main)!important}
.tlog-theme-switch{display:inline-flex;gap:3px;padding:3px;border:1px solid var(--border-color);border-radius:8px;background:var(--panel-bg-2)}
.tlog-theme-switch button{height:32px!important;padding:0 10px!important;border:0!important;background:transparent!important;color:var(--text-muted)!important;border-radius:6px!important;font-size:11px!important;white-space:nowrap}
.tlog-theme-switch button.active{background:var(--bg-card)!important;color:var(--text-main)!important;box-shadow:0 0 0 1px var(--border-highlight)}
.graph-dashboard-v2{display:block;min-width:0}
.graph-dashboard-summary{display:grid;grid-template-columns:repeat(10,minmax(86px,1fr));gap:8px;margin:0 0 12px}
.graph-summary-item{min-width:0;padding:8px 9px;border:1px solid var(--border-color);border-radius:8px;background:var(--panel-bg);box-shadow:0 5px 18px var(--shadow-color)}
.graph-summary-item span{display:block;color:var(--text-muted);font-size:9px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.graph-summary-item strong{display:block;margin-top:3px;color:var(--text-main);font:800 13px/1.2 monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.graph-dashboard-workspace{display:grid;grid-template-columns:minmax(0,3fr) minmax(320px,1fr);gap:14px;align-items:start}
.graph-dashboard-main,.graph-dashboard-dock{min-width:0}
.graph-dashboard-main .graph-viewer-left{display:block}
.graph-dashboard-main .graph-viewer-chart-wrap{background:var(--graph-bg)!important;border-color:var(--border-color)!important;box-shadow:0 8px 24px var(--shadow-color)}
.graph-dashboard-dock{border:1px solid var(--border-color);border-radius:10px;background:var(--panel-bg);overflow:hidden;box-shadow:0 8px 24px var(--shadow-color);position:sticky;top:10px}
.graph-dock-tabs{display:grid;grid-template-columns:repeat(4,1fr);gap:0;border-bottom:1px solid var(--border-color);background:var(--panel-bg-2)}
.graph-dock-tabs button{min-width:0;height:42px;border:0;border-right:1px solid var(--border-color);background:transparent;color:var(--text-muted);font-size:10px;font-weight:800;cursor:pointer;padding:0 5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.graph-dock-tabs button:last-child{border-right:0}.graph-dock-tabs button.active{color:#38bdf8;background:rgba(56,189,248,.08);box-shadow:inset 0 -2px 0 #38bdf8}
.graph-dock-panel{padding:10px;min-height:360px}.graph-dock-panel[hidden]{display:none!important}
.graph-dock-panel #attitudePanel{position:static!important;top:auto!important;margin:0;border:0!important;background:transparent!important;padding:0!important;box-shadow:none!important}
.graph-dock-panel #boardMessagesPanel{margin:0!important;border:0!important;background:transparent!important;padding:0!important}
.graph-dock-panel #boardMessagesList{max-height:520px!important}
.graph-dock-data-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.graph-dock-data-card{border:1px solid var(--border-color);border-radius:7px;background:var(--panel-bg-2);padding:9px;min-width:0}.graph-dock-data-card b{display:block;color:var(--text-muted);font-size:9px}.graph-dock-data-card span{display:block;margin-top:3px;font:800 13px monospace;color:var(--text-main);overflow-wrap:anywhere}
#graphDockTx16Content .sticks-detail-inner{margin:0;max-width:none;border:0;background:transparent}#graphDockTx16Content .sticks-grid{grid-template-columns:1fr;padding:0}#graphDockTx16Content .stick-pad{width:118px;height:118px;flex-basis:118px}#graphDockTx16Content .switches-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.mavlink-selector-shell{margin-top:14px;border:1px solid var(--border-color);border-radius:10px;background:var(--panel-bg);padding:11px;box-shadow:0 8px 24px var(--shadow-color)}
.mavlink-selector-toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:9px}.mavlink-selector-toolbar strong{margin-right:auto;font-size:12px}.mavlink-selector-toolbar button{height:34px;border:1px solid var(--border-highlight);border-radius:7px;background:var(--input-bg);color:var(--text-main);font-size:10px;font-weight:800;cursor:pointer;padding:0 10px}.mavlink-selector-toolbar .preset-btn{color:#93c5fd}.mavlink-selector-shell.collapsed #mavlinkPlotPanel{display:none!important}.mavlink-selector-shell.collapsed{padding-bottom:8px}
#graphSelectedSeriesChips{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 9px}.graph-series-chip{display:inline-flex;align-items:center;gap:6px;max-width:260px;border:1px solid var(--border-color);border-radius:999px;background:var(--panel-bg-2);padding:5px 8px;color:var(--text-main);font:700 10px monospace}.graph-series-chip i{width:8px;height:8px;border-radius:50%;flex:0 0 8px}.graph-series-chip button{border:0;background:transparent;color:var(--text-muted);cursor:pointer;font-weight:900;padding:0;line-height:1}.graph-series-chip span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#mavlinkPlotPanel{background:var(--panel-bg-2)!important;border-color:var(--border-color)!important}#mavlinkPlotSearch{background:var(--input-bg)!important;color:var(--text-main)!important}.mavlink-message-group{background:var(--panel-bg)!important;border-color:var(--border-color)!important}.mavlink-message-group>summary{background:var(--panel-bg-2)!important}.mavlink-field-row{color:var(--text-main)!important}
.graph-mobile-nav{display:none}
@media (max-width:1199px){
  .graph-dashboard-workspace{grid-template-columns:1fr}.graph-dashboard-dock{position:static}.graph-dashboard-summary{grid-template-columns:repeat(5,minmax(0,1fr))}.graph-dock-panel{min-height:0}.graph-dock-panel #boardMessagesList{max-height:360px!important}
}
@media (max-width:767px){
  #graphViewerOverlay{padding:8px!important}.graph-viewer-toolbar{padding:7px!important;gap:6px!important}.graph-viewer-toolbar>*{max-width:100%}.graph-viewer-title{width:100%;order:-1}.tlog-theme-switch{width:100%}.tlog-theme-switch button{flex:1}
  .graph-mobile-nav{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;margin:0 0 9px}.graph-mobile-nav button{height:46px;border:1px solid var(--border-color);border-radius:7px;background:var(--panel-bg);color:var(--text-muted);font-size:9px;font-weight:800;padding:0 3px}.graph-mobile-nav button.active{color:#38bdf8;border-color:#38bdf8;background:rgba(56,189,248,.08)}
  .graph-dashboard-summary{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.graph-summary-item{padding:7px}.graph-dashboard-workspace{display:block}.graph-dashboard-dock{margin-top:8px}.graph-dock-tabs{grid-template-columns:repeat(2,1fr)}.graph-dock-tabs button{height:44px}.graph-dock-panel{padding:8px}
  #graphCanvas{height:340px!important}.graph-help{font-size:10px}.mavlink-selector-shell{padding:8px;margin-top:8px}.mavlink-selector-toolbar{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.mavlink-selector-toolbar strong{grid-column:1/-1}.mavlink-selector-toolbar button{height:44px}.mavlink-plot-head{grid-template-columns:1fr!important}#mavlinkPlotGroups{grid-template-columns:1fr!important;max-height:420px!important}
  .graph-dashboard-v2[data-mobile-active="overview"] .graph-dashboard-workspace,.graph-dashboard-v2[data-mobile-active="overview"] #mavlinkSelectorShell{display:none!important}
  .graph-dashboard-v2[data-mobile-active="graph"] .graph-dashboard-summary,.graph-dashboard-v2[data-mobile-active="graph"] .graph-dashboard-dock{display:none!important}
  .graph-dashboard-v2[data-mobile-active="attitude"] .graph-dashboard-summary,.graph-dashboard-v2[data-mobile-active="attitude"] .graph-dashboard-main,.graph-dashboard-v2[data-mobile-active="attitude"] #mavlinkSelectorShell{display:none!important}
  .graph-dashboard-v2[data-mobile-active="messages"] .graph-dashboard-summary,.graph-dashboard-v2[data-mobile-active="messages"] .graph-dashboard-main,.graph-dashboard-v2[data-mobile-active="messages"] #mavlinkSelectorShell{display:none!important}
}
'''
html = require_replace(html, "\n</style>", css + "\n</style>", "dashboard css")

# Theme switch in graph toolbar.
toolbar_anchor = '      <button id="graphResetZoom" type="button">Скинути zoom</button>\n    </div>'
toolbar_replacement = '''      <button id="graphResetZoom" type="button">Скинути zoom</button>
      <div class="tlog-theme-switch" role="group" aria-label="Тема">
        <button type="button" data-theme-choice="dark" onclick="setTlogTheme('dark')">● Темна</button>
        <button type="button" data-theme-choice="light" onclick="setTlogTheme('light')">○ Світла</button>
      </div>
    </div>'''
html = require_replace(html, toolbar_anchor, toolbar_replacement, "theme switch toolbar")

js = r'''

function tlogThemeColor(name,fallback){
  const v=getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v||fallback;
}
function redrawGraphViewer(){
  try{if(typeof renderGraphSeries==='function')renderGraphSeries();}catch(_e){}
  try{if(Number.isFinite(graphViewerState?.selectedTimeMs))syncGraphDashboardAtTime(graphViewerState.selectedTimeMs);}catch(_e){}
}
function setTlogTheme(theme){
  const next=theme==='light'?'light':'dark';
  document.documentElement.setAttribute('data-tlog-theme',next);
  try{localStorage.setItem('tlog-theme',next);}catch(_e){}
  document.querySelectorAll('[data-theme-choice]').forEach(btn=>{
    btn.classList.toggle('active',btn.dataset.themeChoice===next);
    btn.setAttribute('aria-pressed',btn.dataset.themeChoice===next?'true':'false');
  });
  if(typeof redrawGraphViewer==='function'){
    try{redrawGraphViewer();}catch(_e){}
  }
}
function initTlogTheme(){
  let saved='dark';
  try{saved=localStorage.getItem('tlog-theme')||'dark';}catch(_e){}
  setTlogTheme(saved);
}

function setGraphDockTab(name){
  const allowed=['attitude','messages','tx16','data'];
  const next=allowed.includes(name)?name:'attitude';
  document.querySelectorAll('[data-dock-panel]').forEach(panel=>{panel.hidden=panel.dataset.dockPanel!==next;});
  document.querySelectorAll('[data-dock-tab]').forEach(btn=>{
    const active=btn.dataset.dockTab===next;
    btn.classList.toggle('active',active);
    btn.setAttribute('aria-selected',active?'true':'false');
  });
}
function setGraphMobileView(name){
  const root=document.getElementById('graphDashboardV2');if(!root)return;
  const next=['overview','graph','attitude','messages'].includes(name)?name:'graph';
  root.dataset.mobileActive=next;
  document.querySelectorAll('[data-mobile-view]').forEach(btn=>btn.classList.toggle('active',btn.dataset.mobileView===next));
  if(next==='attitude')setGraphDockTab('attitude');
  if(next==='messages')setGraphDockTab('messages');
  setTimeout(()=>{try{if(typeof renderGraphSeries==='function')renderGraphSeries();}catch(_e){}},0);
}
function setMavlinkSelectorCollapsed(collapsed){
  const shell=document.getElementById('mavlinkSelectorShell');if(!shell)return;
  shell.classList.toggle('collapsed',Boolean(collapsed));
  const btn=document.getElementById('mavlinkSelectorToggle');
  if(btn){btn.textContent=collapsed?'Розгорнути':'Згорнути';btn.setAttribute('aria-expanded',collapsed?'false':'true');}
}
function applyDashboardPreset(name){
  if(name==='altitude'){
    graphViewerState.selectedSeries.clear();
    const select=document.getElementById('graphMetricSelect');if(select)select.value='altitude';
    if(typeof setGraphMetric==='function')setGraphMetric('altitude');
  }else if(typeof applyDynamicPreset==='function'){
    applyDynamicPreset(name);
    const select=document.getElementById('graphMetricSelect');if(select)select.value='__custom';
  }
  setTimeout(renderSelectedSeriesChips,0);
}
function renderSelectedSeriesChips(){
  const host=document.getElementById('graphSelectedSeriesChips');if(!host)return;
  const selected=(graphViewerState.dynamicCatalog||[]).filter(x=>graphViewerState.selectedSeries.has(x.id));
  if(selected.length){
    host.innerHTML=selected.map(x=>`<div class="graph-series-chip"><i style="background:${seriesColorFor(x.id)}"></i><span>${dynamicEscapeHtml(x.label||x.id)}</span><button type="button" data-remove-series="${dynamicEscapeHtml(x.id)}" title="Прибрати">×</button></div>`).join('');
  }else{
    const metric=graphMetricByKey(graphViewerState.metricKey);
    host.innerHTML=metric?`<div class="graph-series-chip"><i style="background:#38bdf8"></i><span>${dynamicEscapeHtml(metric.label)} (${dynamicEscapeHtml(metric.unit)})</span></div>`:'<div class="graph-series-chip"><span>Сигнали не вибрані</span></div>';
  }
  host.querySelectorAll('[data-remove-series]').forEach(btn=>btn.onclick=()=>{
    graphViewerState.selectedSeries.delete(btn.dataset.removeSeries);
    if(typeof renderMavlinkFieldBrowser==='function')renderMavlinkFieldBrowser();
    if(typeof resetDynamicGraphView==='function')resetDynamicGraphView();
    if(typeof renderGraphSeries==='function')renderGraphSeries();
    renderSelectedSeriesChips();
  });
}
function dashboardSample(timeKey,valueKey,timeMs){
  const d=graphViewerState.result?.graph_data||{},times=d[timeKey]||[],values=d[valueKey]||[];
  const i=nearestSampleIndex(times,timeMs),v=i>=0?Number(values[i]):NaN;
  return Number.isFinite(v)?v:null;
}
function dashboardModeAtTime(timeMs){
  const d=graphViewerState.result?.graph_data||{},tt=d.mode_time_ms||[],vv=d.flight_mode||[];
  if(!tt.length||!vv.length)return '—';let i=nearestSampleIndex(tt,timeMs);if(i<0)return '—';if(Number(tt[i])>timeMs&&i>0)i-=1;return String(vv[i]||'—');
}
function nearestDashboardTimelineRow(timeMs){
  const rows=Array.isArray(graphViewerState.result?.timeline)?graphViewerState.result.timeline:[];let best=null,diff=Infinity;
  rows.forEach(row=>{const sec=typeof timelineSeconds==='function'?timelineSeconds(row?.time):null;if(sec===null)return;const dd=Math.abs(sec*1000-timeMs);if(dd<diff){diff=dd;best=row;}});return best;
}
function renderGraphDashboardSummary(snapshot){
  const host=document.getElementById('graphDashboardSummary');if(!host)return;
  const items=[['ЧАС',snapshot.time??'—'],['РЕЖИМ',snapshot.mode??'—'],['ВИСОТА',snapshot.altitude??'—'],['ДАЛЬНІСТЬ',snapshot.distance??'—'],['АЗИМУТ',snapshot.heading??'—'],['НАПРУГА',snapshot.voltage??'—'],['СТРУМ',snapshot.current??'—'],['RSSI',snapshot.rssi??'—'],['dBm',snapshot.dbm??'—'],['TEMP',snapshot.temperature??'—']];
  host.innerHTML=items.map(([k,v])=>`<div class="graph-summary-item"><span>${k}</span><strong>${v}</strong></div>`).join('');
}
function renderGraphDockTx16(timeMs){
  const host=document.getElementById('graphDockTx16Content');if(!host)return;const row=nearestDashboardTimelineRow(timeMs);
  if(!row){host.innerHTML='<div class="board-message-empty">Немає RC-даних для цього моменту</div>';return;}
  try{host.innerHTML=typeof renderTimelineSticks==='function'?renderTimelineSticks(row):'<div class="board-message-empty">TX16 недоступний</div>';}catch(_e){host.innerHTML='<div class="board-message-empty">TX16 недоступний</div>';}
}
function renderGraphDockData(timeMs){
  const host=document.getElementById('graphDockDataContent');if(!host)return;
  const roll=dashboardSample('attitude_time_ms','roll_deg',timeMs),pitch=dashboardSample('attitude_time_ms','pitch_deg',timeMs),yaw=dashboardSample('attitude_time_ms','yaw_deg',timeMs),vs=dashboardSample('vertical_speed_time_ms','vertical_speed_down_ms',timeMs),load=dashboardSample('engine_load_time_ms','engine_load_pct',timeMs),temp=dashboardSample('fc_temp_time_ms','fc_temp_c',timeMs);
  const cards=[['ROLL',roll===null?'—':roll.toFixed(1)+'°'],['PITCH',pitch===null?'—':pitch.toFixed(1)+'°'],['YAW',yaw===null?'—':yaw.toFixed(1)+'°'],['V/S',vs===null?'—':vs.toFixed(1)+' м/с'],['ENGINE LOAD',load===null?'—':load.toFixed(1)+' %'],['TEMP FC',temp===null?'—':temp.toFixed(1)+' °C']];
  host.innerHTML='<div class="graph-dock-data-grid">'+cards.map(([k,v])=>`<div class="graph-dock-data-card"><b>${k}</b><span>${v}</span></div>`).join('')+'</div>';
}
function syncGraphDashboardAtTime(timeMs){
  const row=nearestDashboardTimelineRow(timeMs),alt=dashboardSample('altitude_time_ms','altitude_m',timeMs),heading=dashboardSample('attitude_time_ms','yaw_deg',timeMs),voltage=dashboardSample('voltage_time_ms','voltage_v',timeMs),current=dashboardSample('current_time_ms','current_a',timeMs),rssi=dashboardSample('rssi_time_ms','rssi_pct',timeMs),dbm=dashboardSample('radio_time_ms','radio_dbm',timeMs),temp=dashboardSample('fc_temp_time_ms','fc_temp_c',timeMs);
  renderGraphDashboardSummary({time:formatGraphTime(timeMs),mode:dashboardModeAtTime(timeMs),altitude:alt===null?'—':alt.toFixed(1)+' м',distance:row?.dist??'—',heading:heading===null?'—':heading.toFixed(1)+'°',voltage:voltage===null?'—':voltage.toFixed(1)+' V',current:current===null?'—':current.toFixed(1)+' A',rssi:rssi===null?'—':Math.round(rssi)+' %',dbm:dbm===null?'—':Math.round(dbm)+' dBm',temperature:temp===null?'—':temp.toFixed(1)+' °C'});
  renderGraphDockTx16(timeMs);renderGraphDockData(timeMs);renderSelectedSeriesChips();
}
function ensureGraphDashboardV2(){
  const shell=document.querySelector('#graphViewerOverlay .graph-viewer-shell');if(!shell)return;
  if(!document.getElementById('graphDashboardV2')){
    const layout=shell.querySelector('.graph-viewer-layout'),left=layout?.querySelector('.graph-viewer-left'),attitude=document.getElementById('attitudePanel'),mav=document.getElementById('mavlinkPlotPanel');
    if(!layout||!left||!attitude)return;
    const root=document.createElement('section');root.id='graphDashboardV2';root.className='graph-dashboard-v2';root.dataset.mobileActive='graph';
    root.innerHTML=`
      <div class="graph-mobile-nav" aria-label="Мобільні розділи">
        <button type="button" data-mobile-view="overview" onclick="setGraphMobileView('overview')">Огляд</button>
        <button type="button" data-mobile-view="graph" class="active" onclick="setGraphMobileView('graph')">Графік</button>
        <button type="button" data-mobile-view="attitude" onclick="setGraphMobileView('attitude')">Авіагоризонт</button>
        <button type="button" data-mobile-view="messages" onclick="setGraphMobileView('messages')">Повідомлення</button>
      </div>
      <div class="graph-dashboard-summary" id="graphDashboardSummary"></div>
      <div class="graph-dashboard-workspace">
        <div class="graph-dashboard-main" id="graphDashboardMain"></div>
        <aside class="graph-dashboard-dock" id="graphDashboardDock">
          <div class="graph-dock-tabs" role="tablist">
            <button type="button" class="active" role="tab" data-dock-tab="attitude" onclick="setGraphDockTab('attitude')">Авіагоризонт</button>
            <button type="button" role="tab" data-dock-tab="messages" onclick="setGraphDockTab('messages')">Повідомлення</button>
            <button type="button" role="tab" data-dock-tab="tx16" onclick="setGraphDockTab('tx16')">TX16</button>
            <button type="button" role="tab" data-dock-tab="data" onclick="setGraphDockTab('data')">Дані</button>
          </div>
          <div class="graph-dock-panel" data-dock-panel="attitude"></div>
          <div class="graph-dock-panel" data-dock-panel="messages" hidden></div>
          <div class="graph-dock-panel" data-dock-panel="tx16" hidden><div id="graphDockTx16Content"></div></div>
          <div class="graph-dock-panel" data-dock-panel="data" hidden><div id="graphDockDataContent"></div></div>
        </aside>
      </div>
      <section id="mavlinkSelectorShell" class="mavlink-selector-shell">
        <div class="mavlink-selector-toolbar"><strong>MAVLink параметри</strong><button type="button" class="preset-btn" onclick="applyDashboardPreset('altitude')">Altitude</button><button type="button" class="preset-btn" onclick="applyDashboardPreset('power')">Power</button><button type="button" class="preset-btn" onclick="applyDashboardPreset('radio')">Radio</button><button type="button" class="preset-btn" onclick="applyDashboardPreset('attitude')">Attitude</button><button type="button" class="preset-btn" onclick="applyDashboardPreset('esc')">ESC</button><button id="mavlinkSelectorToggle" type="button" aria-expanded="true" onclick="setMavlinkSelectorCollapsed(!document.getElementById('mavlinkSelectorShell').classList.contains('collapsed'))">Згорнути</button></div>
        <div id="graphSelectedSeriesChips"></div>
      </section>`;
    shell.insertBefore(root,layout);
    document.getElementById('graphDashboardMain').appendChild(left);
    const selector=document.getElementById('mavlinkSelectorShell');if(mav)selector.appendChild(mav);
    const attitudeHost=document.querySelector('[data-dock-panel="attitude"]');attitudeHost.appendChild(attitude);
    const messages=document.getElementById('boardMessagesPanel');if(messages)document.querySelector('[data-dock-panel="messages"]').appendChild(messages);
    layout.remove();
    const groups=document.getElementById('mavlinkPlotGroups');if(groups&&!groups.dataset.dashboardChipBound){groups.addEventListener('change',()=>setTimeout(renderSelectedSeriesChips,0));groups.dataset.dashboardChipBound='1';}
  }
  initTlogTheme();setGraphDockTab('attitude');setGraphMobileView(document.getElementById('graphDashboardV2')?.dataset.mobileActive||'graph');
}

initTlogTheme();
'''
html = require_replace(html, "\nfunction openGraphViewer(result){", js + "\nfunction openGraphViewer(result){", "dashboard javascript")

# Make every openGraphViewer variant initialize the new shell after showing overlay.
show_anchor = "overlay.hidden=false;overlay.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';"
show_replacement = show_anchor + "ensureGraphDashboardV2();"
html = html.replace(show_anchor, show_replacement)

# Keep dashboard values synced when graph cursor changes.
select_anchor = "graphViewerState.selectedTimeMs=timeMs;updateAttitudeAtTime(timeMs);"
html = html.replace(select_anchor, select_anchor + "syncGraphDashboardAtTime(timeMs);")

# Initial sync after the current attitude is rendered in both graph-viewer implementations.
html = html.replace("updateAttitudeAtTime(graphViewerState.selectedTimeMs);renderBoardMessagesAtTime(graphViewerState.selectedTimeMs);", "updateAttitudeAtTime(graphViewerState.selectedTimeMs);syncGraphDashboardAtTime(graphViewerState.selectedTimeMs);renderBoardMessagesAtTime(graphViewerState.selectedTimeMs);")
html = html.replace("renderGraphSeries(metric);updateAttitudeAtTime(graphViewerState.selectedTimeMs);", "renderGraphSeries(metric);updateAttitudeAtTime(graphViewerState.selectedTimeMs);syncGraphDashboardAtTime(graphViewerState.selectedTimeMs);")

# Canvas grid/labels adapt to light/dark theme in both the legacy and dynamic renderer.
html = html.replace("ctx.strokeStyle='#243244';ctx.lineWidth=1;ctx.fillStyle='#94a3b8';ctx.font='11px monospace';", "ctx.strokeStyle=tlogThemeColor('--graph-grid','#243244');ctx.lineWidth=1;ctx.fillStyle=tlogThemeColor('--text-muted','#94a3b8');ctx.font='11px monospace';")
html = html.replace("ctx.fillStyle='#e2e8f0';ctx.font='bold 12px sans-serif';", "ctx.fillStyle=tlogThemeColor('--text-main','#e2e8f0');ctx.font='bold 12px sans-serif';")

PATH.write_text(html, encoding="utf-8")
print("dashboard layout v2 applied")
