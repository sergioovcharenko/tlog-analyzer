from pathlib import Path

main_path = Path("backend/main.py")
html_path = Path("index.html")
main = main_path.read_text(encoding="utf-8")
html = html_path.read_text(encoding="utf-8")

# Backend integration -------------------------------------------------------
if "from backend.mavlink_plot import MavlinkPlotCollector, build_board_messages" not in main:
    anchor = "from pymavlink import mavutil\n"
    if anchor not in main:
        raise SystemExit("pymavlink import anchor not found")
    main = main.replace(
        anchor,
        anchor + "try:\n    from backend.mavlink_plot import MavlinkPlotCollector, build_board_messages\nexcept ImportError:\n    from mavlink_plot import MavlinkPlotCollector, build_board_messages\n",
        1,
    )
else:
    main = main.replace(
        "from backend.mavlink_plot import MavlinkPlotCollector, build_board_messages\n",
        "try:\n    from backend.mavlink_plot import MavlinkPlotCollector, build_board_messages\nexcept ImportError:\n    from mavlink_plot import MavlinkPlotCollector, build_board_messages\n",
        1,
    )

if "mavlink_plot_collector = MavlinkPlotCollector" not in main:
    anchor = "        # STATUSTEXT MAVLink2 chunks\n        statustext_chunks = {}\n"
    if anchor not in main:
        raise SystemExit("collector init anchor not found")
    main = main.replace(
        anchor,
        anchor + "\n        # Dynamic chart-only catalog. Existing analysis branches remain unchanged.\n        mavlink_plot_collector = MavlinkPlotCollector(max_points_per_series=1200)\n",
        1,
    )

old_loop = '''        needed_messages = [
            "HEARTBEAT", "SYS_STATUS", "VFR_HUD", "EFI_STATUS", "ALTITUDE",
            "LOCAL_POSITION_NED", "GLOBAL_POSITION_INT", "RC_CHANNELS",
            "RADIO", "RADIO_STATUS", "ATTITUDE", "VIBRATION",
            "TEMPERATURE", "HIGHRES_IMU", "SCALED_PRESSURE",
            "SCALED_PRESSURE2", "SCALED_PRESSURE3", "MCU_STATUS",
            "STATUSTEXT", "ESC_TELEMETRY_1_TO_4", "PARAM_VALUE",
        ]

        while True:
            msg = mav.recv_match(type=needed_messages, blocking=False)
'''
new_loop = '''        # Read every decoded MAVLink message so the plot catalog is truly dynamic.
        # Specialized analysis below still reacts only to the message types it knows.
        while True:
            msg = mav.recv_match(blocking=False)
'''
if old_loop in main:
    main = main.replace(old_loop, new_loop, 1)
elif "msg = mav.recv_match(blocking=False)" not in main:
    raise SystemExit("MAVLink loop anchor not found")

collector_anchor = '''            msg_type = msg.get_type()
            t_stamp = getattr(msg, "_timestamp", 0.0)

            if t_stamp > 0:
'''
collector_insert = '''            msg_type = msg.get_type()
            t_stamp = getattr(msg, "_timestamp", 0.0)

            if t_stamp > 0:
                try:
                    mavlink_plot_collector.add(msg_type, msg.to_dict(), t_stamp)
                except Exception:
                    pass

'''
if "mavlink_plot_collector.add(msg_type, msg.to_dict(), t_stamp)" not in main:
    if collector_anchor not in main:
        raise SystemExit("collector packet anchor not found")
    main = main.replace(collector_anchor, collector_insert, 1)

old_sig = '''            is_error=False,
            is_pilot_action=False,
            event_type="SYSTEM",
        ):
'''
new_sig = '''            is_error=False,
            is_pilot_action=False,
            event_type="SYSTEM",
            severity=None,
        ):
'''
if old_sig in main and '"severity": severity,' not in main:
    main = main.replace(old_sig, new_sig, 1)

if '"severity": severity,' not in main:
    anchor = '''                    "eventType": event_type,
                    "isError": is_error,
'''
    if anchor not in main:
        raise SystemExit("event severity row anchor not found")
    main = main.replace(anchor, '''                    "eventType": event_type,
                    "severity": severity,
                    "isError": is_error,
''', 1)

