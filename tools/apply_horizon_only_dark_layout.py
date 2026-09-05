from pathlib import Path
import re

PATH = Path('index.html')
MARKER = '/* HORIZON_ONLY_DARK_V1 */'
text = PATH.read_text(encoding='utf-8')

if MARKER in text:
    raise SystemExit(0)

# Theme selector is removed from the UI. Dark remains the single supported visual mode.
text = re.sub(r'<button[^>]*data-theme-choice=["\'](?:dark|light)["\'][^>]*>.*?</button>', '', text, flags=re.S)

summary_re = re.compile(r'function renderGraphDashboardSummary\(snapshot\)\{.*?\n\}', re.S)
summary_fn = r'''function renderGraphDashboardSummary(snapshot){
  const host=document.getElementById('graphDashboardSummary');if(!host)return;
  const items=[['ЧАС',snapshot.time??'—'],['РЕЖИМ',snapshot.mode??'—'],['ВИСОТА',snapshot.altitude??'—'],['ДАЛЬНІСТЬ',snapshot.distance??'—'],['АЗИМУТ',snapshot.heading??'—'],['НАПРУГА',snapshot.voltage??'—'],['СТРУМ',snapshot.current??'—'],['RSSI',snapshot.rssi??'—'],['dBm',snapshot.dbm??'—'],['TEMP',snapshot.temperature??'—']];
  const toneFor=(k,v)=>{
    const n=parseFloat(String(v??'').replace(',','.'));
    if(!Number.isFinite(n))return '';
    if(k==='НАПРУГА')return typeof attitudeBatClass==='function'?attitudeBatClass(n):'';
    if(k==='СТРУМ')return typeof attitudeCurrentClass==='function'?attitudeCurrentClass(n):'';
    if(k==='TEMP')return typeof attitudeFcTempClass==='function'?attitudeFcTempClass(n):'';
    if(k==='RSSI')return n>=75?'summary-success':(n>=40?'summary-warning':'summary-danger');
    if(k==='dBm')return n>=-70?'summary-success':(n>=-85?'summary-warning':'summary-danger');
    return '';
  };
  host.innerHTML=items.map(([k,v])=>`<div class="graph-summary-item ${toneFor(k,v)}"><span>${k}</span><strong>${v}</strong></div>`).join('');
  applyHorizonOnlyDarkLayout();
}'''
text, count = summary_re.subn(summary_fn, text, count=1)
if count != 1:
    raise SystemExit('renderGraphDashboardSummary anchor not found')

css = r'''
/* HORIZON_ONLY_DARK_V1 */
.tlog-theme-switch{display:none!important}
#globalThemeSwitch{display:none!important}
.graph-dashboard-summary{display:none!important}
.graph-dashboard-summary.in-attitude{
  display:grid!important;
  grid-template-columns:repeat(2,minmax(0,1fr))!important;
  gap:7px!important;
  margin:10px 0 0!important;
}
.graph-dashboard-summary.in-attitude .graph-summary-item{
  margin:0!important;
  padding:8px 9px!important;
  background:#080d13!important;
  border:1px solid #253246!important;
  box-shadow:none!important;
}
.graph-dashboard-summary.in-attitude .graph-summary-item span{color:#7dd3fc!important}
.graph-dashboard-summary.in-attitude .graph-summary-item strong{color:var(--text-main);font-size:15px!important}
.graph-summary-item.att-bat-green strong,.graph-summary-item.att-engine-green strong,.graph-summary-item.summary-success strong{color:#22c55e!important}
.graph-summary-item.att-bat-orange strong,.graph-summary-item.att-fc-orange strong,.graph-summary-item.summary-warning strong{color:#f59e0b!important}
.graph-summary-item.att-bat-red strong,.graph-summary-item.att-current-red strong,.graph-summary-item.att-fc-red strong,.graph-summary-item.summary-danger strong{color:#ef4444!important}
.graph-dock-tabs{display:none!important}
.graph-dock-panel:not([data-dock-panel="attitude"]){display:none!important}
.graph-dock-panel[data-dock-panel="attitude"]{display:block!important}
.graph-dashboard-dock .attitude-radio-row{display:none!important}
.graph-dashboard-dock .attitude-flight-mode{display:none!important}
.graph-dashboard-dock #attitudeValues{display:none!important}
.graph-dashboard-dock #boardMessagesPanel{display:none!important}
.graph-dashboard-dock{overflow:visible!important}
@media (max-width:1199px){.graph-dashboard-summary.in-attitude{grid-template-columns:repeat(5,minmax(0,1fr))!important}}
@media (max-width:767px){.graph-dashboard-summary.in-attitude{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
'''
text = text.replace('</style>', css + '\n</style>', 1)

js = r'''
<script>
function applyHorizonOnlyDarkLayout(){
  try{localStorage.setItem('tlog-theme','dark');}catch(_e){}
  document.documentElement.setAttribute('data-tlog-theme','dark');
  const summary=document.getElementById('graphDashboardSummary');
  const attitudePanel=document.getElementById('attitudePanel');
  if(summary&&attitudePanel){
    summary.classList.add('in-attitude');
    if(summary.parentElement!==attitudePanel)attitudePanel.appendChild(summary);
  }
  const attitudeDock=document.querySelector('.graph-dock-panel[data-dock-panel="attitude"]');
  if(attitudeDock)attitudeDock.hidden=false;
  document.querySelectorAll('.graph-dock-panel:not([data-dock-panel="attitude"])').forEach(el=>{el.hidden=true;});
}
(function(){
  let queued=false;
  const schedule=()=>{
    if(queued)return;queued=true;
    requestAnimationFrame(()=>{queued=false;applyHorizonOnlyDarkLayout();});
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
  new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});
})();
</script>
'''
text = text.replace('</body>', js + '\n</body>', 1)

PATH.write_text(text, encoding='utf-8')
