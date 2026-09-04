from pathlib import Path


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"anchor not found: {label}")
    return text.replace(old, new, 1)


# ---------------- backend ----------------
backend_path = Path("backend/main.py")
backend = backend_path.read_text(encoding="utf-8")

if "def _build_graph_data(" not in backend:
    helper = r'''

def _timeline_graph_time_ms(value):
    m = re.match(r"^(-)?(\d+):(\d+(?:\.\d+)?)$", str(value or "").strip())
    if not m:
        return None
    total = int(m.group(2)) * 60.0 + float(m.group(3))
    if m.group(1):
        total = -total
    return int(round(total * 1000.0))


def _graph_numeric(value):
    if valid_number(value):
        return float(value)
    m = re.search(r"-?\d+(?:[\.,]\d+)?", str(value or ""))
    if not m:
        return None
    try:
        number = float(m.group(0).replace(",", "."))
    except ValueError:
        return None
    return number if valid_number(number) else None


def _build_graph_data(timeline_rows, attitude_samples=None, base_timestamp=0.0):
    """Build finite telemetry series for the interactive graph viewer.

    Timeline snapshots provide low-rate values already validated by the analyzer.
    ATTITUDE samples are kept separately at native MAVLink rate for a smoother
    artificial horizon. Missing series are omitted entirely.
    """
    out = {}

    def append_pair(time_key, value_key, time_ms, value):
        if time_ms is None or not valid_number(value):
            return
        out.setdefault(time_key, []).append(int(round(float(time_ms))))
        out.setdefault(value_key, []).append(float(value))

    for row in timeline_rows or []:
        if not isinstance(row, dict) or row.get("eventType") != "SNAPSHOT":
            continue
        t_ms = _timeline_graph_time_ms(row.get("time"))
        if t_ms is None:
            continue

        append_pair("altitude_time_ms", "altitude_m", t_ms, _graph_numeric(row.get("alt")))
        append_pair("voltage_time_ms", "voltage_v", t_ms, row.get("volt"))
        append_pair("current_time_ms", "current_a", t_ms, row.get("curr"))
        append_pair("engine_load_time_ms", "engine_load_pct", t_ms, row.get("engineLoad"))
        append_pair("radio_time_ms", "radio_dbm", t_ms, row.get("dbm"))
        append_pair("vertical_speed_time_ms", "vertical_speed_down_ms", t_ms, row.get("verticalSpeedDown"))

        rc = row.get("rcChannels") or {}
        if isinstance(rc, dict):
            for ch in range(1, 19):
                append_pair(
                    f"rc_ch{ch}_time_ms",
                    f"rc_ch{ch}_pwm",
                    t_ms,
                    rc.get(f"ch{ch}"),
                )

        esc = row.get("esc") or []
        if isinstance(esc, list):
            for item in esc:
                if not isinstance(item, dict):
                    continue
                esc_id = item.get("id")
                if not valid_number(esc_id):
                    continue
                esc_id = int(float(esc_id))
                if not 1 <= esc_id <= 4:
                    continue
                append_pair(f"esc{esc_id}_rpm_time_ms", f"esc{esc_id}_rpm", t_ms, item.get("rpm"))
                append_pair(f"esc{esc_id}_current_time_ms", f"esc{esc_id}_current_a", t_ms, item.get("current"))

    attitude_time = []
    roll_values = []
    pitch_values = []
    yaw_values = []
    for sample in attitude_samples or []:
        if not isinstance(sample, dict):
            continue
        ts = sample.get("timestamp")
        roll = sample.get("roll")
        pitch = sample.get("pitch")
        yaw = sample.get("yaw")
        if not all(valid_number(v) for v in (ts, roll, pitch, yaw)):
            continue
        t_ms = int(round((float(ts) - float(base_timestamp or 0.0)) * 1000.0))
        attitude_time.append(t_ms)
        roll_values.append(math.degrees(float(roll)))
        pitch_values.append(math.degrees(float(pitch)))
        yaw_values.append(math.degrees(float(yaw)) % 360.0)

    if attitude_time:
        out["attitude_time_ms"] = attitude_time
        out["roll_deg"] = roll_values
        out["pitch_deg"] = pitch_values
        out["yaw_deg"] = yaw_values

    return out

'''
    backend = replace_once(backend, "def heading_difference_deg(a, b):", helper + "def heading_difference_deg(a, b):", "backend helper insertion")