if "severity=severity" not in main:
    marker = '''            add_event(
                full_txt,
                timestamp,
                mode,
                bool(thrust_match or is_serious_system_text(full_txt)),
                False,
                event_type,
            )
'''
    replacement = '''            add_event(
                full_txt,
                timestamp,
                mode,
                bool(thrust_match or is_serious_system_text(full_txt)),
                False,
                event_type,
                severity=severity,
            )
'''
    if marker not in main:
        raise SystemExit("STATUSTEXT add_event anchor not found")
    main = main.replace(marker, replacement, 1)

if '"mavlink_plot": mavlink_plot,' not in main:
    anchor = '''        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)

        return {
            "success": True,
            "graph_data": graph_data,
'''
    replacement = '''        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)
        mavlink_plot = mavlink_plot_collector.build(base_t)
        board_messages = build_board_messages(raw_timeline, base_t)

        return {
            "success": True,
            "graph_data": graph_data,
            "mavlink_plot": mavlink_plot,
            "board_messages": board_messages,
'''
    if anchor not in main:
        raise SystemExit("API result graph_data anchor not found")
    main = main.replace(anchor, replacement, 1)

# Frontend layout -----------------------------------------------------------
if 'id="mavlinkPlotPanel"' not in html:
    left_anchor = '''    <div class="graph-viewer-layout">
      <div class="graph-viewer-chart-wrap">
'''
    if left_anchor not in html:
        raise SystemExit("graph viewer left anchor not found")
    html = html.replace(left_anchor, '''    <div class="graph-viewer-layout">
      <div class="graph-viewer-left">
      <div class="graph-viewer-chart-wrap">
''', 1)

    close_anchor = '''        <div class="graph-help">Миша: наведи — перегляд моменту • клік — зафіксувати • колесо — zoom • потягни — панорама • подвійний клік — reset.</div>
      </div>
      <aside id="attitudePanel">
'''
    dynamic_panel = '''        <div class="graph-help">Миша: наведи — перегляд моменту • клік — зафіксувати • колесо — zoom • потягни — панорама • подвійний клік — reset.</div>
      </div>
      <section id="mavlinkPlotPanel" aria-label="Динамічні MAVLink параметри">
        <div class="mavlink-plot-head">
          <div><b>📡 MAVLink ПАРАМЕТРИ</b><span id="mavlinkPlotStatus">Обери поля для накладання на графік</span></div>
          <input id="mavlinkPlotSearch" type="search" placeholder="Пошук: rpm, battery, roll..." autocomplete="off">
          <button id="mavlinkPlotClear" type="button">Очистити</button>
        </div>
        <div id="mavlinkPlotGroups"></div>
      </section>
      </div>
      <aside id="attitudePanel">
'''
    if close_anchor not in html:
        raise SystemExit("graph viewer chart close anchor not found")
    html = html.replace(close_anchor, dynamic_panel, 1)

if 'id="boardMessagesPanel"' not in html:
    msg_anchor = '''        <div id="attitudeValues" class="attitude-values"></div>
      </aside>
'''
    msg_markup = '''        <div id="attitudeValues" class="attitude-values"></div>
        <section id="boardMessagesPanel" aria-label="Повідомлення борта">
          <div class="board-messages-title">⚠ ПОВІДОМЛЕННЯ БОРТА</div>
          <div class="board-messages-subtitle">Події в межах ±5 с від вибраного часу</div>
          <div id="boardMessagesList">Немає повідомлень</div>
        </section>
      </aside>
'''
    if msg_anchor not in html:
        raise SystemExit("attitude values close anchor not found")
    html = html.replace(msg_anchor, msg_markup, 1)

