from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

# Version badge only (keep internal title/version comments untouched).
s=s.replace('>v1.3.3 «3D Lazy FIX»</div>','>BETA v1.0</div>',1)

# TX16 group colors + movement row style.
needle=""".tx16-chip.active{color:#22c55e;border-color:rgba(34,197,94,.45)}
.tx16-chip.stop{color:#f87171;border-color:rgba(239,68,68,.55);font-weight:900}
.tx16-empty{color:#64748b;font:10px monospace}
"""
repl=""".tx16-chip.active{color:#22c55e;border-color:rgba(34,197,94,.45)}
.tx16-chip.stop{color:#f87171;border-color:rgba(239,68,68,.55);font-weight:900}
/* Functional groups: SC+SF = drop system (red), SD+SH = Emergency Stop (yellow). */
.tx16-chip.drop-control{color:#fca5a5!important;border-color:rgba(239,68,68,.72)!important;background:rgba(239,68,68,.10)!important;font-weight:800}
.tx16-chip.drop-control b{color:#fecaca!important}
.tx16-chip.emergency-control{color:#fde68a!important;border-color:rgba(245,158,11,.78)!important;background:rgba(245,158,11,.10)!important;font-weight:800}
.tx16-chip.emergency-control b{color:#fef3c7!important}
.tx16-chip.drop-control.changed{box-shadow:0 0 0 1px rgba(239,68,68,.35) inset}
.tx16-chip.emergency-control.changed{box-shadow:0 0 0 1px rgba(245,158,11,.35) inset}
.tx16-empty{color:#64748b;font:10px monospace}
.disarmed-movement-row{background:rgba(245,158,11,.13)!important;box-shadow:inset 5px 0 0 #f59e0b}
.disarmed-movement-row .tl-analysis{color:#fde68a!important;font-weight:900}
"""
if needle not in s: raise SystemExit('CSS anchor not found')
s=s.replace(needle,repl,1)

# Add physical-movement detector before renderResults.
anchor='function renderResults(data){\n'
if anchor not in s: raise SystemExit('renderResults anchor not found')
fn=r'''function detectDisarmedPhysicalMovement(data){
  const sessionCount=Number(data?.flight?.flightSessionCount||0);
  if(sessionCount>0)return {events:[],alerts:[]};

  const rows=(Array.isArray(data?.timeline)?data.timeline:[])
    .filter(r=>r&&r.eventType==='SNAPSHOT'&&timelineSeconds(r.time)!==null);
  if(rows.length<2)return {events:[],alerts:[]};

  const numFromText=v=>{
    if(typeof v==='number'&&Number.isFinite(v))return v;
    const m=String(v??'').replace(',','.').match(/-?\d+(?:\.\d+)?/);
    return m?Number(m[0]):null;
  };
  const vals=(getter)=>rows.map(getter).filter(v=>typeof v==='number'&&Number.isFinite(v));
  const spread=a=>a.length?Math.max(...a)-Math.min(...a):0;

  const altSpread=spread(vals(r=>numFromText(r.alt)));
  const rollSpread=spread(vals(r=>r.attitude&&Number.isFinite(r.attitude.roll)?r.attitude.roll:null));
  const pitchSpread=spread(vals(r=>r.attitude&&Number.isFinite(r.attitude.pitch)?r.attitude.pitch:null));
  const distSpread=spread(vals(r=>numFromText(r.dist)));

  const signs=[];
  if(altSpread>=0.7)signs.push(`висота змінилась на ${altSpread.toFixed(1)} м`);
  if(Math.max(rollSpread,pitchSpread)>=15)signs.push(`Roll/Pitch змінилися до ${Math.max(rollSpread,pitchSpread).toFixed(1)}°`);
  if(distSpread>=2.0)signs.push(`позиційна дальність змінилась на ${distSpread.toFixed(1)} м`);

  // One noisy sensor is not enough: require at least two independent signs.
  if(signs.length<2)return {events:[],alerts:[]};

  const base=rows[0];
  const baseAlt=numFromText(base.alt);
  const baseDist=numFromText(base.dist);
  const baseRoll=base.attitude?.roll;
  const basePitch=base.attitude?.pitch;
  let strongest=rows[0], strongestScore=-1;
  rows.forEach(r=>{
    const a=numFromText(r.alt), d=numFromText(r.dist);
    const rr=r.attitude?.roll, pp=r.attitude?.pitch;
    let score=0;
    if(baseAlt!==null&&a!==null)score+=Math.abs(a-baseAlt)*2;
    if(baseDist!==null&&d!==null)score+=Math.abs(d-baseDist);
    if(Number.isFinite(baseRoll)&&Number.isFinite(rr))score+=Math.abs(rr-baseRoll)/5;
    if(Number.isFinite(basePitch)&&Number.isFinite(pp))score+=Math.abs(pp-basePitch)/5;
    if(score>strongestScore){strongestScore=score;strongest=r;}
  });

  const level=signs.length>=3?'ПІДТВЕРДЖЕНІ ОЗНАКИ':'ЙМОВІРНЕ ПЕРЕМІЩЕННЯ';
  const text=`⚠️ ${level}: зафіксовано ознаки фізичного переміщення заживленого БПЛА при DISARMED — ${signs.join('; ')}.`;
  const ev={...strongest,eventType:'DISARMED_PHYSICAL_MOVEMENT',analysisText:text,isError:false,systemText:strongest.systemText||''};
  const alert=`<span class="ai-jump" data-jump-time="${strongest.time||''}">⚠️ <b>Ознаки фізичного переміщення заживленого БПЛА при DISARMED:</b> ${signs.join('; ')}. TLOG підтверджує телеметричні ознаки руху, але не встановлює процедурну причину. Натисніть, щоб перейти до Timeline.</span>`;
  return {events:[ev],alerts:[alert]};
}

'''
s=s.replace(anchor,fn+anchor,1)

