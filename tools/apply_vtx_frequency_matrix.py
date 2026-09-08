from pathlib import Path

INDEX = Path("index.html")
BACKEND = Path("backend/main.py")
html = INDEX.read_text(encoding="utf-8")
backend = BACKEND.read_text(encoding="utf-8")

# ---------- frontend CSS ----------
if ".vtx-frequency-worst{" not in html:
    anchor = ".vtx-frequency-best .vtx-frequency-main{color:var(--success)}"
    insert = anchor + "\n.vtx-frequency-worst{\n  border-color:var(--danger)!important;\n  background:rgba(239,68,68,.12)!important;\n  box-shadow:inset 0 0 0 1px rgba(239,68,68,.20);\n}\n.vtx-frequency-worst .vtx-frequency-main{color:var(--danger)}"
    if anchor not in html:
        raise SystemExit("VTX CSS anchor not found")
    html = html.replace(anchor, insert, 1)

# ---------- frontend helper ----------
start = html.find("const VTX_")
end_marker = "\nfunction summarizeEngineLoad"
end = html.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("VTX helper region not found")
new_helper = r'''const VTX_NORMAL_DBM_LIMIT=-85;
const VTX_MIN_STABILITY_SAMPLES=3;
const VTX_FREQUENCY_MATRIX={'5.2':[5180,5240,5300],'5.5':[5520,5580,5640],'5.8':[5700,5765,5825]};

function summarizeVtxFrequencySelections(timeline,frequencyDbmStats){
  const stats=new Map();
  Object.values(VTX_FREQUENCY_MATRIX).flat().forEach(freq=>{
    stats.set(freq,{frequency:freq,switches:0,avgDbm:null,dbmSamples:0});
  });
  let previous=null;
  let totalSwitches=0;
  for(const row of (Array.isArray(timeline)?timeline:[])){
    const freq=Number(row?.videoFreq);
    if(!Number.isFinite(freq)||freq<=0)continue;
    const f=Math.round(freq);
    if(!stats.has(f))continue;
    if(previous!==null&&f!==previous){
      stats.get(f).switches+=1;
      totalSwitches+=1;
    }
    previous=f;
  }
  for(const row of (Array.isArray(frequencyDbmStats)?frequencyDbmStats:[])){
    const f=Math.round(Number(row?.frequency));
    if(!stats.has(f))continue;
    const item=stats.get(f);
    const avg=Number(row?.avgDbm), samples=Number(row?.samples);
    item.avgDbm=Number.isFinite(avg)?avg:null;
    item.dbmSamples=Number.isFinite(samples)?samples:0;
  }
  const frequencies=[...stats.values()];
  const candidates=frequencies
    .filter(item=>item.dbmSamples>=VTX_MIN_STABILITY_SAMPLES&&Number.isFinite(item.avgDbm))
    .sort((a,b)=>(b.avgDbm-a.avgDbm)||(b.dbmSamples-a.dbmSamples));
  return {
    totalSwitches,
    frequencies,
    stableFrequency:candidates.length?candidates[0].frequency:null,
    worstFrequency:candidates.length>1?candidates[candidates.length-1].frequency:null
  };
}
'''
html = html[:start] + new_helper + html[end:]

# ---------- frontend render ----------
old_call = "const vtxFlight=summarizeVtxFrequencySelections(data.timeline);"
new_call = "const vtxFlight=summarizeVtxFrequencySelections(data.timeline,video.frequencyDbmStats);"
if old_call in html:
    html = html.replace(old_call, new_call, 1)
elif new_call not in html:
    raise SystemExit("VTX summarize call not found")

render_start = html.find("  const vtxByFrequency=new Map(vtxFlight.frequencies.map(item=>[item.frequency,item]));")
render_end = html.find("\n\n  // V23.9:", render_start)
if render_start < 0 or render_end < 0:
    raise SystemExit("VTX render region not found")