# Frontend styles -----------------------------------------------------------
if '#mavlinkPlotPanel{' not in html:
    css_anchor = '.graph-help{margin-top:8px;color:#64748b;font-size:11px;line-height:1.45}\n'
    css = r'''.graph-viewer-left{display:flex;flex-direction:column;gap:12px;min-width:0}
#mavlinkPlotPanel{border:1px solid #223044;border-radius:9px;background:#0b1118;padding:12px;min-width:0}
.mavlink-plot-head{display:grid;grid-template-columns:minmax(220px,1fr) minmax(220px,360px) auto;gap:9px;align-items:center;margin-bottom:10px}
.mavlink-plot-head>div{display:flex;flex-direction:column;gap:2px}.mavlink-plot-head b{font-size:12px;color:#f8fafc}.mavlink-plot-head span{font:10px monospace;color:#64748b}
#mavlinkPlotSearch{height:36px;border:1px solid #334155;border-radius:7px;background:#08111b;color:#f8fafc;padding:0 10px;outline:none}
#mavlinkPlotSearch:focus{border-color:#38bdf8;box-shadow:0 0 0 2px rgba(56,189,248,.08)}
#mavlinkPlotClear{height:36px;border:1px solid #475569;border-radius:7px;background:#0f1722;color:#cbd5e1;padding:0 12px;font-weight:800;cursor:pointer}
#mavlinkPlotGroups{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:7px;max-height:300px;overflow:auto;padding-right:3px}
.mavlink-message-group{border:1px solid #243244;border-radius:7px;background:#080d13;overflow:hidden;align-self:start}
.mavlink-message-group>summary{cursor:pointer;padding:8px 9px;color:#93c5fd;font:800 11px monospace;user-select:none;background:#0b121b}
.mavlink-field-list{padding:4px 7px 7px;display:grid;gap:3px}
.mavlink-field-row{display:grid;grid-template-columns:18px 12px minmax(0,1fr) auto;gap:6px;align-items:center;padding:4px 3px;border-radius:5px;color:#cbd5e1;font:10px monospace;cursor:pointer}
.mavlink-field-row:hover{background:rgba(56,189,248,.06)}.mavlink-field-row input{margin:0}.mavlink-field-color{width:10px;height:10px;border-radius:50%;box-shadow:0 0 6px currentColor}.mavlink-field-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.mavlink-field-unit{color:#64748b}
#boardMessagesPanel{margin-top:10px;border:1px solid #27364a;border-radius:8px;background:#080d13;padding:10px}
.board-messages-title{font-size:11px;font-weight:900;color:#f8fafc}.board-messages-subtitle{margin:2px 0 7px;color:#64748b;font:9px monospace}
#boardMessagesList{display:grid;gap:5px;max-height:190px;overflow:auto}.board-message{border-left:3px solid #475569;border-radius:5px;background:#0b1118;padding:6px 7px;font:10px/1.35 monospace;color:#cbd5e1}.board-message-time{font-weight:900;margin-right:6px}.board-message-error{border-left-color:#ef4444;background:rgba(239,68,68,.08)}.board-message-error .board-message-time{color:#f87171}.board-message-warning{border-left-color:#f59e0b;background:rgba(245,158,11,.07)}.board-message-warning .board-message-time{color:#fbbf24}.board-message-info{border-left-color:#38bdf8}.board-message-info .board-message-time{color:#7dd3fc}.board-message-recovery{border-left-color:#22c55e;background:rgba(34,197,94,.06)}.board-message-recovery .board-message-time{color:#4ade80}.board-message-empty{color:#64748b;font:10px monospace;padding:8px 2px}
@media(max-width:900px){.mavlink-plot-head{grid-template-columns:1fr}.mavlink-plot-head input,.mavlink-plot-head button{width:100%}#mavlinkPlotGroups{max-height:360px}}
'''
    if css_anchor not in html:
        raise SystemExit("graph CSS anchor not found")
    html = html.replace(css_anchor, css_anchor + css, 1)

# Extend graph state with dynamic selections.
old_state = "const graphViewerState={result:null,registry:[],metricKey:null,selectedTimeMs:null,viewStartMs:null,viewEndMs:null,pinned:false,dragging:false,lastX:0};"
new_state = "const graphViewerState={result:null,registry:[],metricKey:null,selectedTimeMs:null,viewStartMs:null,viewEndMs:null,pinned:false,dragging:false,lastX:0,selectedSeries:new Set(),seriesColors:new Map(),dynamicCatalog:[]};"
if old_state in html:
    html = html.replace(old_state, new_state, 1)
elif "selectedSeries:new Set()" not in html:
    raise SystemExit("graphViewerState anchor not found")

