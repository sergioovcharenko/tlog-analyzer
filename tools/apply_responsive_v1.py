from pathlib import Path

path = Path('index.html')
html = path.read_text(encoding='utf-8')

CSS_MARKER = '/* RESPONSIVE V1 */'
SCRIPT_MARKER = 'id="responsiveV1Runtime"'

responsive_css = r'''
/* RESPONSIVE V1 */
html,body{max-width:100%;overflow-x:hidden}
img,svg,canvas,video{max-width:100%}
button,input,select,textarea{font:inherit}
button,.btn-reset,.analyze,.file-action-btn,.graph-viewer-back,.graph-reset-btn,.graph-viewer-close,#mavlinkPlotClear{touch-action:manipulation}

@media (max-width:1199px){
  .header{padding:16px 20px;gap:14px;flex-wrap:wrap}
  .container{padding:24px 14px}
  .grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
  .graph-viewer-shell{padding:12px!important}
  .graph-viewer-layout{grid-template-columns:1fr!important;gap:14px!important}
  .graph-viewer-left{min-width:0}
  #attitudePanel{width:100%!important;max-width:none!important;min-width:0!important}
  .map-v17-layout{grid-template-columns:1fr!important}
  #mapTelemetryPanel{min-height:auto!important;width:100%!important}
  .mavlink-plot-head{grid-template-columns:1fr minmax(220px,360px) auto!important}
  [class*="tx16"]{max-width:100%}
  .tx16-panel{width:100%;max-width:100%}
}

@media (max-width:767px){
  body{font-size:14px}
  .header{padding:12px;align-items:flex-start}
  .header h1{font-size:18px;line-height:1.2}
  .header p{font-size:11px}
  .btn-reset{width:100%;min-height:44px;padding:10px 12px}
  .container{padding:14px 8px}
  .upload{padding:42px 12px}
  .upload-icon{font-size:40px}
  .upload-title{font-size:17px}
  .upload-subtitle{font-size:12px}
  .analyze,.file-action-btn,.graph-viewer-back,.graph-reset-btn,.graph-viewer-close,#mavlinkPlotClear,select,input[type="search"]{min-height:44px;touch-action:manipulation}
  .file-actions{grid-template-columns:1fr!important;gap:8px!important}
  .section-title{font-size:14px;margin-top:26px}
  .grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .card{padding:12px;min-width:0}
  .card-title{font-size:10px}
  .card-value{font-size:18px;overflow-wrap:anywhere}
  .card-desc{font-size:10px}
  .ai-box{padding:14px;margin-bottom:20px}
  .ai-title{font-size:16px}
  .ai-list{padding-left:18px;font-size:12px}

  /* Timeline becomes a touch-friendly card feed on phones. */
  .timeline{overflow:visible!important;background:transparent!important;border:0!important}
  .timeline .tl-header{display:none}
  .timeline .tl-item{
    min-width:0!important;
    width:100%!important;
    display:grid!important;
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    gap:7px!important;
    padding:10px!important;
    margin:0 0 9px!important;
    border:1px solid var(--border-color)!important;
    border-radius:9px!important;
    background:var(--bg-card);
    align-items:stretch!important;
  }
  .timeline .tl-item>div{min-width:0!important;padding:6px 7px!important;border-radius:6px;background:#0d131a;overflow-wrap:anywhere;white-space:normal!important}
  .tl-item>div::before{content:attr(data-mobile-label);display:block;margin-bottom:2px;color:#64748b;font:800 9px/1.2 monospace;text-transform:uppercase;letter-spacing:.04em}
  .timeline .tl-system,.timeline .tl-analysis,.timeline .tl-pilot,.timeline [class*="tx16"]{grid-column:1/-1!important}
  .timeline .esc-detail,.timeline .vib-detail,.timeline .att-detail{min-width:0!important;width:100%!important;overflow:auto}
  .timeline .esc-detail-inner{margin-left:0!important;max-width:100%!important;min-width:0!important}

  /* Graph + attitude stack vertically and keep touch controls readable. */
  .graph-viewer-shell{padding:8px!important;overflow-x:hidden!important}
  .graph-viewer-toolbar{display:grid!important;grid-template-columns:1fr!important;gap:8px!important}
  .graph-viewer-toolbar>*{width:100%!important;min-width:0!important}
  .graph-viewer-layout{grid-template-columns:1fr!important;gap:10px!important}
  .graph-viewer-chart-wrap{min-width:0!important;overflow-x:auto!important;-webkit-overflow-scrolling:touch}
  #graphCanvas{min-width:620px}
  #attitudePanel{width:100%!important;max-width:none!important;margin:0!important;padding:10px!important}
  #attitudeHorizon{transform:scale(.88);transform-origin:top center;margin-bottom:-26px!important}
  .attitude-head-row{gap:6px!important;flex-wrap:wrap!important}
  .attitude-mode-card{min-width:0!important;flex:1 1 150px!important}
  .attitude-radio-row,.attitude-values{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  #boardMessagesPanel{width:100%!important}

  /* Dynamic MAVLink browser becomes one-column and scrolls internally. */
  .mavlink-plot-head{grid-template-columns:1fr!important;gap:7px!important}
  .mavlink-plot-head>*{width:100%!important;min-width:0!important}
  #mavlinkPlotGroups{grid-template-columns:1fr!important;max-height:420px!important}
  .mavlink-field-row{grid-template-columns:22px 12px minmax(0,1fr) auto!important;min-height:38px}

  /* Map/telemetry and TX16 blocks stack without forcing page overflow. */
  .map-v17-layout{grid-template-columns:1fr!important;gap:10px!important}
  .map-v17-svg-wrap,.map-v17-map-wrap,[id*="map"] svg{max-width:100%!important;overflow:hidden}
  #mapTelemetryPanel{width:100%!important;min-width:0!important;min-height:auto!important}
  .tx16-panel,[class*="tx16-panel"],[class*="tx16-wrap"],[class*="tx16-grid"]{width:100%!important;max-width:100%!important;min-width:0!important;grid-template-columns:1fr!important}
  [class*="tx16"] button{min-height:44px;touch-action:manipulation}

  .scroll-top-fab{right:10px!important;bottom:10px!important;min-height:44px}
}

@media (max-width:430px){
  .header{padding:10px 8px}
  .container{padding:10px 6px}
  .grid{grid-template-columns:1fr 1fr;gap:6px}
  .card{padding:10px 8px}
  .card-value{font-size:17px}
  .timeline .tl-item{grid-template-columns:1fr!important;padding:8px!important}
  .timeline .tl-system,.timeline .tl-analysis,.timeline .tl-pilot,.timeline [class*="tx16"]{grid-column:1!important}
  #attitudeHorizon{transform:scale(.78);margin-bottom:-52px!important}
  .attitude-radio-row,.attitude-values{grid-template-columns:1fr 1fr!important;gap:6px!important}
  .attitude-value{padding:7px!important}
  .attitude-mode-card span{font-size:14px!important}
  #graphCanvas{min-width:560px}
  #mavlinkPlotPanel{padding:9px!important}
  .mavlink-message-group>summary{padding:10px 8px!important}
}
'''