if "attitude_graph_samples = []" not in backend:
    backend = replace_once(
        backend,
        "        attitude_critical_peak = None\n\n        # VTX",
        "        attitude_critical_peak = None\n        # Native-rate ATTITUDE stream for the graph/aviation-horizon viewer.\n        attitude_graph_samples = []\n\n        # VTX",
        "attitude graph samples init",
    )

if "attitude_graph_samples.append" not in backend:
    anchor = "            elif msg_type == \"ATTITUDE\":\n                if valid_number(msg.roll):"
    replacement = "            elif msg_type == \"ATTITUDE\":\n                if (\n                    current_timestamp > 0\n                    and valid_number(getattr(msg, \"roll\", None))\n                    and valid_number(getattr(msg, \"pitch\", None))\n                    and valid_number(getattr(msg, \"yaw\", None))\n                ):\n                    attitude_graph_samples.append({\n                        \"timestamp\": current_timestamp,\n                        \"roll\": float(msg.roll),\n                        \"pitch\": float(msg.pitch),\n                        \"yaw\": float(msg.yaw),\n                    })\n\n                if valid_number(msg.roll):"
    backend = replace_once(backend, anchor, replacement, "ATTITUDE capture")

if '"graph_data": graph_data,' not in backend:
    backend = replace_once(
        backend,
        "        return {\n            \"success\": True,",
        "        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)\n\n        return {\n            \"success\": True,\n            \"graph_data\": graph_data,",
        "graph_data response",
    )

backend_path.write_text(backend, encoding="utf-8")


# ---------------- frontend ----------------
index_path = Path("index.html")
html = index_path.read_text(encoding="utf-8")

if "/* GRAPH ATTITUDE VIEWER */" not in html:
    css = r'''
/* GRAPH ATTITUDE VIEWER */
#graphViewerBtn{position:fixed;right:22px;bottom:22px;z-index:9000;height:48px;padding:0 18px;border:1px solid #38bdf8;border-radius:9px;background:#082f49;color:#e0f2fe;font-weight:900;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.32)}
#graphViewerOverlay{position:fixed;inset:0;z-index:9500;background:#05080d;color:#e5edf5;overflow:auto;padding:18px}
#graphViewerOverlay[hidden]{display:none!important}
.graph-viewer-shell{max-width:1500px;margin:0 auto}
.graph-viewer-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px;padding:10px;border:1px solid #223044;border-radius:9px;background:#0b1118}
.graph-viewer-toolbar button,.graph-viewer-toolbar select{height:40px;border:1px solid #334155;border-radius:7px;background:#0f1722;color:#e5edf5;padding:0 12px;font-size:13px}
.graph-viewer-toolbar button{cursor:pointer;font-weight:800}
.graph-viewer-title{font-size:15px;font-weight:900;margin-right:auto;color:#f8fafc}
.graph-viewer-layout{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:14px;align-items:start}
.graph-viewer-chart-wrap{position:relative;min-width:0;border:1px solid #223044;border-radius:9px;background:#080d13;padding:10px}
#graphCanvas{width:100%;height:520px;display:block;cursor:crosshair;touch-action:none}
#graphTooltip{position:absolute;pointer-events:none;display:none;padding:6px 8px;border:1px solid #334155;border-radius:6px;background:rgba(2,6,23,.94);color:#f8fafc;font:12px monospace;white-space:nowrap;z-index:2}
#graphNoData{padding:32px;text-align:center;color:#94a3b8}
#attitudePanel{border:1px solid #223044;border-radius:9px;background:#0b1118;padding:14px;position:sticky;top:16px}
.attitude-title{font-size:13px;font-weight:900;margin-bottom:10px;color:#f8fafc}
#attitudeHorizon{width:250px;height:250px;max-width:100%;aspect-ratio:1;border:7px solid #27364a;border-radius:50%;overflow:hidden;position:relative;margin:0 auto 12px;background:#111827;box-shadow:inset 0 0 0 2px #0f172a}
#attitudeScene{position:absolute;left:50%;top:50%;width:180%;height:180%;transform:translate(-50%,-50%);transform-origin:50% 50%;background:linear-gradient(to bottom,#2b78c5 0%,#4f9ad7 49.4%,#f5f5f4 49.5%,#f5f5f4 50.5%,#8a5a36 50.6%,#5f3b27 100%);will-change:transform}
.attitude-pitch-line{position:absolute;left:50%;top:50%;width:34%;height:1px;background:rgba(255,255,255,.82);transform:translate(-50%,-50%)}
.attitude-pitch-line::before,.attitude-pitch-line::after{content:'';position:absolute;top:-44px;width:50%;height:1px;background:rgba(255,255,255,.45)}
.attitude-pitch-line::before{left:25%}.attitude-pitch-line::after{left:25%;top:44px}
.attitude-aircraft{position:absolute;left:50%;top:50%;width:54%;height:4px;background:#facc15;transform:translate(-50%,-50%);z-index:3;box-shadow:0 0 0 1px #111827}
.attitude-aircraft::before,.attitude-aircraft::after{content:'';position:absolute;top:-5px;width:22px;height:14px;border-top:4px solid #facc15}
.attitude-aircraft::before{left:-2px;transform:rotate(18deg)}.attitude-aircraft::after{right:-2px;transform:rotate(-18deg)}
.attitude-center-dot{position:absolute;left:50%;top:50%;width:8px;height:8px;border-radius:50%;background:#facc15;transform:translate(-50%,-50%);z-index:4}
.attitude-values{display:grid;grid-template-columns:1fr 1fr;gap:7px;font:12px monospace}
.attitude-value{border:1px solid #253246;border-radius:6px;padding:8px;background:#080d13}.attitude-value b{display:block;color:#7dd3fc;margin-bottom:2px}
.graph-help{margin-top:8px;color:#64748b;font-size:11px;line-height:1.45}
@media(max-width:900px){.graph-viewer-layout{grid-template-columns:1fr}#attitudePanel{position:static}#graphCanvas{height:390px}#graphViewerBtn{right:12px;bottom:12px}.graph-viewer-title{width:100%}}
'''
    html = replace_once(html, "</style>", css + "\n</style>", "viewer css")

