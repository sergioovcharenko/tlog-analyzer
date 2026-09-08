from pathlib import Path

INDEX=Path('index.html')
BACKEND=Path('backend/main.py')
html=INDEX.read_text(encoding='utf-8')
backend=BACKEND.read_text(encoding='utf-8')

if '.vtx-frequency-worst{' not in html:
    anchor='.vtx-frequency-best .vtx-frequency-main{color:var(--success)}'
    if anchor not in html: raise SystemExit('CSS anchor not found')
    html=html.replace(anchor,anchor+'''\n.vtx-frequency-worst{border-color:var(--danger)!important;background:rgba(239,68,68,.12)!important;box-shadow:inset 0 0 0 1px rgba(239,68,68,.20)}\n.vtx-frequency-worst .vtx-frequency-main{color:var(--danger)}''',1)

if '.vtx-frequency-header{' not in html:
    css_anchor='.vtx-frequency-band{\n  display:flex;'
    if css_anchor not in html: raise SystemExit('matrix CSS anchor not found')
    css='''.vtx-frequency-header{\n  display:flex;\n  align-items:center;\n  justify-content:center;\n  min-height:28px;\n  font-size:12px;\n  font-weight:800;\n  color:var(--text-muted);\n}\n.vtx-frequency-row-label{\n  display:flex;\n  align-items:center;\n  justify-content:center;\n  font-weight:800;\n  color:var(--text-muted);\n  border:1px solid var(--border-color);\n  border-radius:6px;\n  background:var(--bg-header);\n}\n'''
    html=html.replace(css_anchor,css+css_anchor,1)

old_helper=r'''const VTX_NORMAL_DBM_LIMIT=-85;
const VTX_MIN_STABILITY_SAMPLES=3;
const VTX_FREQUENCY_MATRIX={'5.2':[5180,5240,5300],'5.5':[5520,5580,5640],'5.8':[5700,5765,5825]};

function summarizeVtxFrequencySelections(timeline,frequencyDbmStats){'''
new_helper=r'''const VTX_NORMAL_DBM_LIMIT=-85;
const VTX_MIN_STABILITY_SAMPLES=3;
const VTX_FREQUENCY_MATRIX={'5.2':[5180,5240,5300],'5.5':[5520,5580,5640],'5.8':[5700,5765,5825]};
const VTX_MATRIX_ROWS=[
  {label:'K1',frequencies:[5180,5520,5700]},
  {label:'K2',frequencies:[5240,5580,5765]},
  {label:'K3',frequencies:[5300,5640,5825]}
];

function summarizeVtxFrequencySelections(timeline,frequencyDbmStats){'''
if old_helper in html:
    html=html.replace(old_helper,new_helper,1)
elif 'const VTX_MATRIX_ROWS=[' not in html:
    raise SystemExit('matrix rows anchor not found')

old_video=r'''  const video=data.video||{};
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
new_video=r'''  const video=data.video||{};
  const vtxFlight=summarizeVtxFrequencySelections(data.timeline,video.frequencyDbmStats);
  const vtxByFrequency=new Map(vtxFlight.frequencies.map(item=>[item.frequency,item]));
  const vtxCellHtml=freq=>{
    const item=vtxByFrequency.get(freq)||{switches:0,avgDbm:null,dbmSamples:0};
    const best=freq===vtxFlight.stableFrequency,worst=freq===vtxFlight.worstFrequency;
    const dbmText=item.dbmSamples>0&&item.avgDbm!==null?`AVG ${item.avgDbm.toFixed(1)} dBm`:'dBm —';
    return `<div class="vtx-frequency-cell${best?' vtx-frequency-best':''}${worst?' vtx-frequency-worst':''}"><div class="vtx-frequency-main">${freq} — ${item.switches}</div><div class="vtx-frequency-dbm">${dbmText}</div></div>`;
  };
  const vtxRowLabels={
    K1:'<div class="vtx-frequency-row-label">K1</div>',
    K2:'<div class="vtx-frequency-row-label">K2</div>',
    K3:'<div class="vtx-frequency-row-label">K3</div>'
  };
  const vtxMatrixHtml=`
    <div></div>
    <div class="vtx-frequency-header">5.2</div>
    <div class="vtx-frequency-header">5.5</div>
    <div class="vtx-frequency-header">5.8</div>
    ${VTX_MATRIX_ROWS.map(row=>`${vtxRowLabels[row.label]}${row.frequencies.map(vtxCellHtml).join('')}`).join('')}
  `;
  document.getElementById('videoGrid').innerHTML=`
    <div class="vtx-matrix-card">
      <div class="card-title">ВИКОРИСТАНІ VTX ЧАСТОТИ</div>
      <div class="vtx-frequency-grid">${vtxMatrixHtml}</div>
      <div class="card-desc">AVG = сума всіх RADIO/RADIO_STATUS dBm-відліків на активній частоті / кількість відліків; -128 включено. ≥ -85 dBm — норма. Зелена — найкраще середнє, червона — найгірше.</div>
    </div>
    ${createCard('Змін VTX',video.changeCount??vtxFlight.totalSwitches)}
  `;'''
if old_video in html:
    html=html.replace(old_video,new_video,1)
elif 'const vtxRowLabels={' not in html:
    raise SystemExit('video matrix anchor not found')

INDEX.write_text(html,encoding='utf-8')
BACKEND.write_text(backend,encoding='utf-8')
print('VTX column matrix applied')
