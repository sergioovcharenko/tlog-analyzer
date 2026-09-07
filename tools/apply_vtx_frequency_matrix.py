from pathlib import Path

INDEX = Path("index.html")
html = INDEX.read_text(encoding="utf-8")

css_marker = ".vtx-frequency-grid{"
if css_marker not in html:
    anchor = ".ai-box{"
    css = r'''.vtx-matrix-card{
  grid-column:span 3;
  background:var(--bg-card);
  border:1px solid var(--border-color);
  border-radius:8px;
  padding:18px;
}
.vtx-frequency-grid{
  display:grid;
  grid-template-columns:64px repeat(3,minmax(125px,1fr));
  gap:8px;
  align-items:stretch;
}
.vtx-frequency-band{
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight:800;
  color:var(--text-muted);
  border:1px solid var(--border-color);
  border-radius:6px;
  background:var(--bg-header);
}
.vtx-frequency-cell{
  border:1px solid var(--border-color);
  border-radius:6px;
  padding:9px 10px;
  background:var(--bg-header);
  min-width:0;
}
.vtx-frequency-main{font-size:15px;font-weight:800;white-space:nowrap}
.vtx-frequency-dbm{margin-top:2px;color:var(--text-muted);font-size:11px;white-space:nowrap}
.vtx-frequency-best{
  border-color:var(--success)!important;
  background:rgba(34,197,94,.12)!important;
  box-shadow:inset 0 0 0 1px rgba(34,197,94,.20);
}
.vtx-frequency-best .vtx-frequency-main{color:var(--success)}
@media(max-width:760px){
  .vtx-matrix-card{grid-column:1/-1}
  .vtx-frequency-grid{grid-template-columns:52px repeat(3,minmax(82px,1fr));gap:5px}
  .vtx-frequency-cell{padding:7px 5px}
  .vtx-frequency-main{font-size:12px}
  .vtx-frequency-dbm{font-size:9px}
}

'''
    if anchor not in html:
        raise SystemExit("CSS anchor not found")
    html = html.replace(anchor, css + anchor, 1)

old_helper = r'''function summarizeVtxFrequencySelections(timeline){
  const stats=new Map();
  let previous=null;
  let totalSwitches=0;
  for(const row of (Array.isArray(timeline)?timeline:[])){
    const freq=Number(row?.videoFreq);
    if(!Number.isFinite(freq)||freq<=0)continue;
    const f=Math.round(freq);
    if(!stats.has(f))stats.set(f,{frequency:f,switches:0});
    if(previous!==null&&f!==previous){
      stats.get(f).switches+=1;
      totalSwitches+=1;
    }
    previous=f;
  }
  return {
    totalSwitches,
    frequencies:[...stats.values()].sort((a,b)=>a.frequency-b.frequency)
  };
}'''

new_helper = r'''const VTX_STABLE_DBM_LIMIT=-85;
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

if old_helper in html:
    html = html.replace(old_helper, new_helper, 1)
elif new_helper not in html:
    raise SystemExit("VTX summary helper anchor not found")

old_video = r'''  const video=data.video||{};
  const vtxFlight=summarizeVtxFrequencySelections(data.timeline);
  document.getElementById('videoGrid').innerHTML=`
    ${createCard(
      'ВІДЕОЧАСТОТИ ЗА ПОЛІТ',
      vtxFlight.frequencies.length
        ?vtxFlight.frequencies.map(item=>`${item.frequency} MHz — ${item.switches} перемикань`).join('<br>')
        :'—',
      vtxFlight.frequencies.length
        ?`Усього перемикань між частотами: ${vtxFlight.totalSwitches}`
        :'Частоти визначаються з телеметрії VTX/CH7+CH8'
    )}
    ${createCard('Змін VTX',video.changeCount??vtxFlight.totalSwitches)}
  `;'''

new_video = r'''  const video=data.video||{};
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

if old_video in html:
    html = html.replace(old_video, new_video, 1)
elif new_video not in html:
    raise SystemExit("VTX render anchor not found")

INDEX.write_text(html, encoding="utf-8")
print("VTX frequency matrix applied")
