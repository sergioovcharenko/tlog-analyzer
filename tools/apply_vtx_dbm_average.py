from pathlib import Path

index_path=Path('index.html')
backend_path=Path('backend/main.py')
html=index_path.read_text(encoding='utf-8')
backend=backend_path.read_text(encoding='utf-8')

# Red highlight for the worst average.
if '.vtx-frequency-worst{' not in html:
    anchor='.vtx-frequency-best .vtx-frequency-main{color:var(--success)}'
    if anchor not in html:
        raise SystemExit('VTX CSS anchor not found')
    html=html.replace(anchor,anchor+'''\n.vtx-frequency-worst{\n  border-color:var(--danger)!important;\n  background:rgba(239,68,68,.12)!important;\n  box-shadow:inset 0 0 0 1px rgba(239,68,68,.20);\n}\n.vtx-frequency-worst .vtx-frequency-main{color:var(--danger)}''',1)

# Add a unique helper; leave the legacy helper untouched to avoid duplicate const declarations.
marker_start='/* VTX_ALL_DBM_AVERAGE_V1_START */'
marker_end='/* VTX_ALL_DBM_AVERAGE_V1_END */'
if marker_start in html and marker_end in html:
    a=html.index(marker_start); b=html.index(marker_end,a)+len(marker_end)
    html=html[:a]+html[b:]

legacy_fn=html.find('function summarizeVtxFrequencySelections')
if legacy_fn<0:
    raise SystemExit('legacy VTX helper not found')
legacy_stable=html.find('stableFrequency',legacy_fn)
legacy_end=html.find('\n}',legacy_stable)
if legacy_stable<0 or legacy_end<0:
    raise SystemExit('legacy VTX helper end not found')
legacy_end+=2

new_helper=r'''\n/* VTX_ALL_DBM_AVERAGE_V1_START */
function summarizeVtxFrequencySelectionsAllDbm(timeline,frequencyDbmStats){
  const stats=new Map();
  Object.values(VTX_FREQUENCY_MATRIX).flat().forEach(freq=>stats.set(freq,{frequency:freq,switches:0,avgDbm:null,dbmSamples:0}));
  let previous=null,totalSwitches=0;
  for(const row of (Array.isArray(timeline)?timeline:[])){
    const freq=Number(row?.videoFreq);
    if(!Number.isFinite(freq)||freq<=0)continue;
    const f=Math.round(freq);
    if(!stats.has(f))continue;
    if(previous!==null&&f!==previous){stats.get(f).switches+=1;totalSwitches+=1;}
    previous=f;
  }
  for(const row of (Array.isArray(frequencyDbmStats)?frequencyDbmStats:[])){
    const f=Math.round(Number(row?.frequency));
    if(!stats.has(f))continue;
    const item=stats.get(f),avg=Number(row?.avgDbm),samples=Number(row?.samples);
    item.avgDbm=Number.isFinite(avg)?avg:null;
    item.dbmSamples=Number.isFinite(samples)?samples:0;
  }
  const frequencies=[...stats.values()];
  const candidates=frequencies.filter(item=>item.dbmSamples>=3&&Number.isFinite(item.avgDbm)).sort((a,b)=>(b.avgDbm-a.avgDbm)||(b.dbmSamples-a.dbmSamples));
  return {totalSwitches,frequencies,stableFrequency:candidates.length?candidates[0].frequency:null,worstFrequency:candidates.length>1?candidates[candidates.length-1].frequency:null};
}
/* VTX_ALL_DBM_AVERAGE_V1_END */'''
html=html[:legacy_end]+new_helper+html[legacy_end:]

html=html.replace('const vtxFlight=summarizeVtxFrequencySelections(data.timeline);','const vtxFlight=summarizeVtxFrequencySelectionsAllDbm(data.timeline,video.frequencyDbmStats);',1)
html=html.replace('const vtxFlight=summarizeVtxFrequencySelections(data.timeline,video.frequencyDbmStats);','const vtxFlight=summarizeVtxFrequencySelectionsAllDbm(data.timeline,video.frequencyDbmStats);',1)
if 'summarizeVtxFrequencySelectionsAllDbm(data.timeline,video.frequencyDbmStats)' not in html:
    raise SystemExit('VTX call site not found')

render_start=html.find('  const vtxByFrequency=new Map(vtxFlight.frequencies.map(item=>[item.frequency,item]));')
render_end=html.find('\n\n  // V23.9:',render_start)
if render_start<0 or render_end<0:
    raise SystemExit('VTX render anchors not found')
new_render=r'''  const vtxByFrequency=new Map(vtxFlight.frequencies.map(item=>[item.frequency,item]));
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
      <div class="card-desc">AVG = сума всіх RADIO/RADIO_STATUS dBm-відліків на активній частоті / кількість відліків; -128 включено. ≥ -85 dBm — норма. Зелена — найкраще середнє, червона — найгірше.</div>
    </div>
    ${createCard('Змін VTX',video.changeCount??vtxFlight.totalSwitches)}
  `;'''
html=html[:render_start]+new_render+html[render_end:]

# Backend raw per-frequency average.
init_anchor='        dbm_sample_count = 0\n        telem_rssi_raw = None'
init_repl='''        dbm_sample_count = 0
        vtx_dbm_stats = {
            freq: {"sum": 0.0, "samples": 0}
            for band in VTX_CHANNELS.values() for freq in band.values()
        }
        telem_rssi_raw = None'''
if init_anchor in backend:
    backend=backend.replace(init_anchor,init_repl,1)
elif 'vtx_dbm_stats = {' not in backend:
    raise SystemExit('backend init anchor not found')

radio_anchor='''                if dbm_val != 0:
                    dbm_sum += float(dbm_val)
                    dbm_sample_count += 1
'''
radio_repl='''                if dbm_val != 0:
                    dbm_sum += float(dbm_val)
                    dbm_sample_count += 1
                    vtx_state = get_vtx_state(ch7_current, ch8_current)
                    if vtx_state:
                        bucket = vtx_dbm_stats.get(vtx_state.get("frequency"))
                        if bucket is not None:
                            bucket["sum"] += float(dbm_val)
                            bucket["samples"] += 1
'''
if radio_anchor in backend:
    backend=backend.replace(radio_anchor,radio_repl,1)
elif 'vtx_state = get_vtx_state(ch7_current, ch8_current)' not in backend:
    raise SystemExit('backend radio anchor not found')

response_anchor='''                "changeCount": video_change_count,
                "uniqueCount": len(video_freq_seen),'''
response_repl='''                "changeCount": video_change_count,
                "frequencyDbmStats": [
                    {
                        "frequency": freq,
                        "samples": bucket["samples"],
                        "avgDbm": round(bucket["sum"] / bucket["samples"], 1)
                        if bucket["samples"] > 0 else None,
                    }
                    for freq, bucket in sorted(vtx_dbm_stats.items())
                ],
                "uniqueCount": len(video_freq_seen),'''
if response_anchor in backend:
    backend=backend.replace(response_anchor,response_repl,1)
elif '"frequencyDbmStats": [' not in backend:
    raise SystemExit('backend response anchor not found')

index_path.write_text(html,encoding='utf-8')
backend_path.write_text(backend,encoding='utf-8')
print('VTX all-sample dBm average applied')