responsive_script = r'''
<script id="responsiveV1Runtime">
(function(){
  const MOBILE_LABELS=[
    'ЧАС','MODE','ALT','BAT','CURRENT','dBm','RSSI','TEMP FC','VIB','ATT','ENGINE LOAD','ESC','ПОВІДОМЛЕННЯ','АНАЛІЗ','TX16S','ДІЯ ПІЛОТА'
  ];

  function applyMobileTimelineLabels(){
    document.querySelectorAll('.timeline .tl-item').forEach(row=>{
      Array.from(row.children).forEach((cell,index)=>{
        if(!cell.dataset.mobileLabel) cell.dataset.mobileLabel=MOBILE_LABELS[index]||`ПОЛЕ ${index+1}`;
      });
    });
  }
  window.applyMobileTimelineLabels=applyMobileTimelineLabels;

  function refreshResponsiveUI(){
    applyMobileTimelineLabels();
    document.documentElement.classList.toggle('is-phone',window.innerWidth<=767);
    document.documentElement.classList.toggle('is-tablet',window.innerWidth>767&&window.innerWidth<=1199);
  }

  document.addEventListener('DOMContentLoaded',()=>{
    refreshResponsiveUI();
    const target=document.getElementById('timeline')||document.querySelector('.timeline')||document.body;
    const observer=new MutationObserver(()=>applyMobileTimelineLabels());
    observer.observe(target,{childList:true,subtree:true});
  });
  window.addEventListener('resize',refreshResponsiveUI,{passive:true});
  window.addEventListener('orientationchange',()=>setTimeout(refreshResponsiveUI,80),{passive:true});
})();
</script>
'''

if CSS_MARKER not in html:
    idx = html.find('</style>')
    if idx < 0:
        raise SystemExit('style close tag not found')
    html = html[:idx] + responsive_css + '\n' + html[idx:]

if SCRIPT_MARKER not in html:
    idx = html.rfind('</body>')
    if idx < 0:
        raise SystemExit('body close tag not found')
    html = html[:idx] + responsive_script + '\n' + html[idx:]

path.write_text(html,encoding='utf-8')
print('Applied responsive v1 tablet/phone layer')
