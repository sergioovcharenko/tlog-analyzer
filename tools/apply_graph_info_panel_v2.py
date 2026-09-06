from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "index.html"
BACKEND_PATH = ROOT / "backend" / "main.py"

INDEX_MARKER = "/* GRAPH_INFO_PANEL_V2 */"
BACKEND_MARKER = "# GRAPH_INFO_PANEL_V2_BACKEND"


def require_replace(text, old, new, count=1, label="replacement"):
    actual = text.count(old)
    if actual < count:
        raise RuntimeError(f"{label}: expected at least {count} anchor(s), found {actual}")
    return text.replace(old, new, count)


def patch_backend():
    text = BACKEND_PATH.read_text(encoding="utf-8")
    if BACKEND_MARKER in text:
        return False

    text = require_replace(
        text,
        "# V23.28 — clearer powertrain wording; competing-cause logic preserved\n",
        BACKEND_MARKER + " — graph rail adds ground speed + travelled distance telemetry.\n"
        "# V23.28 — clearer powertrain wording; competing-cause logic preserved\n",
        label="backend marker",
    )

    text = require_replace(
        text,
        '        append_pair("vertical_speed_time_ms", "vertical_speed_down_ms", t_ms, row.get("verticalSpeedDown"))\n',
        '        append_pair("vertical_speed_time_ms", "vertical_speed_down_ms", t_ms, row.get("verticalSpeedDown"))\n'
        '        append_pair("ground_speed_time_ms", "ground_speed_ms", t_ms, row.get("groundSpeed"))\n'
        '        append_pair("total_distance_time_ms", "total_distance_m", t_ms, row.get("totalDistance"))\n',
        label="graph data speed series",
    )

    text = require_replace(
        text,
        "        curr_vertical_speed_down = None\n",
        "        curr_vertical_speed_down = None\n"
        "        curr_ground_speed = None\n"
        "        total_distance_travelled = 0.0\n"
        "        last_ground_speed_timestamp = None\n",
        label="ground speed state",
    )

    ground_anchor = '''                if valid_number(msg.groundspeed):
                    max_speed = max(
                        max_speed,
                        float(msg.groundspeed),
                    )
'''
    ground_replacement = '''                if valid_number(msg.groundspeed):
                    ground_speed = max(0.0, float(msg.groundspeed))
                    max_speed = max(max_speed, ground_speed)
                    if last_ground_speed_timestamp is not None and is_currently_armed:
                        ground_dt = current_timestamp - last_ground_speed_timestamp
                        if 0.0 < ground_dt <= 5.0:
                            total_distance_travelled += ground_speed * ground_dt
                    curr_ground_speed = ground_speed
                    last_ground_speed_timestamp = current_timestamp
'''
    text = require_replace(text, ground_anchor, ground_replacement, label="VFR_HUD groundspeed integration")

    engine_line = '                    "engineLoad": round(curr_engine_load, 1) if valid_number(curr_engine_load) else None,\n'
    engine_plus = (
        engine_line
        + '                    "groundSpeed": round(curr_ground_speed, 2) if valid_number(curr_ground_speed) else None,\n'
        + '                    "totalDistance": round(total_distance_travelled, 1),\n'
    )
    occurrences = text.count(engine_line)
    if occurrences < 2:
        raise RuntimeError(f"timeline snapshot fields: expected >=2 engineLoad anchors, found {occurrences}")
    text = text.replace(engine_line, engine_plus)

    BACKEND_PATH.write_text(text, encoding="utf-8")
    return True


