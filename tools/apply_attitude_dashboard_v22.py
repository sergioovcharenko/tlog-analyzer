from pathlib import Path
import re

html_path = Path("index.html")
backend_path = Path("backend/main.py")
html = html_path.read_text(encoding="utf-8")
backend = backend_path.read_text(encoding="utf-8")

# 1) Green ground in the attitude indicator.
html = html.replace(
    "#8a5a36 50.6%,#5f3b27 100%",
    "#4c9a3f 50.6%,#2f7d32 100%",
    1,
)

# 1b) The upper roll marker must move around the fixed bank scale.
html = html.replace(
    '<div class="attitude-roll-pointer" aria-hidden="true"></div>',
    '<div id="attitudeRollPointer" class="attitude-roll-pointer" aria-hidden="true"></div>',
    1,
)
html = html.replace(
    '.attitude-roll-pointer{position:absolute;left:50%;top:7px;z-index:7;width:0;height:0;transform:translateX(-50%);border-left:7px solid transparent;border-right:7px solid transparent;border-top:0;border-bottom:13px solid #facc15;filter:drop-shadow(0 1px 2px #000);pointer-events:none}',
    '.attitude-roll-pointer{position:absolute;left:50%;top:50%;z-index:7;width:0;height:0;transform:translate(-50%,-50%) rotate(0deg) translateY(-112px);transform-origin:0 0;border-left:7px solid transparent;border-right:7px solid transparent;border-top:13px solid #facc15;border-bottom:0;filter:drop-shadow(0 1px 2px #000);pointer-events:none;will-change:transform}',
    1,
)

# 2) Add compact RSSI/dBm cards above the horizon.
if 'id="attitudeRssi"' not in html:
    anchor = '        <div id="attitudeHorizon" aria-label="Авіагоризонт з шкалою крену і тангажу">'
    insert = '''        <div class="attitude-radio-row">
          <div class="attitude-radio-card"><b>RSSI</b><span id="attitudeRssi">—</span></div>
          <div class="attitude-radio-card"><b>dBm</b><span id="attitudeDbm">—</span></div>
        </div>
'''
    if anchor not in html:
        raise SystemExit("attitude horizon markup anchor not found")
    html = html.replace(anchor, insert + anchor, 1)

# 2b) Show the current flight mode in the empty top-right area of the attitude panel.
if 'id="attitudeFlightMode"' not in html:
    title_anchor = '        <div class="attitude-title">✈ АВІАГОРИЗОНТ</div>'
    title_markup = '''        <div class="attitude-head-row">
          <div class="attitude-title">✈ АВІАГОРИЗОНТ</div>
          <div class="attitude-mode-card"><b>ПОЛІТНИЙ РЕЖИМ</b><span id="attitudeFlightMode">—</span></div>
        </div>'''
    if title_anchor not in html:
        raise SystemExit("attitude title anchor not found")
    html = html.replace(title_anchor, title_markup, 1)

# 3) Dashboard styles: top radio cards + denser 3-column telemetry grid.
if '.attitude-radio-row{' not in html:
    css_anchor = '.attitude-values{display:grid;grid-template-columns:1fr 1fr;gap:7px;font:12px monospace}'
    css = '''.attitude-radio-row{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:0 0 9px}
.attitude-radio-card{display:flex;align-items:center;justify-content:space-between;gap:8px;border:1px solid #28435d;border-radius:7px;padding:8px 10px;background:#08111b;font:800 12px monospace;box-shadow:inset 0 0 0 1px rgba(56,189,248,.04)}
.attitude-radio-card b{font-size:10px;color:#7dd3fc;letter-spacing:.07em}.attitude-radio-card span{font-size:15px;color:#f8fafc}
.attitude-values{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;font:12px monospace}
.attitude-value{min-width:0}.attitude-value b{white-space:normal}.attitude-value .att-main{display:block;font-size:15px;font-weight:900;color:#f8fafc}
.attitude-value.att-fc .att-main{color:#38bdf8}.attitude-value.att-current .att-main{color:#fb7185}.attitude-value.att-engine .att-main{color:#facc15}
'''
    if css_anchor not in html:
        raise SystemExit("attitude values CSS anchor not found")
    html = html.replace(css_anchor, css, 1)

# Flight mode badge styling.
if '.attitude-mode-card{' not in html:
    css_anchor = '.attitude-title{font-size:13px;font-weight:900;margin-bottom:10px;color:#f8fafc}'
    mode_css = '''.attitude-head-row{display:flex;align-items:stretch;justify-content:space-between;gap:10px;margin-bottom:9px}.attitude-head-row .attitude-title{display:flex;align-items:center;margin-bottom:0}
.attitude-mode-card{min-width:170px;border:1px solid #334e68;border-radius:7px;background:#08111b;padding:6px 10px;text-align:right;font-family:monospace;box-shadow:inset 0 0 0 1px rgba(56,189,248,.05)}
.attitude-mode-card b{display:block;color:#7dd3fc;font-size:9px;letter-spacing:.06em;line-height:1.15}.attitude-mode-card span{display:block;color:#f8fafc;font-size:16px;font-weight:900;line-height:1.2;margin-top:2px}'''
    if css_anchor not in html:
        raise SystemExit("attitude title CSS anchor not found")
    html = html.replace(css_anchor, css_anchor + '\n' + mode_css, 1)