# Insert movement result before combined AI alerts, so it is conditional and included in Timeline.
needle="""  const combinedAiAlerts=[
    ...(data.ai?.alerts||[]),
    ...buildTx16ActivationAlerts(data.timeline)
  ];
"""
repl="""  const disarmedMovement=detectDisarmedPhysicalMovement(data);
  if(disarmedMovement.events.length){
    data.timeline=[...(Array.isArray(data.timeline)?data.timeline:[]),...disarmedMovement.events]
      .sort((a,b)=>(timelineSeconds(a?.time)??0)-(timelineSeconds(b?.time)??0));
  }

  const combinedAiAlerts=[
    ...(data.ai?.alerts||[]),
    ...buildTx16ActivationAlerts(data.timeline),
    ...disarmedMovement.alerts
  ];
"""
if needle not in s: raise SystemExit('AI alerts anchor not found')
s=s.replace(needle,repl,1)

# Distinct TX16 group colors in compact Timeline.
needle="""  const sfActive=cur.sf==='УВІМКНЕНО'?'active':'';
  const shActive=(cur.sh==='НАТИСНУТО'&&cur.sd==='ДО СЕБЕ')?'stop':'';
  return `<div class="tl-tx16s">${chip('SA','sa')}${chip('SB','sb')}${chip('SC','sc')}${chip('SF','sf',sfActive)}${chip('SD','sd')}${chip('SH','sh',shActive)}${chip('LS','ls')}${chip('RS','rs')}</div>`;
"""
repl="""  const sfActive=cur.sf==='УВІМКНЕНО'?' active':'';
  const shActive=(cur.sh==='НАТИСНУТО'&&cur.sd==='ДО СЕБЕ')?' stop':'';
  return `<div class="tl-tx16s">${chip('SA','sa')}${chip('SB','sb')}${chip('SC','sc','drop-control')}${chip('SF','sf','drop-control'+sfActive)}${chip('SD','sd','emergency-control')}${chip('SH','sh','emergency-control'+shActive)}${chip('LS','ls')}${chip('RS','rs')}</div>`;
"""
if needle not in s: raise SystemExit('TX16 chip anchor not found')
s=s.replace(needle,repl,1)

# Timeline movement row class.
needle="""    if(item.eventType==='COMMUNICATION_RESTORED')rowClass+=' communication-restored-row';
"""
repl="""    if(item.eventType==='COMMUNICATION_RESTORED')rowClass+=' communication-restored-row';
    if(item.eventType==='DISARMED_PHYSICAL_MOVEMENT')rowClass+=' disarmed-movement-row';
"""
if needle not in s: raise SystemExit('row class anchor not found')
s=s.replace(needle,repl,1)

p.write_text(s,encoding='utf-8')
print('movement/version/TX16 color patch applied')