if 'id="graphViewerOverlay"' not in html:
    markup = r'''
<button id="graphViewerBtn" type="button" hidden>📈 Переглянути графік</button>
<section id="graphViewerOverlay" hidden aria-hidden="true">
  <div class="graph-viewer-shell">
    <div class="graph-viewer-toolbar">
      <button id="graphViewerClose" type="button">← Назад до аналізу</button>
      <div class="graph-viewer-title">📈 ГРАФІК TLOG + АВІАГОРИЗОНТ</div>
      <label for="graphMetricSelect">Показник:</label>
      <select id="graphMetricSelect"></select>
      <button id="graphResetZoom" type="button">Скинути zoom</button>
    </div>
    <div class="graph-viewer-layout">
      <div class="graph-viewer-chart-wrap">
        <canvas id="graphCanvas"></canvas>
        <div id="graphTooltip"></div>
        <div id="graphNoData" hidden>Немає даних у цьому TLOG</div>
        <div class="graph-help">Миша: наведи — перегляд моменту • клік — зафіксувати • колесо — zoom • потягни — панорама • подвійний клік — reset.</div>
      </div>
      <aside id="attitudePanel">
        <div class="attitude-title">✈ АВІАГОРИЗОНТ</div>
        <div id="attitudeHorizon" aria-label="Авіагоризонт">
          <div id="attitudeScene"><div class="attitude-pitch-line"></div></div>
          <div class="attitude-aircraft"></div><div class="attitude-center-dot"></div>
        </div>
        <div id="attitudeValues" class="attitude-values"></div>
      </aside>
    </div>
  </div>
</section>
'''
    pos = html.rfind("<script>")
    if pos < 0:
        raise SystemExit("script anchor not found")
    html = html[:pos] + markup + "\n" + html[pos:]