# Requested threshold colors for battery/current/FC temperature/Engine Load.
if '.att-bat-green .att-main' not in html:
    css_anchor = '.attitude-value.att-fc .att-main{color:#38bdf8}.attitude-value.att-current .att-main{color:#fb7185}.attitude-value.att-engine .att-main{color:#facc15}'
    threshold_css = '''.attitude-value.att-fc .att-main,.attitude-value.att-current .att-main{color:#f8fafc}
.att-bat-green .att-main{color:#22c55e!important}.att-bat-orange .att-main{color:#f59e0b!important}.att-bat-red .att-main{color:#ef4444!important}
.att-current-red .att-main{color:#ef4444!important}
.att-fc-orange .att-main{color:#f59e0b!important}.att-fc-red .att-main{color:#ef4444!important}
.att-engine-green .att-main{color:#22c55e!important}'''
    if css_anchor not in html:
        raise SystemExit("attitude threshold CSS anchor not found")
    html = html.replace(css_anchor, css_anchor + '\n' + threshold_css, 1)

# The older v2 nth-child emphasis assumes two columns; remove it for v2.2.
html = html.replace(
    '.attitude-value:nth-child(1),.attitude-value:nth-child(2){font-size:16px;font-weight:900;border-color:#334e68}.attitude-value:nth-child(1) b,.attitude-value:nth-child(2) b{font-size:10px;letter-spacing:.08em}',
    '.attitude-value b{font-size:10px;letter-spacing:.06em}',
    1,
)

# Slightly widen the avionics column to fit the 3-column telemetry cards.
html = html.replace(
    'grid-template-columns:minmax(0,1fr) 310px',
    'grid-template-columns:minmax(0,1fr) 390px',
    1,
)

# 4) Helpers for requested dashboard warning thresholds.
helpers = r'''function attitudeBatClass(v){
  if(!Number.isFinite(v))return '';
  if(v>=20&&v<=25.2)return 'att-bat-green';
  if(v>=18&&v<20)return 'att-bat-orange';
  if(v<=17.99)return 'att-bat-red';
  return '';
}
function attitudeCurrentClass(v){
  return Number.isFinite(v)&&v>=80?'att-current-red':'';
}
function attitudeFcTempClass(v){
  if(!Number.isFinite(v))return '';
  if(v>=85)return 'att-fc-red';
  if(v>=80&&v<85)return 'att-fc-orange';
  return '';
}
'''
if 'function attitudeBatClass(v)' not in html:
    anchor = 'function updateAttitudeAtTime(timeMs){'
    if anchor not in html:
        raise SystemExit("attitude updater anchor not found")
    html = html.replace(anchor, helpers + anchor, 1)

# 5) Replace attitude updater so every readout follows the selected graph time.
start = html.find('function updateAttitudeAtTime(timeMs){')
end = html.find('\nfunction graphTimeFromClientX', start)
if start < 0 or end < 0:
    raise SystemExit("updateAttitudeAtTime function anchor not found")

