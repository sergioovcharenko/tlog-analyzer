from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"anchor not found: {label}")
    return text.replace(old, new, 1)


html = INDEX.read_text(encoding="utf-8")

helper_anchor = "function renderResults(data){"
helpers = r'''function summarizeEngineLoad(timeline){
  const values=(Array.isArray(timeline)?timeline:[])
    .filter(row=>row&&row.eventType==='SNAPSHOT'&&String(row.mode||'').toUpperCase()!=='DISARMED')
    .map(row=>Number(row.engineLoad))
    .filter(Number.isFinite)
    .map(v=>Math.max(0,Math.min(100,v)));
  if(!values.length)return null;
  const sum=values.reduce((a,b)=>a+b,0);
  return {
    avg:sum/values.length,
    min:Math.min(...values),
    max:Math.max(...values),
    samples:values.length
  };
}

function summarizeVtxFrequencySelections(timeline){
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
}

'''
if helpers not in html:
    if helper_anchor not in html:
        raise SystemExit("anchor not found: renderResults")
    html = html.replace(helper_anchor, helpers + helper_anchor, 1)

old_radio = r'''    ${createCard(
      'RADIO dBm',
      typeof data.radio?.worstDbm==='number'
        ?`MAX ${data.radio.worstDbm} dBm`
        :'—',
      typeof data.radio?.avgDbm==='number'
        ?`Середнє: ${data.radio.avgDbm.toFixed(1)} dBm (включно з -128)`
        :'Середнє значення недоступне'
    )}'''
new_radio = r'''    ${createCard(
      'RADIO dBm • СЕРЕДНЄ',
      typeof data.radio?.avgDbm==='number'
        ?`${data.radio.avgDbm.toFixed(1)} dBm`
        :'—',
      typeof data.radio?.worstDbm==='number'
        ?`Найгірше: ${data.radio.worstDbm} dBm • середнє включає -128`
        :'Найгірше значення недоступне'
    )}'''
html = replace_once(html, old_radio, new_radio, "RADIO dBm card")

old_health_tail = r'''    ${createCard(
      'Вібрації X/Y/Z',
      `${data.health?.vibX??'—'} / ${data.health?.vibY??'—'} / ${data.health?.vibZ??'—'}`
    )}
  `;

  const video=data.video||{};'''
new_health_tail = r'''    ${createCard(
      'Вібрації X/Y/Z',
      `${data.health?.vibX??'—'} / ${data.health?.vibY??'—'} / ${data.health?.vibZ??'—'}`
    )}
    ${(()=>{
      const engine=summarizeEngineLoad(data.timeline);
      return createCard(
        'ENGINE LOAD • СЕРЕДНЄ ЗА ПОЛІТ',
        engine?`${engine.avg.toFixed(1)} %`:'—',
        engine?`MIN ${engine.min.toFixed(1)}% • MAX ${engine.max.toFixed(1)}% • ${engine.samples} відліків`:'EFI_STATUS.engine_load у цьому польоті не знайдено'
      );
    })()}
  `;

  const video=data.video||{};'''
html = replace_once(html, old_health_tail, new_health_tail, "health grid tail")

old_video = r'''  const video=data.video||{};
  document.getElementById('videoGrid').innerHTML=`
    ${createCard(
      'VTX / Відеочастота',
      typeof video.frequency==='number'
        ?`${video.frequency} MHz`
        :'—',
      'Розрахунок за CH7 + CH8'
    )}
    ${createCard('Змін VTX',video.changeCount??0)}
  `;'''
new_video = r'''  const video=data.video||{};
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
html = replace_once(html, old_video, new_video, "VTX summary grid")

INDEX.write_text(html, encoding="utf-8")
print("dashboard flight summary integration applied")
