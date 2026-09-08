from pathlib import Path

INDEX=Path('index.html')
BACKEND=Path('backend/main.py')
html=INDEX.read_text(encoding='utf-8')
backend=BACKEND.read_text(encoding='utf-8')

if '.vtx-frequency-worst{' not in html:
    anchor='.vtx-frequency-best .vtx-frequency-main{color:var(--success)}'
    if anchor not in html: raise SystemExit('CSS anchor not found')
    html=html.replace(anchor,anchor+'''\n.vtx-frequency-worst{border-color:var(--danger)!important;background:rgba(239,68,68,.12)!important;box-shadow:inset 0 0 0 1px rgba(239,68,68,.20)}\n.vtx-frequency-worst .vtx-frequency-main{color:var(--danger)}''',1)

old_helper=r'''const VTX_STABLE_DBM_LIMIT=-85;
const VTX_MIN_STABILITY_SAMPLES=3;
const VTX_FREQUENCY_MATRIX={'5.2':[5180,5240,5300],'5.5':[5520,5580,5640],'5.8':[5700,5765,5825]};

function summarizeVtxFrequencySelections(timeline){
  const stats=new Map();
  Object.values(VTX_FREQUENCY_MATRIX).flat().forEach(freq=>{
    stats.set(freq,{frequency:freq,switches:0,dbmSum:0,dbmSamples:0,avgDbm:null});
  });
  let previous=null;
  let totalSwitches=0;
  for(const row of (Array.isArray(timeline)?timeline:[])){
    const freq=Number(row?.videoFreq);
    if(!Number.isFinite(freq)||freq<=0)continue;
    const f=Math.round(freq);
    if(!stats.has(f))continue;
    const item=stats.get(f);
    if(previous!==null&&f!==previous){
      item.switches+=1;
      totalSwitches+=1;
    }
    previous=f;
    const dbm=Number(row?.dbm);
    if(Number.isFinite(dbm)){
      item.dbmSum+=dbm;
      item.dbmSamples+=1;
    }
  }
  const frequencies=[...stats.values()].map(item=>({
    ...item,
    avgDbm:item.dbmSamples?item.dbmSum/item.dbmSamples:null
  }));
  const stableCandidates=frequencies
    .filter(item=>item.dbmSamples>=VTX_MIN_STABILITY_SAMPLES&&item.avgDbm!==null&&item.avgDbm>=VTX_STABLE_DBM_LIMIT)
    .sort((a,b)=>(b.avgDbm-a.avgDbm)||(b.dbmSamples-a.dbmSamples));
  return {
    totalSwitches,
    frequencies,
    stableFrequency:stableCandidates.length?stableCandidates[0].frequency:null
  };
}'''
new_helper=r'''const VTX_NORMAL_DBM_LIMIT=-85;
const VTX_MIN_STABILITY_SAMPLES=3;
const VTX_FREQUENCY_MATRIX={'5.2':[5180,5240,5300],'5.5':[5520,5580,5640],'5.8':[5700,5765,5825]};

function summarizeVtxFrequencySelections(timeline,frequencyDbmStats){
  const stats=new Map();
  Object.values(VTX_FREQUENCY_MATRIX).flat().forEach(freq=>stats.set(freq,{frequency:freq,switches:0,avgDbm:null,dbmSamples:0}));
  let previous=null,totalSwitches=0;
  for(const row of (Array.isArray(timeline)?timeline:[])){
    const freq=Number(row?.videoFreq); if(!Number.isFinite(freq)||freq<=0)continue;
    const f=Math.round(freq); if(!stats.has(f))continue;
    if(previous!==null&&f!==previous){stats.get(f).switches+=1;totalSwitches+=1;} previous=f;
  }
  for(const row of (Array.isArray(frequencyDbmStats)?frequencyDbmStats:[])){
    const f=Math.round(Number(row?.frequency)); if(!stats.has(f))continue;
    const item=stats.get(f),hasAvg=!(row?.avgDbm===null||row?.avgDbm===undefined),avg=hasAvg?Number(row.avgDbm):NaN,samples=Number(row?.samples);
    item.avgDbm=hasAvg&&Number.isFinite(avg)?avg:null; item.dbmSamples=Number.isFinite(samples)?samples:0;
  }
  const frequencies=[...stats.values()];
  const candidates=frequencies.filter(item=>item.dbmSamples>=VTX_MIN_STABILITY_SAMPLES&&item.dbmSamples>0&&item.avgDbm!==null&&Number.isFinite(item.avgDbm)).sort((a,b)=>(b.avgDbm-a.avgDbm)||(b.dbmSamples-a.dbmSamples));
  return {totalSwitches,frequencies,stableFrequency:candidates.length?candidates[0].frequency:null,worstFrequency:candidates.length>1?candidates[candidates.length-1].frequency:null};
}'''

