from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "index.html"
MARKER = "/* LIGHT_THEME_POLISH_V1 */"

html = PATH.read_text(encoding="utf-8")
if MARKER in html:
    print("light theme and board messages patch already applied")
    raise SystemExit(0)

css = r'''

/* LIGHT_THEME_POLISH_V1 */
[data-tlog-theme="light"]{
  --light-page:#eef3f8;
  --light-panel:#ffffff;
  --light-panel-2:#f7f9fc;
  --light-text:#172033;
  --light-muted:#5b6b80;
  --light-border:#cbd7e6;
  --light-accent:#0877c9;
  --bg-main:var(--light-page);
  --bg-card:var(--light-panel);
  --bg-header:#f8fafc;
  --panel-bg:var(--light-panel);
  --panel-bg-2:var(--light-panel-2);
  --input-bg:#ffffff;
  --border-color:var(--light-border);
  --border-highlight:#9fb0c6;
  --text-main:var(--light-text);
  --text-muted:var(--light-muted);
  --accent:var(--light-accent);
  --accent-hover:#075fa1;
  --accent-glow:rgba(8,119,201,.14);
  --graph-bg:#ffffff;
  --graph-grid:rgba(71,85,105,.18);
  --shadow-color:rgba(15,23,42,.08);
}
[data-tlog-theme="light"] body{background:var(--light-page);color:var(--light-text)}
[data-tlog-theme="light"] .header,
[data-tlog-theme="light"] .card,
[data-tlog-theme="light"] .ai-box,
[data-tlog-theme="light"] .timeline,
[data-tlog-theme="light"] .graph-viewer-toolbar,
[data-tlog-theme="light"] .graph-dashboard-dock,
[data-tlog-theme="light"] .graph-summary-item,
[data-tlog-theme="light"] .mavlink-selector-shell{background:var(--light-panel)!important;color:var(--light-text)!important;border-color:var(--light-border)!important}
[data-tlog-theme="light"] .timeline{box-shadow:0 8px 22px rgba(15,23,42,.05)}
[data-tlog-theme="light"] .tl-header{background:#e7eef7!important;color:#40536a!important;border-color:var(--light-border)!important;box-shadow:0 2px 8px rgba(15,23,42,.08)}
[data-tlog-theme="light"] .tl-item{border-color:#dce5ef!important;color:var(--light-text)!important}
[data-tlog-theme="light"] .tl-system{color:#24364c!important}
[data-tlog-theme="light"] .tl-pilot{color:#0867ad!important}
[data-tlog-theme="light"] .repeat-alert-group{background:var(--light-panel-2)!important;border-color:var(--light-border)!important}
[data-tlog-theme="light"] .repeat-critical>summary{color:#b91c1c!important}
[data-tlog-theme="light"] .repeat-attention>summary{color:#c2410c!important}
[data-tlog-theme="light"] .repeat-warning>summary{color:#a16207!important}
[data-tlog-theme="light"] .repeat-info>summary{color:#1d4ed8!important}
[data-tlog-theme="light"] .esc-toggle,
[data-tlog-theme="light"] .vib-toggle,
[data-tlog-theme="light"] .att-toggle{background:#eef4fb!important;color:#0b67a8!important;border-color:#aebed2!important}
[data-tlog-theme="light"] .esc-detail{background:#f6f9fc!important;border-color:var(--light-border)!important}
[data-tlog-theme="light"] .esc-detail-inner{background:#ffffff!important;border-color:var(--light-border)!important}
[data-tlog-theme="light"] .timeline-scrollbar-fixed::-webkit-scrollbar-track{background:#e6edf5!important}
[data-tlog-theme="light"] .timeline-scrollbar-fixed::-webkit-scrollbar-thumb{background:#9aabc0!important}
[data-tlog-theme="light"] .timeline-floating-header{background:#e7eef7!important;border-color:var(--light-border)!important;box-shadow:0 4px 14px rgba(15,23,42,.12)!important}
[data-tlog-theme="light"] input,
[data-tlog-theme="light"] select,
[data-tlog-theme="light"] button{border-color:#aebed2}
[data-tlog-theme="light"] .graph-viewer-chart-wrap{background:#ffffff!important;border-color:var(--light-border)!important}
[data-tlog-theme="light"] .graph-help{color:#607086!important}
[data-tlog-theme="light"] .graph-dock-tabs{background:#edf3f9!important;border-color:var(--light-border)!important}
[data-tlog-theme="light"] .graph-dock-tabs button{color:#4b5f78!important;border-color:var(--light-border)!important}
[data-tlog-theme="light"] .graph-dock-tabs button.active{color:#075f9d!important;background:#dceefa!important;box-shadow:inset 0 -2px 0 #0877c9!important}
[data-tlog-theme="light"] #boardMessagesPanel{background:#ffffff!important;color:var(--light-text)!important}
[data-tlog-theme="light"] #boardMessagesList{scrollbar-color:#9aabc0 #edf3f8}
[data-tlog-theme="light"] .board-message{background:#f7f9fc!important;color:#27384d!important;border:1px solid #d7e1ec;border-left-width:4px}
[data-tlog-theme="light"] .board-message-error{background:#fff1f2!important;border-left-color:#dc2626!important;color:#7f1d1d!important}
[data-tlog-theme="light"] .board-message-warning{background:#fff8e6!important;border-left-color:#d97706!important;color:#78350f!important}
[data-tlog-theme="light"] .board-message-info{background:#eef7ff!important;border-left-color:#0284c7!important;color:#164e63!important}
[data-tlog-theme="light"] .board-message-recovery{background:#eefbf2!important;border-left-color:#16a34a!important;color:#14532d!important}
[data-tlog-theme="light"] .board-message-current{outline:2px solid #0877c9!important;outline-offset:-1px;box-shadow:0 0 0 3px rgba(8,119,201,.10)}
[data-tlog-theme="light"] .board-message-empty{color:#607086!important}
[data-tlog-theme="light"] .board-messages-title{color:#24364c!important}
[data-tlog-theme="light"] .board-messages-subtitle{color:#607086!important}
[data-tlog-theme="light"] #mavlinkPlotPanel,
[data-tlog-theme="light"] .mavlink-message-group,
[data-tlog-theme="light"] .mavlink-message-group>summary{background:#f7f9fc!important;color:var(--light-text)!important;border-color:var(--light-border)!important}
[data-tlog-theme="light"] #mavlinkPlotSearch{background:#ffffff!important;color:var(--light-text)!important;border-color:#aebed2!important}
[data-tlog-theme="light"] #mapTelemetryPanel{background:#f7f9fc!important;color:var(--light-text)!important;border-color:var(--light-border)!important}
[data-tlog-theme="light"] #mapTelemetryPanel>div:first-child{color:var(--light-text)!important}
[data-tlog-theme="light"] #mapZoomOut,
[data-tlog-theme="light"] #mapZoomReset,
[data-tlog-theme="light"] #mapZoomIn,
[data-tlog-theme="light"] #mapMode3D,
[data-tlog-theme="light"] #map3dTop,
[data-tlog-theme="light"] #map3dNorth,
[data-tlog-theme="light"] #map3dEast,
[data-tlog-theme="light"] #antennaModeManual{background:#f7f9fc!important;color:#40536a!important;border-color:#aebed2!important}
[data-tlog-theme="light"] #antennaManualAz{background:#ffffff!important;color:var(--light-text)!important;border-color:#aebed2!important}
[data-tlog-theme="light"] #scrollTopBtn{background:#ffffff!important;color:#24364c!important;border-color:#aebed2!important;box-shadow:0 8px 24px rgba(15,23,42,.12)!important}

.board-message-current{outline:2px solid #38bdf8;outline-offset:-1px;box-shadow:0 0 0 3px rgba(56,189,248,.10)}
#boardMessagesList{max-height:520px!important}
'''