def patch_index():
    text = INDEX_PATH.read_text(encoding="utf-8")
    if INDEX_MARKER in text:
        return False

    summary_pattern = re.compile(
        r"function renderGraphDashboardSummary\(snapshot\)\{.*?\n\}\nfunction renderGraphDockTx16",
        re.S,
    )
    summary_replacement = r'''/* GRAPH_INFO_PANEL_V2 */
function formatDashboardDistance(value){
  const n=Number(value);
  if(!Number.isFinite(n))return '—';
  if(n>=1000)return (n/1000).toFixed(2)+' км';
  return n.toFixed(1)+' м';
}
function renderGraphDashboardSummary(snapshot){
  const host=document.getElementById('graphDashboardSummary');if(!host)return;
  const items=[
    ['ВИСОТА',snapshot.altitude??'—'],
    ['ЧАС',snapshot.time??'—'],
    ['НАПРУГА',snapshot.voltage??'—'],
    ['ДИСТАНЦІЯ ДО HOME',snapshot.distance??'—'],
    ['ТЕМПЕРАТУРА FC',snapshot.temperature??'—'],
    ['СТРУМ',snapshot.current??'—'],
    ['GROUND SPEED',snapshot.groundSpeed??'—'],
    ['ЗАГАЛЬНА ДИСТАНЦІЯ',snapshot.totalDistance??'—'],
    ['ENGINE LOAD',snapshot.engineLoad??'—']
  ];
  const toneFor=(k,v)=>{
    const n=parseFloat(String(v??'').replace(',','.'));
    if(!Number.isFinite(n))return '';
    if(k==='НАПРУГА')return typeof attitudeBatClass==='function'?attitudeBatClass(n):'';
    if(k==='ТЕМПЕРАТУРА FC')return typeof attitudeFcTempClass==='function'?attitudeFcTempClass(n):'';
    if(k==='СТРУМ')return n>=80?'summary-danger':'';
    if(k==='ENGINE LOAD')return 'summary-success';
    return '';
  };
  host.innerHTML=items.map(([k,v])=>`<div class="graph-summary-item ${toneFor(k,v)}"><span>${k}</span><strong>${v}</strong></div>`).join('');
  applyHorizonOnlyDarkLayout();
}
function renderGraphDockTx16'''
    text, n = summary_pattern.subn(summary_replacement, text, count=1)
    if n != 1:
        raise RuntimeError(f"dashboard summary function: expected 1 replacement, got {n}")

    sync_pattern = re.compile(
        r"function syncGraphDashboardAtTime\(timeMs\)\{.*?\n\}\nfunction ensureGraphDashboardV2",
        re.S,
    )
    sync_replacement = r'''function syncGraphDashboardAtTime(timeMs){
  const row=nearestDashboardTimelineRow(timeMs),
    alt=dashboardSample('altitude_time_ms','altitude_m',timeMs),
    voltage=dashboardSample('voltage_time_ms','voltage_v',timeMs),
    current=dashboardSample('current_time_ms','current_a',timeMs),
    temp=dashboardSample('fc_temp_time_ms','fc_temp_c',timeMs),
    groundSpeed=dashboardSample('ground_speed_time_ms','ground_speed_ms',timeMs),
    totalDistance=dashboardSample('total_distance_time_ms','total_distance_m',timeMs),
    engineLoad=dashboardSample('engine_load_time_ms','engine_load_pct',timeMs);
  renderGraphDashboardSummary({
    altitude:alt===null?'—':alt.toFixed(1)+' м',
    time:formatGraphTime(timeMs),
    voltage:voltage===null?'—':voltage.toFixed(1)+' V',
    distance:row?.dist??'—',
    temperature:temp===null?'—':temp.toFixed(1)+' °C',
    current:current===null?'—':current.toFixed(1)+' A',
    groundSpeed:groundSpeed===null?'—':groundSpeed.toFixed(1)+' м/с',
    totalDistance:formatDashboardDistance(totalDistance),
    engineLoad:engineLoad===null?'—':engineLoad.toFixed(1)+' %'
  });
  renderGraphDockTx16(timeMs);renderGraphDockData(timeMs);renderSelectedSeriesChips();
}
function ensureGraphDashboardV2'''
    text, n = sync_pattern.subn(sync_replacement, text, count=1)
    if n != 1:
        raise RuntimeError(f"dashboard sync function: expected 1 replacement, got {n}")

    board_pattern = re.compile(
        r"function renderBoardMessagesAtTime\(timeMs\)\{.*?\n\}\n\nfunction selectGraphTime",
        re.S,
    )
    board_replacement = r'''function dashboardBoardEvents(){
  const result=graphViewerState.result||{};
  const events=[];
  const raw=Array.isArray(result.board_messages)?result.board_messages:[];
  raw.forEach(m=>{
    const t=Number(m?.time_ms),text=String(m?.text||'').trim();
    if(!Number.isFinite(t)||!text)return;
    events.push({time_ms:t,text,level:['error','warning','info','recovery'].includes(m.level)?m.level:'info',kind:'statustext'});
  });
  const d=result.graph_data||{},tt=Array.isArray(d.mode_time_ms)?d.mode_time_ms:[],vv=Array.isArray(d.flight_mode)?d.flight_mode:[];
  let previous=null;
  for(let i=0;i<Math.min(tt.length,vv.length);i++){
    const mode=String(vv[i]||'').trim(),t=Number(tt[i]);
    if(!mode||!Number.isFinite(t))continue;
    if(previous!==null&&mode!==previous)events.push({time_ms:t,text:`Режим змінено на ${mode}`,level:'info',kind:'mode'});
    previous=mode;
  }
  const seen=new Set();
  return events.sort((a,b)=>a.time_ms-b.time_ms).filter(e=>{
    const key=Math.round(e.time_ms/100)+'|'+e.text;
    if(seen.has(key))return false;seen.add(key);return true;
  });
}
function renderBoardMessagesAtTime(timeMs){
  const root=document.getElementById('boardMessagesList');if(!root)return;
  const rows=dashboardBoardEvents();
  if(!rows.length){root.innerHTML='<div class="board-message-empty">Немає повідомлень борта або перемикань режиму</div>';return;}
  root.innerHTML=rows.map(m=>{const current=Number.isFinite(Number(timeMs))&&Math.abs(Number(m.time_ms)-Number(timeMs))<=BOARD_MESSAGE_WINDOW_MS?' board-message-current':'';const modeClass=m.kind==='mode'?' board-message-mode':'';return `<div class="board-message board-message-${m.level}${modeClass}${current}"><span class="board-message-time">${formatGraphTime(Number(m.time_ms))}</span>${dynamicEscapeHtml(m.text)}</div>`;}).join('');
  const current=root.querySelector('.board-message-current');if(current)current.scrollIntoView({block:'nearest'});
}

function selectGraphTime'''
    text, n = board_pattern.subn(board_replacement, text, count=1)
    if n != 1:
        raise RuntimeError(f"board messages function: expected 1 replacement, got {n}")

    radio_old = """  if(rssiEl)rssiEl.textContent=rssi===null?'—':`${Math.round(rssi)} %`;\n  if(dbmEl)dbmEl.textContent=dbm===null?'—':`${Math.round(dbm)} dBm`;\n  if(modeEl)modeEl.textContent=modeAtTime();\n"""
    radio_new = """  const setRadioTone=(el,tone)=>{\n    const card=el?.closest('.attitude-radio-card');if(!card)return;\n    card.classList.remove('summary-success','summary-warning','summary-danger');\n    if(tone)card.classList.add(tone);\n  };\n  if(rssiEl){rssiEl.textContent=rssi===null?'—':`${Math.round(rssi)} %`;setRadioTone(rssiEl,rssi===null?'':(rssi>=75?'summary-success':(rssi>=40?'summary-warning':'summary-danger')));}\n  if(dbmEl){dbmEl.textContent=dbm===null?'—':`${Math.round(dbm)} dBm`;setRadioTone(dbmEl,dbm===null?'':(dbm>=-70?'summary-success':(dbm>=-85?'summary-warning':'summary-danger')));}\n  if(modeEl)modeEl.textContent=modeAtTime();\n"""
    text = require_replace(text, radio_old, radio_new, label="attitude radio tone")

    text = text.replace(
        "STATUSTEXT від борта • помилки, попередження та службові повідомлення",
        "Режими польоту + STATUSTEXT від борта • помилки, попередження та службові повідомлення",
        1,
    )

    css = r'''
<style>
/* GRAPH_INFO_PANEL_V2_STYLE */
.graph-dashboard-dock .attitude-radio-row{display:grid!important;grid-template-columns:1fr 1fr!important;gap:8px!important;margin:0 0 9px!important}
#attitudePanel .graph-dashboard-summary.in-attitude{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:7px!important}
#attitudePanel .graph-dashboard-summary.in-attitude .graph-summary-item{min-height:58px!important;padding:8px 9px!important}
#attitudePanel .graph-dashboard-summary.in-attitude .graph-summary-item span{font-size:8px!important;line-height:1.2!important;white-space:normal!important}
#attitudePanel .graph-dashboard-summary.in-attitude .graph-summary-item strong{font-size:13px!important;line-height:1.25!important}
.attitude-radio-card.summary-success span{color:#22c55e!important}.attitude-radio-card.summary-warning span{color:#f59e0b!important}.attitude-radio-card.summary-danger span{color:#ef4444!important}
.graph-summary-item.summary-success strong{color:#22c55e!important}.graph-summary-item.summary-warning strong{color:#f59e0b!important}.graph-summary-item.summary-danger strong{color:#ef4444!important}
.board-message-mode{border-left-color:#60a5fa!important;background:rgba(59,130,246,.08)!important}.board-message-mode .board-message-time{color:#93c5fd!important}
#attitudePanel .attitude-board-messages{margin-top:10px!important}
#attitudePanel .attitude-board-messages #boardMessagesList{max-height:250px!important;overflow:auto!important}
@media(max-width:1199px){#attitudePanel .graph-dashboard-summary.in-attitude{grid-template-columns:repeat(3,minmax(0,1fr))!important}}
@media(max-width:767px){#attitudePanel .graph-dashboard-summary.in-attitude{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
</style>
'''
    if "GRAPH_INFO_PANEL_V2_STYLE" not in text:
        text = require_replace(text, "</head>", css + "\n</head>", label="graph info panel css")

    INDEX_PATH.write_text(text, encoding="utf-8")
    return True


if __name__ == "__main__":
    changed_backend = patch_backend()
    changed_index = patch_index()
    print(f"backend changed={changed_backend}; index changed={changed_index}")