if "const graphViewerState=" not in html:
    js = r'''

const graphViewerState={result:null,registry:[],metricKey:null,selectedTimeMs:null,viewStartMs:null,viewEndMs:null,pinned:false,dragging:false,lastX:0};

function buildGraphMetricRegistry(graphData){
  const d=graphData||{};
  const defs=[
    {key:'altitude',label:'Висота',unit:'м',timeKey:'altitude_time_ms',valueKey:'altitude_m'},
    {key:'voltage',label:'Напруга АКБ',unit:'V',timeKey:'voltage_time_ms',valueKey:'voltage_v'},
    {key:'current',label:'Струм',unit:'A',timeKey:'current_time_ms',valueKey:'current_a'},
    {key:'engine_load',label:'Engine Load',unit:'%',timeKey:'engine_load_time_ms',valueKey:'engine_load_pct'},
    {key:'radio_dbm',label:'Радіосигнал',unit:'dBm',timeKey:'radio_time_ms',valueKey:'radio_dbm'},
    {key:'vertical_speed',label:'Вертикальна швидкість вниз',unit:'м/с',timeKey:'vertical_speed_time_ms',valueKey:'vertical_speed_down_ms'},
    {key:'roll',label:'Roll',unit:'°',timeKey:'attitude_time_ms',valueKey:'roll_deg'},
    {key:'pitch',label:'Pitch',unit:'°',timeKey:'attitude_time_ms',valueKey:'pitch_deg'},
    {key:'yaw',label:'Yaw',unit:'°',timeKey:'attitude_time_ms',valueKey:'yaw_deg'}
  ];
  for(let ch=1;ch<=18;ch++)defs.push({key:`rc_ch${ch}`,label:`RC CH${ch}`,unit:'us',timeKey:`rc_ch${ch}_time_ms`,valueKey:`rc_ch${ch}_pwm`});
  for(let esc=1;esc<=4;esc++){
    defs.push({key:`esc${esc}_rpm`,label:`ESC${esc} RPM`,unit:'RPM',timeKey:`esc${esc}_rpm_time_ms`,valueKey:`esc${esc}_rpm`});
    defs.push({key:`esc${esc}_current`,label:`ESC${esc} струм`,unit:'A',timeKey:`esc${esc}_current_time_ms`,valueKey:`esc${esc}_current_a`});
  }
  return defs.map(x=>({...x,available:Array.isArray(d[x.timeKey])&&Array.isArray(d[x.valueKey])&&d[x.timeKey].length>0&&d[x.valueKey].length>0}));
}

function nearestSampleIndex(times,targetMs){
  if(!Array.isArray(times)||!times.length||!Number.isFinite(targetMs))return -1;
  let lo=0,hi=times.length-1;
  while(lo<hi){const mid=Math.floor((lo+hi)/2);if(times[mid]<targetMs)lo=mid+1;else hi=mid;}
  if(lo===0)return 0;
  const a=lo-1,b=lo;
  return Math.abs(times[a]-targetMs)<=Math.abs(times[b]-targetMs)?a:b;
}

function formatGraphTime(ms){
  if(!Number.isFinite(ms))return '—';
  const sign=ms<0?'-':'';let s=Math.abs(ms)/1000;const m=Math.floor(s/60);s-=m*60;return `${sign}${String(m).padStart(2,'0')}:${s.toFixed(3).padStart(6,'0')}`;
}

function graphMetricByKey(key){return graphViewerState.registry.find(x=>x.key===key)||null;}
function graphSeries(metric){
  const d=graphViewerState.result?.graph_data||{};if(!metric)return {times:[],values:[]};
  const times=d[metric.timeKey]||[],values=d[metric.valueKey]||[];const outT=[],outV=[];
  for(let i=0;i<Math.min(times.length,values.length);i++){const t=Number(times[i]),v=Number(values[i]);if(Number.isFinite(t)&&Number.isFinite(v)){outT.push(t);outV.push(v);}}
  return {times:outT,values:outV};
}

function openGraphViewer(result){
  graphViewerState.result=result||window.__lastAnalysisResult||null;
  graphViewerState.registry=buildGraphMetricRegistry(graphViewerState.result?.graph_data||{});
  const overlay=document.getElementById('graphViewerOverlay'),select=document.getElementById('graphMetricSelect');
  if(!overlay||!select)return;
  const available=graphViewerState.registry.filter(x=>x.available);
  select.innerHTML=available.map(x=>`<option value="${x.key}">${x.label} (${x.unit})</option>`).join('');
  overlay.hidden=false;overlay.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
  document.getElementById('graphViewerClose').onclick=closeGraphViewer;
  document.getElementById('graphResetZoom').onclick=()=>{const m=graphMetricByKey(graphViewerState.metricKey);resetGraphView(m);renderGraphSeries(m);};
  select.onchange=()=>setGraphMetric(select.value);
  ensureGraphCanvasEvents();
  if(!available.length){document.getElementById('graphNoData').hidden=false;updateAttitudeAtTime(0);return;}
  const preferred=available.find(x=>x.key==='altitude')||available[0];select.value=preferred.key;setGraphMetric(preferred.key);
}

function closeGraphViewer(){
  const overlay=document.getElementById('graphViewerOverlay');if(overlay){overlay.hidden=true;overlay.setAttribute('aria-hidden','true');}
  document.body.style.overflow='';
}

function resetGraphView(metric){
  const s=graphSeries(metric);if(!s.times.length){graphViewerState.viewStartMs=null;graphViewerState.viewEndMs=null;return;}
  graphViewerState.viewStartMs=s.times[0];graphViewerState.viewEndMs=s.times[s.times.length-1];
  if(graphViewerState.viewEndMs<=graphViewerState.viewStartMs)graphViewerState.viewEndMs=graphViewerState.viewStartMs+1000;
}

function setGraphMetric(metricKey){
  const metric=graphMetricByKey(metricKey);graphViewerState.metricKey=metricKey;
  if(!metric||!metric.available){document.getElementById('graphNoData').hidden=false;return;}
  document.getElementById('graphNoData').hidden=true;
  const s=graphSeries(metric);const minT=s.times[0],maxT=s.times[s.times.length-1];
  if(!Number.isFinite(graphViewerState.viewStartMs)||!Number.isFinite(graphViewerState.viewEndMs)||graphViewerState.viewEndMs<minT||graphViewerState.viewStartMs>maxT)resetGraphView(metric);
  if(!Number.isFinite(graphViewerState.selectedTimeMs))graphViewerState.selectedTimeMs=minT;
  renderGraphSeries(metric);updateAttitudeAtTime(graphViewerState.selectedTimeMs);
}

function canvasPlotGeometry(canvas){return {left:58,right:24,top:24,bottom:48,width:canvas.clientWidth||800,height:canvas.clientHeight||520};}

function renderGraphSeries(metric){
  const canvas=document.getElementById('graphCanvas');if(!canvas||!metric)return;
  const s=graphSeries(metric),noData=document.getElementById('graphNoData');
  if(!s.times.length){noData.hidden=false;return;}noData.hidden=true;
  const dpr=Math.max(1,window.devicePixelRatio||1),w=Math.max(320,canvas.clientWidth||800),h=Math.max(280,canvas.clientHeight||520);
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  const g=canvasPlotGeometry(canvas),x0=g.left,x1=w-g.right,y0=g.top,y1=h-g.bottom;
  const viewStart=Number.isFinite(graphViewerState.viewStartMs)?graphViewerState.viewStartMs:s.times[0],viewEnd=Number.isFinite(graphViewerState.viewEndMs)?graphViewerState.viewEndMs:s.times[s.times.length-1];
  const pts=[];for(let i=0;i<s.times.length;i++){if(s.times[i]>=viewStart&&s.times[i]<=viewEnd)pts.push([s.times[i],s.values[i]]);}if(!pts.length)return;
  let ymin=Math.min(...pts.map(p=>p[1])),ymax=Math.max(...pts.map(p=>p[1]));if(ymax===ymin){ymax+=1;ymin-=1;}const pad=(ymax-ymin)*.08;ymin-=pad;ymax+=pad;
  const X=t=>x0+(t-viewStart)/(viewEnd-viewStart||1)*(x1-x0),Y=v=>y1-(v-ymin)/(ymax-ymin||1)*(y1-y0);
  ctx.strokeStyle='#243244';ctx.lineWidth=1;ctx.fillStyle='#94a3b8';ctx.font='11px monospace';
  for(let i=0;i<=5;i++){const yy=y0+(y1-y0)*i/5;ctx.beginPath();ctx.moveTo(x0,yy);ctx.lineTo(x1,yy);ctx.stroke();const val=ymax-(ymax-ymin)*i/5;ctx.fillText(val.toFixed(Math.abs(val)<10?2:1),6,yy+4);}
  for(let i=0;i<=6;i++){const xx=x0+(x1-x0)*i/6;ctx.beginPath();ctx.moveTo(xx,y0);ctx.lineTo(xx,y1);ctx.stroke();const t=viewStart+(viewEnd-viewStart)*i/6;ctx.fillText(formatGraphTime(t),Math.max(2,xx-28),h-18);}
  ctx.strokeStyle='#38bdf8';ctx.lineWidth=2;ctx.beginPath();pts.forEach((p,i)=>{const xx=X(p[0]),yy=Y(p[1]);if(i===0)ctx.moveTo(xx,yy);else ctx.lineTo(xx,yy);});ctx.stroke();
  ctx.fillStyle='#e2e8f0';ctx.font='bold 12px sans-serif';ctx.fillText(`${metric.label} (${metric.unit})`,x0,y0-8);
  const sel=graphViewerState.selectedTimeMs;if(Number.isFinite(sel)&&sel>=viewStart&&sel<=viewEnd){const sx=X(sel);ctx.strokeStyle='#facc15';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(sx,y0);ctx.lineTo(sx,y1);ctx.stroke();}
}

function selectGraphTime(timeMs){
  if(!Number.isFinite(timeMs))return;graphViewerState.selectedTimeMs=timeMs;updateAttitudeAtTime(timeMs);const m=graphMetricByKey(graphViewerState.metricKey);if(m)renderGraphSeries(m);
}

function updateAttitudeAtTime(timeMs){
  const d=graphViewerState.result?.graph_data||{},times=d.attitude_time_ms||[],idx=nearestSampleIndex(times,timeMs);const values=document.getElementById('attitudeValues'),scene=document.getElementById('attitudeScene');
  if(idx<0){if(values)values.innerHTML='<div class="attitude-value" style="grid-column:1/-1">Немає ATTITUDE у цьому TLOG</div>';if(scene)scene.style.transform='translate(-50%,-50%)';return;}
  const roll=Number(d.roll_deg?.[idx]),pitch=Number(d.pitch_deg?.[idx]),yaw=Number(d.yaw_deg?.[idx]);
  if(scene&&Number.isFinite(roll)&&Number.isFinite(pitch)){const py=Math.max(-90,Math.min(90,pitch))*2.2;scene.style.transform=`translate(-50%,calc(-50% + ${py}px)) rotate(${-roll}deg)`;}
  const altMetric=graphViewerState.registry.find(x=>x.key==='altitude'&&x.available);let alt=null;if(altMetric){const s=graphSeries(altMetric),ai=nearestSampleIndex(s.times,timeMs);if(ai>=0)alt=s.values[ai];}
  if(values)values.innerHTML=`<div class="attitude-value"><b>ROLL</b>${Number.isFinite(roll)?roll.toFixed(1)+'°':'—'}</div><div class="attitude-value"><b>PITCH</b>${Number.isFinite(pitch)?pitch.toFixed(1)+'°':'—'}</div><div class="attitude-value"><b>YAW</b>${Number.isFinite(yaw)?yaw.toFixed(1)+'°':'—'}</div><div class="attitude-value"><b>ALT</b>${Number.isFinite(alt)?alt.toFixed(1)+' м':'—'}</div><div class="attitude-value" style="grid-column:1/-1"><b>ЧАС</b>${formatGraphTime(timeMs)}</div>`;
}

function graphTimeFromClientX(clientX){
  const canvas=document.getElementById('graphCanvas'),metric=graphMetricByKey(graphViewerState.metricKey);if(!canvas||!metric)return null;const rect=canvas.getBoundingClientRect(),g=canvasPlotGeometry(canvas),x=clientX-rect.left;if(x<g.left||x>rect.width-g.right)return null;return graphViewerState.viewStartMs+(x-g.left)/(rect.width-g.left-g.right)*(graphViewerState.viewEndMs-graphViewerState.viewStartMs);
}

function ensureGraphCanvasEvents(){
  const canvas=document.getElementById('graphCanvas');if(!canvas||canvas.dataset.graphBound)return;canvas.dataset.graphBound='1';
  const tip=document.getElementById('graphTooltip');
  canvas.addEventListener('mousemove',e=>{if(graphViewerState.dragging){const rect=canvas.getBoundingClientRect(),span=graphViewerState.viewEndMs-graphViewerState.viewStartMs,dt=-(e.clientX-graphViewerState.lastX)/Math.max(1,rect.width-82)*span;graphViewerState.viewStartMs+=dt;graphViewerState.viewEndMs+=dt;graphViewerState.lastX=e.clientX;renderGraphSeries(graphMetricByKey(graphViewerState.metricKey));return;}const t=graphTimeFromClientX(e.clientX),m=graphMetricByKey(graphViewerState.metricKey);if(!Number.isFinite(t)||!m)return;const s=graphSeries(m),i=nearestSampleIndex(s.times,t);if(i<0)return;if(!graphViewerState.pinned)selectGraphTime(s.times[i]);if(tip){tip.style.display='block';tip.style.left=(e.offsetX+14)+'px';tip.style.top=(e.offsetY+14)+'px';tip.textContent=`${formatGraphTime(s.times[i])} • ${s.values[i].toFixed(2)} ${m.unit}`;}});
  canvas.addEventListener('mouseleave',()=>{if(tip)tip.style.display='none';graphViewerState.dragging=false;});
  canvas.addEventListener('mousedown',e=>{if(e.button===0){graphViewerState.dragging=true;graphViewerState.lastX=e.clientX;}});
  window.addEventListener('mouseup',()=>{graphViewerState.dragging=false;});
  canvas.addEventListener('click',e=>{const t=graphTimeFromClientX(e.clientX),m=graphMetricByKey(graphViewerState.metricKey);if(!Number.isFinite(t)||!m)return;const s=graphSeries(m),i=nearestSampleIndex(s.times,t);if(i>=0){graphViewerState.pinned=true;selectGraphTime(s.times[i]);}});
  canvas.addEventListener('dblclick',()=>{graphViewerState.pinned=false;const m=graphMetricByKey(graphViewerState.metricKey);resetGraphView(m);renderGraphSeries(m);});
  canvas.addEventListener('wheel',e=>{e.preventDefault();const center=graphTimeFromClientX(e.clientX);if(!Number.isFinite(center))return;const span=Math.max(1000,graphViewerState.viewEndMs-graphViewerState.viewStartMs),factor=e.deltaY>0?1.25:.8,newSpan=Math.max(1000,span*factor),ratio=(center-graphViewerState.viewStartMs)/span;graphViewerState.viewStartMs=center-newSpan*ratio;graphViewerState.viewEndMs=graphViewerState.viewStartMs+newSpan;renderGraphSeries(graphMetricByKey(graphViewerState.metricKey));},{passive:false});
}

window.addEventListener('resize',()=>{const o=document.getElementById('graphViewerOverlay');if(o&&!o.hidden){const m=graphMetricByKey(graphViewerState.metricKey);if(m)renderGraphSeries(m);}});
'''
    html = replace_once(html, "function renderResults(data){", js + "\nfunction renderResults(data){", "viewer JS")