current_old=r'''const VTX_NORMAL_DBM_LIMIT=-85;
const VTX_MIN_STABILITY_SAMPLES=3;
const VTX_FREQUENCY_MATRIX={'5.2':[5180,5240,5300],'5.5':[5520,5580,5640],'5.8':[5700,5765,5825]};

function summarizeVtxFrequencySelections(timeline,frequencyDbmStats){
  const stats=new Map();
  Object.values(VTX_FREQUENCY_MATRIX).flat().forEach(freq=>stats.set(freq,{frequency:freq,switches:0,avgDbm:null,dbmSamples:0}));
  let previous=null,totalSwitches=0;
  for(const row of (Array.isArray(timeline)?timeline:[])){
    const freq=Number(row?.videoFreq); if(!Number.isFinite(freq)||freq<=0)continue;
    const f=Math.round(freq); if(!stats.has(f))continue;
    if(previous!==null&&f!==previous){stats.get(f).switches+=1;totalSwitches+=1;} previous=f;
  }
  for(const row of (Array.isArray(frequencyDbmStats)?frequencyDbmStats:[])){
    const f=Math.round(Number(row?.frequency)); if(!stats.has(f))continue;
    const item=stats.get(f),avg=Number(row?.avgDbm),samples=Number(row?.samples);
    item.avgDbm=Number.isFinite(avg)?avg:null; item.dbmSamples=Number.isFinite(samples)?samples:0;
  }
  const frequencies=[...stats.values()];
  const candidates=frequencies.filter(item=>item.dbmSamples>=VTX_MIN_STABILITY_SAMPLES&&Number.isFinite(item.avgDbm)).sort((a,b)=>(b.avgDbm-a.avgDbm)||(b.dbmSamples-a.dbmSamples));
  return {totalSwitches,frequencies,stableFrequency:candidates.length?candidates[0].frequency:null,worstFrequency:candidates.length>1?candidates[candidates.length-1].frequency:null};
}'''

if current_old in html: html=html.replace(current_old,new_helper,1)
elif old_helper in html: html=html.replace(old_helper,new_helper,1)
elif new_helper not in html: raise SystemExit('helper anchor not found')

old_video=r'''  const video=data.video||{};
  const vtxFlight=summarizeVtxFrequencySelections(data.timeline);
  const vtxByFrequency=new Map(vtxFlight.frequencies.map(item=>[item.frequency,item]));
  const vtxMatrixHtml=Object.entries(VTX_FREQUENCY_MATRIX).map(([band,freqs])=>{
    const cells=freqs.map(freq=>{
      const item=vtxByFrequency.get(freq)||{switches:0,avgDbm:null,dbmSamples:0};
      const best=freq===vtxFlight.stableFrequency;
      const dbmText=item.avgDbm===null?'dBm —':`AVG ${item.avgDbm.toFixed(1)} dBm`;
      return `<div class="vtx-frequency-cell${best?' vtx-frequency-best':''}"${best?' title="Найстабільніша VTX частота за середнім dBm"':''}><div class="vtx-frequency-main">${freq} — ${item.switches}</div><div class="vtx-frequency-dbm">${dbmText}</div></div>`;
    }).join('');
    return `<div class="vtx-frequency-band">${band}</div>${cells}`;
  }).join('');
  document.getElementById('videoGrid').innerHTML=`
    <div class="vtx-matrix-card">
      <div class="card-title">ВИКОРИСТАНІ VTX ЧАСТОТИ</div>
      <div class="vtx-frequency-grid">${vtxMatrixHtml}</div>
      <div class="card-desc">Зелена — найстабільніша частота: найкращий середній dBm при AVG ≥ ${VTX_STABLE_DBM_LIMIT} dBm; у середнє входить -128.</div>
    </div>
    ${createCard('Змін VTX',video.changeCount??vtxFlight.totalSwitches)}
  `;'''