# Add a later enhancement script that overrides only graph-viewer drawing/selection.
if 'id="dynamicMavlinkPlotEnhancement"' not in html:
    script_anchor = '''</section>

<script>
(function(){
  const TEMP_WAIT_IMAGE='https://i.imgur.com/CduyK.jpeg';
'''
    enhancement = r'''</section>

<script id="dynamicMavlinkPlotEnhancement">
const MAX_DYNAMIC_UNIT_GROUPS=4;
const BOARD_MESSAGE_WINDOW_MS=5000;

function dynamicEscapeHtml(value){
  return String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

function buildDynamicMavlinkCatalog(){
  const groups=graphViewerState.result?.mavlink_plot?.groups||{};
  const out=[];
  Object.keys(groups).sort().forEach(message=>{
    const fields=groups[message]||{};
    Object.keys(fields).sort().forEach(field=>{
      const raw=fields[field]||{};
      const times=Array.isArray(raw.time_ms)?raw.time_ms.map(Number):[];
      const values=Array.isArray(raw.values)?raw.values.map(Number):[];
      const cleanT=[],cleanV=[];
      for(let i=0;i<Math.min(times.length,values.length);i++){
        if(Number.isFinite(times[i])&&Number.isFinite(values[i])){cleanT.push(times[i]);cleanV.push(values[i]);}
      }
      if(!cleanT.length)return;
      out.push({message,field,id:String(raw.id||`${message}.${field}`),label:String(raw.label||`${message}.${field}`),unit:String(raw.unit||''),times:cleanT,values:cleanV});
    });
  });
  graphViewerState.dynamicCatalog=out;
  return out;
}

function seriesColorFor(id){
  if(graphViewerState.seriesColors.has(id))return graphViewerState.seriesColors.get(id);
  const palette=['#38bdf8','#f59e0b','#22c55e','#f472b6','#a78bfa','#fb7185','#2dd4bf','#facc15','#60a5fa','#fb923c','#c084fc','#34d399'];
  let h=2166136261;
  for(const ch of String(id)){h^=ch.charCodeAt(0);h=Math.imul(h,16777619)>>>0;}
  const color=palette[h%palette.length];graphViewerState.seriesColors.set(id,color);return color;
}

function groupSeriesByUnit(series){
  const groups=new Map();
  (series||[]).forEach(s=>{const unit=s.unit||'native';if(!groups.has(unit))groups.set(unit,[]);groups.get(unit).push(s);});
  return groups;
}

function activeGraphSeries(){
  const chosen=(graphViewerState.dynamicCatalog||[]).filter(x=>graphViewerState.selectedSeries.has(x.id));
  if(chosen.length)return chosen.map(x=>({...x,color:seriesColorFor(x.id)}));
  const metric=graphMetricByKey(graphViewerState.metricKey);
  if(!metric||!metric.available)return [];
  const base=graphSeries(metric);
  return [{id:`base:${metric.key}`,label:metric.label,unit:metric.unit||'',times:base.times,values:base.values,color:'#38bdf8'}];
}

function renderMavlinkFieldBrowser(){
  const root=document.getElementById('mavlinkPlotGroups'),search=document.getElementById('mavlinkPlotSearch');
  if(!root)return;
  const q=String(search?.value||'').trim().toLowerCase();
  const catalog=graphViewerState.dynamicCatalog?.length?graphViewerState.dynamicCatalog:buildDynamicMavlinkCatalog();
  const grouped=new Map();
  catalog.forEach(item=>{
    if(q&&!`${item.message} ${item.field} ${item.label} ${item.unit}`.toLowerCase().includes(q))return;
    if(!grouped.has(item.message))grouped.set(item.message,[]);grouped.get(item.message).push(item);
  });
  if(!grouped.size){root.innerHTML='<div class="board-message-empty">Немає доступних числових MAVLink параметрів</div>';return;}
  root.innerHTML=[...grouped.entries()].map(([message,items])=>{
    const open=q||items.some(x=>graphViewerState.selectedSeries.has(x.id))?' open':'';
    return `<details class="mavlink-message-group"${open}><summary>${dynamicEscapeHtml(message)} • ${items.length}</summary><div class="mavlink-field-list">${items.map(item=>{
      const checked=graphViewerState.selectedSeries.has(item.id)?' checked':'';
      const color=seriesColorFor(item.id);
      return `<label class="mavlink-field-row" title="${dynamicEscapeHtml(item.label)}"><input type="checkbox" data-mavlink-series="${dynamicEscapeHtml(item.id)}"${checked}><span class="mavlink-field-color" style="background:${color};color:${color}"></span><span class="mavlink-field-name">${dynamicEscapeHtml(item.field)}</span><span class="mavlink-field-unit">${dynamicEscapeHtml(item.unit||'native')}</span></label>`;
    }).join('')}</div></details>`;
  }).join('');
  root.querySelectorAll('input[data-mavlink-series]').forEach(box=>box.addEventListener('change',()=>setMavlinkSeriesSelected(box.dataset.mavlinkSeries,box.checked)));
}

function dynamicGraphStatus(text,warning=false){
  const el=document.getElementById('mavlinkPlotStatus');if(!el)return;el.textContent=text;el.style.color=warning?'#fbbf24':'#64748b';
}

function setMavlinkSeriesSelected(id,checked){
  const item=(graphViewerState.dynamicCatalog||[]).find(x=>x.id===id);if(!item)return;
  if(checked){
    const future=(graphViewerState.dynamicCatalog||[]).filter(x=>graphViewerState.selectedSeries.has(x.id)||x.id===id);
    if(groupSeriesByUnit(future).size>MAX_DYNAMIC_UNIT_GROUPS){dynamicGraphStatus(`Максимум ${MAX_DYNAMIC_UNIT_GROUPS} різні групи одиниць одночасно`,true);renderMavlinkFieldBrowser();return;}
    graphViewerState.selectedSeries.add(id);
  }else graphViewerState.selectedSeries.delete(id);
  const select=document.getElementById('graphMetricSelect');if(select&&graphViewerState.selectedSeries.size)select.value='__custom';
  dynamicGraphStatus(graphViewerState.selectedSeries.size?`Обрано серій: ${graphViewerState.selectedSeries.size}`:'Обери поля для накладання на графік');
  resetDynamicGraphView();renderMavlinkFieldBrowser();renderGraphSeries(graphMetricByKey(graphViewerState.metricKey));
}

function resetDynamicGraphView(){
  const series=activeGraphSeries(),allTimes=series.flatMap(s=>s.times).filter(Number.isFinite);
  if(!allTimes.length){graphViewerState.viewStartMs=null;graphViewerState.viewEndMs=null;return;}
  graphViewerState.viewStartMs=Math.min(...allTimes);graphViewerState.viewEndMs=Math.max(...allTimes);
  if(graphViewerState.viewEndMs<=graphViewerState.viewStartMs)graphViewerState.viewEndMs=graphViewerState.viewStartMs+1000;
}

function dynamicPresetIds(name){
  const c=graphViewerState.dynamicCatalog||[];
  if(name==='power')return c.filter(x=>(x.message==='SYS_STATUS'&&/voltage_battery|current_battery|load/i.test(x.field))||(x.message==='EFI_STATUS'&&/engine_load|rpm/i.test(x.field))).slice(0,6).map(x=>x.id);
  if(name==='radio')return c.filter(x=>/RADIO/.test(x.message)&&/rssi|remrssi|noise|remnoise|rxerrors|fixed/i.test(x.field)).slice(0,6).map(x=>x.id);
  if(name==='attitude')return c.filter(x=>x.message==='ATTITUDE'&&/^(roll|pitch|yaw|rollspeed|pitchspeed|yawspeed)$/.test(x.field)).slice(0,6).map(x=>x.id);
  if(name==='esc')return c.filter(x=>/^ESC/.test(x.message)&&/rpm|current|voltage|temperature/i.test(x.field)).slice(0,8).map(x=>x.id);
  return [];
}

function applyDynamicPreset(name){
  graphViewerState.selectedSeries.clear();
  dynamicPresetIds(name).forEach(id=>graphViewerState.selectedSeries.add(id));
  resetDynamicGraphView();renderMavlinkFieldBrowser();renderGraphSeries(graphMetricByKey(graphViewerState.metricKey));
}

function dynamicGeometry(canvas){return {left:64,right:22,top:62,bottom:48,width:canvas.clientWidth||800,height:canvas.clientHeight||520};}

function visibleSeriesStats(series,viewStart,viewEnd){
  const groups=groupSeriesByUnit(series),scales=new Map();
  groups.forEach((items,unit)=>{
    const vals=[];items.forEach(s=>{for(let i=0;i<s.times.length;i++)if(s.times[i]>=viewStart&&s.times[i]<=viewEnd&&Number.isFinite(s.values[i]))vals.push(s.values[i]);});
    if(!vals.length)return;let min=Math.min(...vals),max=Math.max(...vals);if(max===min){max+=1;min-=1;}const pad=(max-min)*.08;scales.set(unit,{min:min-pad,max:max+pad});
  });
  return scales;
}

function renderGraphSeries(metric){
  const canvas=document.getElementById('graphCanvas');if(!canvas)return;
  const series=activeGraphSeries(),noData=document.getElementById('graphNoData');
  if(!series.length){if(noData)noData.hidden=false;return;}if(noData)noData.hidden=true;
  if(!Number.isFinite(graphViewerState.viewStartMs)||!Number.isFinite(graphViewerState.viewEndMs))resetDynamicGraphView();
  const dpr=Math.max(1,window.devicePixelRatio||1),w=Math.max(320,canvas.clientWidth||800),h=Math.max(280,canvas.clientHeight||520);canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
  const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  const g=dynamicGeometry(canvas),x0=g.left,x1=w-g.right,y0=g.top,y1=h-g.bottom,viewStart=graphViewerState.viewStartMs,viewEnd=graphViewerState.viewEndMs;
  const X=t=>x0+(t-viewStart)/(viewEnd-viewStart||1)*(x1-x0),scales=visibleSeriesStats(series,viewStart,viewEnd),groups=[...scales.entries()];
  ctx.strokeStyle='#243244';ctx.lineWidth=1;ctx.fillStyle='#94a3b8';ctx.font='11px monospace';
  for(let i=0;i<=5;i++){const yy=y0+(y1-y0)*i/5;ctx.beginPath();ctx.moveTo(x0,yy);ctx.lineTo(x1,yy);ctx.stroke();if(groups[0]){const [unit,scale]=groups[0],v=scale.max-(scale.max-scale.min)*i/5;ctx.fillText(v.toFixed(Math.abs(v)<10?2:1),5,yy+4);}}
  for(let i=0;i<=6;i++){const xx=x0+(x1-x0)*i/6;ctx.beginPath();ctx.moveTo(xx,y0);ctx.lineTo(xx,y1);ctx.stroke();ctx.fillText(formatGraphTime(viewStart+(viewEnd-viewStart)*i/6),Math.max(2,xx-28),h-18);}
  series.forEach(s=>{
    const scale=scales.get(s.unit||'native');if(!scale)return;const Y=v=>y1-(v-scale.min)/(scale.max-scale.min||1)*(y1-y0);let started=false;ctx.strokeStyle=s.color;ctx.lineWidth=1.9;ctx.beginPath();
    for(let i=0;i<s.times.length;i++){const t=s.times[i],v=s.values[i];if(t<viewStart||t>viewEnd||!Number.isFinite(v))continue;const xx=X(t),yy=Y(v);if(!started){ctx.moveTo(xx,yy);started=true;}else ctx.lineTo(xx,yy);}if(started)ctx.stroke();
  });
  let lx=x0,ly=18;ctx.font='bold 10px monospace';series.slice(0,8).forEach(s=>{const text=`${s.label}${s.unit?` [${s.unit}]`:''}`;const width=Math.min(210,ctx.measureText(text).width+22);if(lx+width>x1){lx=x0;ly+=16;}ctx.fillStyle=s.color;ctx.fillRect(lx,ly-7,10,3);ctx.fillStyle='#dbeafe';ctx.fillText(text,lx+14,ly);lx+=width+8;});
  if(groups.length>1){ctx.font='9px monospace';let yy=y0+4;groups.slice(1,MAX_DYNAMIC_UNIT_GROUPS).forEach(([unit,scale])=>{ctx.fillStyle='#64748b';ctx.fillText(`${unit}: ${scale.min.toFixed(1)}…${scale.max.toFixed(1)}`,x1-145,yy);yy+=12;});}
  const sel=graphViewerState.selectedTimeMs;if(Number.isFinite(sel)&&sel>=viewStart&&sel<=viewEnd){const sx=X(sel);ctx.strokeStyle='#facc15';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(sx,y0);ctx.lineTo(sx,y1);ctx.stroke();}
}

function renderBoardMessagesAtTime(timeMs){
  const root=document.getElementById('boardMessagesList');if(!root)return;
  const messages=Array.isArray(graphViewerState.result?.board_messages)?graphViewerState.result.board_messages:[];
  const rows=messages.filter(m=>Number.isFinite(Number(m.time_ms))&&Math.abs(Number(m.time_ms)-timeMs)<=BOARD_MESSAGE_WINDOW_MS).sort((a,b)=>Math.abs(Number(a.time_ms)-timeMs)-Math.abs(Number(b.time_ms)-timeMs)||Number(a.time_ms)-Number(b.time_ms)).slice(0,12);
  if(!rows.length){root.innerHTML='<div class="board-message-empty">Немає повідомлень</div>';return;}
  root.innerHTML=rows.map(m=>{const level=['error','warning','info','recovery'].includes(m.level)?m.level:'info';return `<div class="board-message board-message-${level}"><span class="board-message-time">${formatGraphTime(Number(m.time_ms))}</span>${dynamicEscapeHtml(m.text)}</div>`;}).join('');
}

function selectGraphTime(timeMs){
  if(!Number.isFinite(timeMs))return;
  graphViewerState.selectedTimeMs=timeMs;updateAttitudeAtTime(timeMs);renderBoardMessagesAtTime(timeMs);renderGraphSeries(graphMetricByKey(graphViewerState.metricKey));
}

function graphTimeFromClientX(clientX){
  const canvas=document.getElementById('graphCanvas');if(!canvas||!Number.isFinite(graphViewerState.viewStartMs)||!Number.isFinite(graphViewerState.viewEndMs))return null;const rect=canvas.getBoundingClientRect(),g=dynamicGeometry(canvas),x=clientX-rect.left;if(x<g.left||x>rect.width-g.right)return null;return graphViewerState.viewStartMs+(x-g.left)/(rect.width-g.left-g.right)*(graphViewerState.viewEndMs-graphViewerState.viewStartMs);
}

function dynamicTooltipText(timeMs){
  const lines=[formatGraphTime(timeMs)];activeGraphSeries().forEach(s=>{const i=nearestSampleIndex(s.times,timeMs);if(i>=0&&Number.isFinite(s.values[i]))lines.push(`${s.label}: ${s.values[i].toFixed(Math.abs(s.values[i])<10?2:1)} ${s.unit||''}`);});return lines.join(' • ');
}

function ensureGraphCanvasEvents(){
  const canvas=document.getElementById('graphCanvas');if(!canvas||canvas.dataset.dynamicGraphBound)return;canvas.dataset.dynamicGraphBound='1';const tip=document.getElementById('graphTooltip');
  canvas.addEventListener('mousemove',e=>{if(graphViewerState.dragging){const rect=canvas.getBoundingClientRect(),span=graphViewerState.viewEndMs-graphViewerState.viewStartMs,dt=-(e.clientX-graphViewerState.lastX)/Math.max(1,rect.width-86)*span;graphViewerState.viewStartMs+=dt;graphViewerState.viewEndMs+=dt;graphViewerState.lastX=e.clientX;renderGraphSeries();return;}const t=graphTimeFromClientX(e.clientX);if(!Number.isFinite(t))return;if(!graphViewerState.pinned)selectGraphTime(t);if(tip){tip.style.display='block';tip.style.left=(e.offsetX+14)+'px';tip.style.top=(e.offsetY+14)+'px';tip.textContent=dynamicTooltipText(t);}});
  canvas.addEventListener('mouseleave',()=>{if(tip)tip.style.display='none';graphViewerState.dragging=false;});canvas.addEventListener('mousedown',e=>{if(e.button===0){graphViewerState.dragging=true;graphViewerState.lastX=e.clientX;}});window.addEventListener('mouseup',()=>{graphViewerState.dragging=false;});
  canvas.addEventListener('click',e=>{const t=graphTimeFromClientX(e.clientX);if(Number.isFinite(t)){graphViewerState.pinned=true;selectGraphTime(t);}});canvas.addEventListener('dblclick',()=>{graphViewerState.pinned=false;resetDynamicGraphView();renderGraphSeries();});
  canvas.addEventListener('wheel',e=>{e.preventDefault();const center=graphTimeFromClientX(e.clientX);if(!Number.isFinite(center))return;const span=Math.max(1000,graphViewerState.viewEndMs-graphViewerState.viewStartMs),factor=e.deltaY>0?1.25:.8,newSpan=Math.max(1000,span*factor),ratio=(center-graphViewerState.viewStartMs)/span;graphViewerState.viewStartMs=center-newSpan*ratio;graphViewerState.viewEndMs=graphViewerState.viewStartMs+newSpan;renderGraphSeries();},{passive:false});
}

function openGraphViewer(result){
  graphViewerState.result=result||window.__lastAnalysisResult||null;graphViewerState.registry=buildGraphMetricRegistry(graphViewerState.result?.graph_data||{});graphViewerState.selectedSeries.clear();graphViewerState.seriesColors.clear();buildDynamicMavlinkCatalog();
  const overlay=document.getElementById('graphViewerOverlay'),select=document.getElementById('graphMetricSelect');if(!overlay||!select)return;const available=graphViewerState.registry.filter(x=>x.available);
  select.innerHTML=available.map(x=>`<option value="${x.key}">${x.label} (${x.unit})</option>`).join('')+'<option value="__preset_power">Power preset</option><option value="__preset_radio">Radio preset</option><option value="__preset_attitude">Attitude preset</option><option value="__preset_esc">ESC preset</option><option value="__custom">Custom</option>';
  overlay.hidden=false;overlay.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';document.getElementById('graphViewerClose').onclick=closeGraphViewer;document.getElementById('graphResetZoom').onclick=()=>{resetDynamicGraphView();renderGraphSeries();};
  const search=document.getElementById('mavlinkPlotSearch'),clear=document.getElementById('mavlinkPlotClear');if(search){search.value='';search.oninput=renderMavlinkFieldBrowser;}if(clear)clear.onclick=()=>{graphViewerState.selectedSeries.clear();dynamicGraphStatus('Обери поля для накладання на графік');renderMavlinkFieldBrowser();resetDynamicGraphView();renderGraphSeries();};renderMavlinkFieldBrowser();
  select.onchange=()=>{const v=select.value;if(v.startsWith('__preset_')){applyDynamicPreset(v.replace('__preset_',''));select.value='__custom';return;}if(v==='__custom')return;graphViewerState.selectedSeries.clear();setGraphMetric(v);renderMavlinkFieldBrowser();};
  ensureGraphCanvasEvents();if(!available.length&&!graphViewerState.dynamicCatalog.length){document.getElementById('graphNoData').hidden=false;updateAttitudeAtTime(0);renderBoardMessagesAtTime(0);return;}
  const preferred=available.find(x=>x.key==='altitude')||available[0];if(preferred){select.value=preferred.key;graphViewerState.metricKey=preferred.key;resetDynamicGraphView();if(!Number.isFinite(graphViewerState.selectedTimeMs))graphViewerState.selectedTimeMs=activeGraphSeries()[0]?.times?.[0]??0;}else{select.value='__custom';resetDynamicGraphView();graphViewerState.selectedTimeMs=graphViewerState.viewStartMs||0;}
  renderGraphSeries();updateAttitudeAtTime(graphViewerState.selectedTimeMs);renderBoardMessagesAtTime(graphViewerState.selectedTimeMs);
}

window.addEventListener('resize',()=>{const o=document.getElementById('graphViewerOverlay');if(o&&!o.hidden)renderGraphSeries();});
</script>

<script>
(function(){
  const TEMP_WAIT_IMAGE='https://i.imgur.com/CduyK.jpeg';
'''
    if script_anchor not in html:
        raise SystemExit("dynamic enhancement script anchor not found")
    html = html.replace(script_anchor, enhancement, 1)

main_path.write_text(main, encoding="utf-8")
html_path.write_text(html, encoding="utf-8")
print("Applied dynamic MAVLink plot backend + field browser + synchronized board messages")