new_render = r'''  const vtxByFrequency=new Map(vtxFlight.frequencies.map(item=>[item.frequency,item]));
  const vtxMatrixHtml=Object.entries(VTX_FREQUENCY_MATRIX).map(([band,freqs])=>{
    const cells=freqs.map(freq=>{
      const item=vtxByFrequency.get(freq)||{switches:0,avgDbm:null,dbmSamples:0};
      const best=freq===vtxFlight.stableFrequency;
      const worst=freq===vtxFlight.worstFrequency;
      const className=`vtx-frequency-cell${best?' vtx-frequency-best':''}${worst?' vtx-frequency-worst':''}`;
      const dbmText=item.avgDbm===null?'dBm —':`AVG ${item.avgDbm.toFixed(1)} dBm`;
      const title=best?'Найкраще середнє dBm':(worst?'Найгірше середнє dBm':'');
      return `<div class="${className}"${title?` title="${title}"`:''}><div class="vtx-frequency-main">${freq} — ${item.switches}</div><div class="vtx-frequency-dbm">${dbmText}</div></div>`;
    }).join('');
    return `<div class="vtx-frequency-band">${band}</div>${cells}`;
  }).join('');
  document.getElementById('videoGrid').innerHTML=`
    <div class="vtx-matrix-card">
      <div class="card-title">ВИКОРИСТАНІ VTX ЧАСТОТИ</div>
      <div class="vtx-frequency-grid">${vtxMatrixHtml}</div>
      <div class="card-desc">AVG = арифметичне середнє всіх RADIO/RADIO_STATUS dBm-відліків на активній частоті; -128 включено. ≥ ${VTX_NORMAL_DBM_LIMIT} dBm — норма. Зелена — найкраще середнє, червона — найгірше.</div>
    </div>
    ${createCard('Змін VTX',video.changeCount??vtxFlight.totalSwitches)}
  `;'''
html = html[:render_start] + new_render + html[render_end:]

# ---------- backend raw RADIO/RADIO_STATUS accumulation ----------
init_anchor = "        dbm_sample_count = 0\n        telem_rssi_raw = None"
init_repl = "        dbm_sample_count = 0\n        vtx_dbm_stats = {\n            freq: {\"sum\": 0.0, \"samples\": 0}\n            for band in VTX_CHANNELS.values() for freq in band.values()\n        }\n        telem_rssi_raw = None"
if init_anchor in backend:
    backend = backend.replace(init_anchor, init_repl, 1)
elif "vtx_dbm_stats = {" not in backend:
    raise SystemExit("Backend VTX dBm init anchor not found")

radio_anchor = '''                if dbm_val != 0:\n                    dbm_sum += float(dbm_val)\n                    dbm_sample_count += 1\n'''
radio_repl = '''                if dbm_val != 0:\n                    dbm_sum += float(dbm_val)\n                    dbm_sample_count += 1\n                    vtx_state = get_vtx_state(ch7_current, ch8_current)\n                    if vtx_state:\n                        bucket = vtx_dbm_stats.get(vtx_state.get("frequency"))\n                        if bucket is not None:\n                            bucket["sum"] += float(dbm_val)\n                            bucket["samples"] += 1\n'''
if radio_anchor in backend:
    backend = backend.replace(radio_anchor, radio_repl, 1)
elif "vtx_state = get_vtx_state(ch7_current, ch8_current)" not in backend:
    raise SystemExit("Backend RADIO accumulation anchor not found")

response_anchor = '''                "changeCount": video_change_count,\n                "uniqueCount": len(video_freq_seen),'''
response_repl = '''                "changeCount": video_change_count,\n                "frequencyDbmStats": [\n                    {\n                        "frequency": freq,\n                        "samples": bucket["samples"],\n                        "avgDbm": round(bucket["sum"] / bucket["samples"], 1)\n                        if bucket["samples"] > 0 else None,\n                    }\n                    for freq, bucket in sorted(vtx_dbm_stats.items())\n                ],\n                "uniqueCount": len(video_freq_seen),'''
if response_anchor in backend:
    backend = backend.replace(response_anchor, response_repl, 1)
elif '"frequencyDbmStats": [' not in backend:
    raise SystemExit("Backend video response anchor not found")

INDEX.write_text(html, encoding="utf-8")
BACKEND.write_text(backend, encoding="utf-8")
print("VTX frequency dBm stats applied")
