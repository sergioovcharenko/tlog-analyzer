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

# 4) Replace attitude updater so every readout follows the selected graph time.
start = html.find('function updateAttitudeAtTime(timeMs){')
end = html.find('\nfunction graphTimeFromClientX', start)
if start < 0 or end < 0:
    raise SystemExit("updateAttitudeAtTime function anchor not found")

new_fn = r'''function updateAttitudeAtTime(timeMs){
  const d=graphViewerState.result?.graph_data||{},times=d.attitude_time_ms||[],idx=nearestSampleIndex(times,timeMs);
  const values=document.getElementById('attitudeValues'),scene=document.getElementById('attitudeScene');
  const rssiEl=document.getElementById('attitudeRssi'),dbmEl=document.getElementById('attitudeDbm');
  const sample=(timeKey,valueKey)=>{const tt=d[timeKey]||[],vv=d[valueKey]||[],i=nearestSampleIndex(tt,timeMs);const v=i>=0?Number(vv[i]):NaN;return Number.isFinite(v)?v:null;};
  const rssi=sample('rssi_time_ms','rssi_pct'),dbm=sample('radio_time_ms','radio_dbm');
  if(rssiEl)rssiEl.textContent=rssi===null?'—':`${Math.round(rssi)} %`;
  if(dbmEl)dbmEl.textContent=dbm===null?'—':`${Math.round(dbm)} dBm`;
  if(idx<0){
    if(values)values.innerHTML='<div class="attitude-value" style="grid-column:1/-1">Немає ATTITUDE у цьому TLOG</div>';
    if(scene)scene.style.transform='translate(-50%,-50%)';
    return;
  }
  const roll=Number(d.roll_deg?.[idx]),pitch=Number(d.pitch_deg?.[idx]),yaw=Number(d.yaw_deg?.[idx]);
  if(scene&&Number.isFinite(roll)&&Number.isFinite(pitch)){const py=Math.max(-90,Math.min(90,pitch))*2.2;scene.style.transform=`translate(-50%,calc(-50% + ${py}px)) rotate(${-roll}deg)`;}
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
    <div class="attitude-value"><b>BAT</b><span class="att-main">${voltage===null?'—':voltage.toFixed(1)+' V'}</span></div>
    <div class="attitude-value att-fc"><b>ТЕМПЕРАТУРА FC</b><span class="att-main">${fcTemp===null?'—':fcTemp.toFixed(1)+' °C'}</span></div>
    <div class="attitude-value att-current"><b>СПОЖИВАННЯ СТРУМУ</b><span class="att-main">${current===null?'—':current.toFixed(1)+' A'}</span></div>
    <div class="attitude-value att-engine"><b>ENGINE LOAD</b><span class="att-main">${engineLoad===null?'—':engineLoad.toFixed(1)+' %'}</span></div>`;
}
'''
html = html[:start] + new_fn + html[end:]

# 5) Backend: export existing snapshot RSSI and FC temperature into graph_data.
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

html_path.write_text(html, encoding="utf-8")
backend_path.write_text(backend, encoding="utf-8")
print("Applied attitude dashboard v2.2: green ground, RSSI/dBm, FC temp, current and Engine Load")