new_video=r'''  const video=data.video||{};
  const vtxFlight=summarizeVtxFrequencySelections(data.timeline,video.frequencyDbmStats);
  const vtxByFrequency=new Map(vtxFlight.frequencies.map(item=>[item.frequency,item]));
  const vtxMatrixHtml=Object.entries(VTX_FREQUENCY_MATRIX).map(([band,freqs])=>{
    const cells=freqs.map(freq=>{
      const item=vtxByFrequency.get(freq)||{switches:0,avgDbm:null,dbmSamples:0};
      const best=freq===vtxFlight.stableFrequency,worst=freq===vtxFlight.worstFrequency;
      const dbmText=item.dbmSamples>0&&item.avgDbm!==null?`AVG ${item.avgDbm.toFixed(1)} dBm`:'dBm —';
      return `<div class="vtx-frequency-cell${best?' vtx-frequency-best':''}${worst?' vtx-frequency-worst':''}"><div class="vtx-frequency-main">${freq} — ${item.switches}</div><div class="vtx-frequency-dbm">${dbmText}</div></div>`;
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
current_video=r'''  const video=data.video||{};
  const vtxFlight=summarizeVtxFrequencySelections(data.timeline,video.frequencyDbmStats);
  const vtxByFrequency=new Map(vtxFlight.frequencies.map(item=>[item.frequency,item]));
  const vtxMatrixHtml=Object.entries(VTX_FREQUENCY_MATRIX).map(([band,freqs])=>{
    const cells=freqs.map(freq=>{
      const item=vtxByFrequency.get(freq)||{switches:0,avgDbm:null,dbmSamples:0};
      const best=freq===vtxFlight.stableFrequency,worst=freq===vtxFlight.worstFrequency;
      const dbmText=item.avgDbm===null?'dBm —':`AVG ${item.avgDbm.toFixed(1)} dBm`;
      return `<div class="vtx-frequency-cell${best?' vtx-frequency-best':''}${worst?' vtx-frequency-worst':''}"><div class="vtx-frequency-main">${freq} — ${item.switches}</div><div class="vtx-frequency-dbm">${dbmText}</div></div>`;
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
if current_video in html: html=html.replace(current_video,new_video,1)
elif old_video in html: html=html.replace(old_video,new_video,1)
elif new_video not in html: raise SystemExit('video anchor not found')

init='        dbm_sample_count = 0\n        telem_rssi_raw = None'
repl='''        dbm_sample_count = 0
        vtx_dbm_stats = {freq: {"sum": 0.0, "samples": 0} for band in VTX_CHANNELS.values() for freq in band.values()}
        telem_rssi_raw = None'''
if init in backend: backend=backend.replace(init,repl,1)
elif 'vtx_dbm_stats = {' not in backend: raise SystemExit('backend init anchor not found')

radio='''                if dbm_val != 0:
                    dbm_sum += float(dbm_val)
                    dbm_sample_count += 1
'''
radio2='''                if dbm_val != 0:
                    dbm_sum += float(dbm_val)
                    dbm_sample_count += 1
                    vtx_state = get_vtx_state(ch7_current, ch8_current)
                    if vtx_state:
                        bucket = vtx_dbm_stats.get(vtx_state.get("frequency"))
                        if bucket is not None:
                            bucket["sum"] += float(dbm_val)
                            bucket["samples"] += 1
'''
if radio in backend: backend=backend.replace(radio,radio2,1)
elif 'vtx_state = get_vtx_state(ch7_current, ch8_current)' not in backend: raise SystemExit('radio anchor not found')

resp='''                "changeCount": video_change_count,
                "uniqueCount": len(video_freq_seen),'''
resp2='''                "changeCount": video_change_count,
                "frequencyDbmStats": [{"frequency": freq, "samples": bucket["samples"], "avgDbm": round(bucket["sum"] / bucket["samples"], 1) if bucket["samples"] > 0 else None} for freq, bucket in sorted(vtx_dbm_stats.items())],
                "uniqueCount": len(video_freq_seen),'''
if resp in backend: backend=backend.replace(resp,resp2,1)
elif '"frequencyDbmStats": [' not in backend: raise SystemExit('response anchor not found')

INDEX.write_text(html,encoding='utf-8'); BACKEND.write_text(backend,encoding='utf-8')
print('VTX all-sample dBm matrix applied')