if "window.__lastAnalysisResult=data;" not in html:
    html = replace_once(
        html,
        "function renderResults(data){\n  UI.progress.style.display='none';\n  UI.results.style.display='block';\n  UI.resetBtn.style.display='inline-block';",
        "function renderResults(data){\n  UI.progress.style.display='none';\n  UI.results.style.display='block';\n  UI.resetBtn.style.display='inline-block';\n  window.__lastAnalysisResult=data;\n  const graphBtn=document.getElementById('graphViewerBtn');\n  if(graphBtn){\n    const hasGraph=buildGraphMetricRegistry(data?.graph_data||{}).some(x=>x.available);\n    graphBtn.hidden=!hasGraph;\n    graphBtn.onclick=()=>openGraphViewer(data);\n  }",
        "renderResults graph button",
    )

if "closeGraphViewer();\n  const graphBtn=document.getElementById('graphViewerBtn');" not in html:
    html = replace_once(
        html,
        "function resetForm(){\n  selectedFile=null;",
        "function resetForm(){\n  closeGraphViewer();\n  const graphBtn=document.getElementById('graphViewerBtn');\n  if(graphBtn)graphBtn.hidden=true;\n  window.__lastAnalysisResult=null;\n  selectedFile=null;",
        "reset graph viewer",
    )

index_path.write_text(html, encoding="utf-8")
print("graph + attitude viewer patch applied")