if "\n</style>" not in html:
    raise SystemExit("style closing tag not found")
html = html.replace("\n</style>", css + "\n</style>", 1)

old_subtitle = '<div class="board-messages-subtitle">Події в межах ±5 с від вибраного часу</div>'
new_subtitle = '<div class="board-messages-subtitle">STATUSTEXT від борта • помилки, попередження та службові повідомлення</div>'
if old_subtitle not in html:
    raise SystemExit("board messages subtitle anchor not found")
html = html.replace(old_subtitle, new_subtitle, 1)

pattern = re.compile(
    r"function renderBoardMessagesAtTime\(timeMs\)\{\n"
    r"  const root=document\.getElementById\('boardMessagesList'\);if\(!root\)return;\n"
    r"  const messages=Array\.isArray\(graphViewerState\.result\?\.board_messages\)\?graphViewerState\.result\.board_messages:\[\];\n"
    r"  const rows=.*?\n"
    r"  if\(!rows\.length\).*?\n"
    r"  root\.innerHTML=.*?\n"
    r"\}",
    re.S,
)
replacement = r'''function renderBoardMessagesAtTime(timeMs){
  const root=document.getElementById('boardMessagesList');if(!root)return;
  const messages=Array.isArray(graphViewerState.result?.board_messages)?graphViewerState.result.board_messages:[];
  const rows=messages.slice().filter(m=>Number.isFinite(Number(m.time_ms))&&String(m.text||'').trim()).sort((a,b)=>Number(a.time_ms)-Number(b.time_ms));
  if(!rows.length){root.innerHTML='<div class="board-message-empty">Немає STATUSTEXT повідомлень від борта</div>';return;}
  root.innerHTML=rows.map(m=>{const level=['error','warning','info','recovery'].includes(m.level)?m.level:'info';const current=Number.isFinite(Number(timeMs))&&Math.abs(Number(m.time_ms)-Number(timeMs))<=BOARD_MESSAGE_WINDOW_MS?' board-message-current':'';return `<div class="board-message board-message-${level}${current}"><span class="board-message-time">${formatGraphTime(Number(m.time_ms))}</span>${dynamicEscapeHtml(m.text)}</div>`;}).join('');
  const current=root.querySelector('.board-message-current');if(current)current.scrollIntoView({block:'nearest'});
}'''
html, count = pattern.subn(replacement, html, count=1)
if count != 1:
    raise SystemExit(f"board message render function anchor not found: {count}")

html = html.replace("ctx.fillStyle='#dbeafe';ctx.fillText(text,lx+14,ly);", "ctx.fillStyle=tlogThemeColor('--text-main','#dbeafe');ctx.fillText(text,lx+14,ly);", 1)
html = html.replace("ctx.fillStyle='#64748b';ctx.fillText(`${unit}: ${scale.min.toFixed(1)}…${scale.max.toFixed(1)}`,x1-145,yy);", "ctx.fillStyle=tlogThemeColor('--text-muted','#64748b');ctx.fillText(`${unit}: ${scale.min.toFixed(1)}…${scale.max.toFixed(1)}`,x1-145,yy);", 1)

PATH.write_text(html, encoding="utf-8")
print("light theme and board messages patch applied")