new_fn = r'''function updateAttitudeAtTime(timeMs){
  const d=graphViewerState.result?.graph_data||{},times=d.attitude_time_ms||[],idx=nearestSampleIndex(times,timeMs);
  const values=document.getElementById('attitudeValues'),scene=document.getElementById('attitudeScene');
  const pointer=document.getElementById('attitudeRollPointer');
  const modeEl=document.getElementById('attitudeFlightMode');
  const rssiEl=document.getElementById('attitudeRssi'),dbmEl=document.getElementById('attitudeDbm');
  const sample=(timeKey,valueKey)=>{const tt=d[timeKey]||[],vv=d[valueKey]||[],i=nearestSampleIndex(tt,timeMs);const v=i>=0?Number(vv[i]):NaN;return Number.isFinite(v)?v:null;};
  const modeAtTime=()=>{const tt=d.mode_time_ms||[],vv=d.flight_mode||[];if(!tt.length||!vv.length)return '—';let i=nearestSampleIndex(tt,timeMs);if(i<0)return '—';if(Number(tt[i])>timeMs&&i>0)i-=1;return String(vv[i]||'—');};
  const rssi=sample('rssi_time_ms','rssi_pct'),dbm=sample('radio_time_ms','radio_dbm');
  if(rssiEl)rssiEl.textContent=rssi===null?'—':`${Math.round(rssi)} %`;
  if(dbmEl)dbmEl.textContent=dbm===null?'—':`${Math.round(dbm)} dBm`;
  if(modeEl)modeEl.textContent=modeAtTime();
  if(idx<0){
    if(values)values.innerHTML='<div class="attitude-value" style="grid-column:1/-1">Немає ATTITUDE у цьому TLOG</div>';
    if(scene)scene.style.transform='translate(-50%,-50%)';
    if(pointer)pointer.style.transform='translate(-50%,-50%) rotate(0deg) translateY(-112px)';
    return;
  }
  const roll=Number(d.roll_deg?.[idx]),pitch=Number(d.pitch_deg?.[idx]),yaw=Number(d.yaw_deg?.[idx]);
  if(scene&&Number.isFinite(roll)&&Number.isFinite(pitch)){const py=Math.max(-90,Math.min(90,pitch))*2.2;scene.style.transform=`translate(-50%,calc(-50% + ${py}px)) rotate(${-roll}deg)`;}
  if(pointer&&Number.isFinite(roll))pointer.style.transform=`translate(-50%,-50%) rotate(${roll}deg) translateY(-112px)`;
  const alt=sample('altitude_time_ms','altitude_m');
  const voltage=sample('voltage_time_ms','voltage_v');
  const fcTemp=sample('fc_temp_time_ms','fc_temp_c');
  const current=sample('current_time_ms','current_a');
  const engineLoad=sample('engine_load_time_ms','engine_load_pct');
  if(values)values.innerHTML=`
    <div class="attitude-value"><b>ROLL</b><span class="att-main">${Number.isFinite(roll)?roll.toFixed(1)+'°':'—'}</span></div>
    <div class="attitude-value"><b>PITCH</b><span class="att-main">${Number.isFinite(pitch)?pitch.toFixed(1)+'°':'—'}</span></div>
    <div class="attitude-value"><b>YAW</b><span class="att-main">${Number.isFinite(yaw)?yaw.toFixed(1)+'°':'—'}</span></div>
    <div class="attitude-value"><b>ALT</b><span class="att-main">${alt===null?'—':alt.toFixed(1)+' м'}</span></div>
    <div class="attitude-value"><b>ЧАС</b><span class="att-main">${formatGraphTime(timeMs)}</span></div>
    <div class="attitude-value ${attitudeBatClass(voltage)}"><b>BAT</b><span class="att-main">${voltage===null?'—':voltage.toFixed(1)+' V'}</span></div>
    <div class="attitude-value att-fc ${attitudeFcTempClass(fcTemp)}"><b>ТЕМПЕРАТУРА FC</b><span class="att-main">${fcTemp===null?'—':fcTemp.toFixed(1)+' °C'}</span></div>
    <div class="attitude-value att-current ${attitudeCurrentClass(current)}"><b>CURRENT</b><span class="att-main">${current===null?'—':current.toFixed(1)+' A'}</span></div>
    <div class="attitude-value att-engine att-engine-green"><b>ENGINE LOAD</b><span class="att-main">${engineLoad===null?'—':engineLoad.toFixed(1)+' %'}</span></div>`;
}
'''
html = html[:start] + new_fn + html[end:]

# 6) Backend: export existing snapshot RSSI and FC temperature into graph_data.
needle = '        append_pair("radio_time_ms", "radio_dbm", t_ms, row.get("dbm"))\n'
addition = (
    '        append_pair("rssi_time_ms", "rssi_pct", t_ms, row.get("rssi"))\n'
    '        append_pair("radio_time_ms", "radio_dbm", t_ms, row.get("dbm"))\n'
    '        append_pair("fc_temp_time_ms", "fc_temp_c", t_ms, row.get("temp"))\n'
)
if 'append_pair("rssi_time_ms", "rssi_pct"' not in backend:
    if needle not in backend:
        raise SystemExit("backend radio graph anchor not found")
    backend = backend.replace(needle, addition, 1)

# 6b) Export the flight mode at each timeline snapshot so the badge follows graph time.
if 'out.setdefault("mode_time_ms", []).append(t_ms)' not in backend:
    anchor = '        if t_ms is None:\n            continue\n\n'
    mode_export = '''        mode = str(row.get("mode") or "").strip()
        if mode:
            out.setdefault("mode_time_ms", []).append(t_ms)
            out.setdefault("flight_mode", []).append(str(mode))

'''
    if anchor not in backend:
        raise SystemExit("backend graph time anchor not found")
    backend = backend.replace(anchor, anchor + mode_export, 1)

html_path.write_text(html, encoding="utf-8")
backend_path.write_text(backend, encoding="utf-8")
print("Applied attitude dashboard v2.2: flight mode badge, warning colors, green ground, moving roll pointer, RSSI/dBm, FC temp, Current and Engine Load")
