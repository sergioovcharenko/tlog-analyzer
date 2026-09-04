from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

css_anchor=""".disarmed-movement-row{background:rgba(245,158,11,.13)!important;box-shadow:inset 5px 0 0 #f59e0b}
.disarmed-movement-row .tl-analysis{color:#fde68a!important;font-weight:900}
"""
css_repl=css_anchor+""".esc-fault-row{background:rgba(239,68,68,.14)!important;box-shadow:inset 5px 0 0 #ef4444}
.esc-fault-row .tl-analysis{color:#fecaca!important;font-weight:900}
"""
if css_anchor not in s:
    raise SystemExit('ESC CSS anchor not found')
s=s.replace(css_anchor,css_repl,1)

anchor='function renderResults(data){\n'
if anchor not in s:
    raise SystemExit('renderResults anchor not found')

fn=r'''const ESC_FAULT_MIN_PERSIST_SEC=1.5;
const ESC_RPM_DEFICIT_RATIO=0.65;
const ESC_CURRENT_DEFICIT_RATIO=0.60;
const ESC_ZERO_TELEM_MAX_SEC=1.0;

function buildEscPowertrainAlerts(timeline){
  const rows=(Array.isArray(timeline)?timeline:[])
    .filter(r=>r&&r.eventType==='SNAPSHOT'&&Number.isFinite(r.flightNumber)&&Array.isArray(r.esc)&&timelineSeconds(r.time)!==null)
    .slice()
    .sort((a,b)=>timelineSeconds(a.time)-timelineSeconds(b.time));

  const median=a=>{
    const v=a.filter(x=>typeof x==='number'&&Number.isFinite(x)).slice().sort((x,y)=>x-y);
    if(!v.length)return null;
    const m=Math.floor(v.length/2);
    return v.length%2?v[m]:(v[m-1]+v[m])/2;
  };
  const escById=row=>{
    const out={};
    (row.esc||[]).forEach(e=>{if(e&&Number.isFinite(+e.id))out[+e.id]=e;});
    return out;
  };

  const flights=new Map();
  rows.forEach(r=>{
    const n=+r.flightNumber;
    if(!flights.has(n))flights.set(n,[]);
    flights.get(n).push(r);
  });

  const alerts=[];
  const events=[];
  const telemetryGaps=[];

  flights.forEach((flightRows,flightNumber)=>{
    const startSec=timelineSeconds(flightRows[0]?.time);
    const endSec=timelineSeconds(flightRows[flightRows.length-1]?.time);
    const flightDuration=(startSec!==null&&endSec!==null)?Math.max(0,endSec-startSec):0;

    for(let motor=1;motor<=4;motor++){
      let candidate=null;
      let zeroCandidate=null;
      let firstConfirmed=null;

      const closeCandidate=(endRow)=>{
        if(!candidate)return;
        const end=timelineSeconds(endRow?.time??candidate.lastTime);
        const duration=(candidate.startSec!==null&&end!==null)?Math.max(0,end-candidate.startSec):0;
        if(duration>=ESC_FAULT_MIN_PERSIST_SEC && candidate.samples>=2){
          const confirmedByCurrent=candidate.currentCorroboratedSamples>0;
          const confirmedByNonzeroRpm=candidate.nonzeroDeficitSamples>=2;
          if(confirmedByCurrent||confirmedByNonzeroRpm){
            if(!firstConfirmed)firstConfirmed={...candidate,duration,confirmedByCurrent,confirmedByNonzeroRpm};
          }
        }
        candidate=null;
      };

      const closeZeroCandidate=(endRow)=>{
        if(!zeroCandidate)return;
        const end=timelineSeconds(endRow?.time??zeroCandidate.lastTime);
        const duration=(zeroCandidate.startSec!==null&&end!==null)?Math.max(0,end-zeroCandidate.startSec):0;
        const rpmZeroIsTelemetryOnly=zeroCandidate.currentCorroboratedSamples===0 && duration<=ESC_ZERO_TELEM_MAX_SEC;
        if(rpmZeroIsTelemetryOnly){
          telemetryGaps.push({flightNumber,motor,time:zeroCandidate.firstTime,duration,text:'короткочасна втрата RPM-телеметрії'});
        }
        zeroCandidate=null;
      };

      flightRows.forEach((row,idx)=>{
        const map=escById(row);
        const own=map[motor]||{};
        const rpm=Number.isFinite(+own.rpm)?+own.rpm:null;
        const current=Number.isFinite(+own.current)?+own.current:null;
        const peerRpms=[];
        const peerCurrents=[];
        for(let id=1;id<=4;id++){
          if(id===motor)continue;
          const e=map[id]||{};
          if(Number.isFinite(+e.rpm)&&+e.rpm>800)peerRpms.push(+e.rpm);
          if(Number.isFinite(+e.current)&&+e.current>=0)peerCurrents.push(+e.current);
        }
        const peerRpm=median(peerRpms);
        const peerCurrent=median(peerCurrents);
        const peersActive=peerRpm!==null&&peerRpm>1200;
        const rpmZero=(rpm===0);
        const rpmDeficit=peersActive&&rpm!==null&&rpm<peerRpm*ESC_RPM_DEFICIT_RATIO;
        const currentCorroborated=current!==null&&peerCurrent!==null&&peerCurrent>=2&&current<peerCurrent*ESC_CURRENT_DEFICIT_RATIO;
        const persistentRpmDeficit=rpmDeficit;
        const t=timelineSeconds(row.time);

        if(rpmZero&&peersActive){
          if(!zeroCandidate)zeroCandidate={startSec:t,firstTime:row.time,lastTime:row.time,currentCorroboratedSamples:0};
          zeroCandidate.lastTime=row.time;
          if(currentCorroborated)zeroCandidate.currentCorroboratedSamples++;
        }else{
          closeZeroCandidate(row);
        }

        if(persistentRpmDeficit){
          if(!candidate){
            candidate={startSec:t,firstTime:row.time,lastTime:row.time,samples:0,currentCorroboratedSamples:0,nonzeroDeficitSamples:0,maxDeficitPct:0,firstRow:row};
          }
          candidate.lastTime=row.time;
          candidate.samples++;
          if(currentCorroborated)candidate.currentCorroboratedSamples++;
          if(rpm!==null&&rpm>0)candidate.nonzeroDeficitSamples++;
          if(peerRpm&&rpm!==null){
            candidate.maxDeficitPct=Math.max(candidate.maxDeficitPct,(1-rpm/peerRpm)*100);
          }
        }else{
          closeCandidate(row);
        }

        if(idx===flightRows.length-1){
          closeCandidate(row);
          closeZeroCandidate(row);
        }
      });

      if(!firstConfirmed)continue;

      const firstAnomalyTime=firstConfirmed.firstTime;
      const firstSec=timelineSeconds(firstAnomalyTime);
      const fromStart=(firstSec!==null&&startSec!==null)?Math.max(0,firstSec-startSec):null;
      const toEnd=(firstSec!==null&&endSec!==null)?Math.max(0,endSec-firstSec):null;
      let phase='у середині польоту';
      if(fromStart!==null&&(fromStart<=15 || (flightDuration>0&&fromStart<=flightDuration*0.20)))phase='на початку польоту';
      else if(toEnd!==null&&(toEnd<=15 || (flightDuration>0&&toEnd<=flightDuration*0.20)))phase='наприкінці польоту';

      const evidence=[];
      evidence.push(`стійкий дефіцит RPM до ${firstConfirmed.maxDeficitPct.toFixed(0)}%`);
      if(firstConfirmed.confirmedByCurrent)evidence.push('одночасно знижений струм ESC');
      if(firstConfirmed.confirmedByNonzeroRpm)evidence.push('аномалія підтверджена не лише нульовими RPM-пакетами');

      const text=`🔴 ЙМОВІРНА НЕСПРАВНІСТЬ MOTOR/ESC ${motor}: ${evidence.join('; ')}. Вперше помітно ${phase} (${firstAnomalyTime}), тривалість підтвердженої аномалії ≈ ${firstConfirmed.duration.toFixed(1)} с. Одиничний RPM=0 без стійкості/підтвердження струмом не вважається відмовою.`;
      alerts.push(`<span class="ai-jump" data-jump-time="${firstAnomalyTime}">${text} Можливі причини: двигун, ESC, силове з'єднання або живлення; TLOG не встановлює конкретну фізичну причину. Натисніть, щоб перейти до Timeline.</span>`);
      events.push({...firstConfirmed.firstRow,eventType:'ESC_POWERTRAIN_FAULT',analysisText:text,isError:true,systemText:firstConfirmed.firstRow?.systemText||''});
    }
  });

  return {alerts,events,telemetryGaps};
}

'''
s=s.replace(anchor,fn+anchor,1)

old="""  const disarmedMovement=detectDisarmedPhysicalMovement(data);
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
new="""  const disarmedMovement=detectDisarmedPhysicalMovement(data);
  if(disarmedMovement.events.length){
    data.timeline=[...(Array.isArray(data.timeline)?data.timeline:[]),...disarmedMovement.events]
      .sort((a,b)=>(timelineSeconds(a?.time)??0)-(timelineSeconds(b?.time)??0));
  }

  const escPowertrain=buildEscPowertrainAlerts(data.timeline);
  if(escPowertrain.events.length){
    data.timeline=[...(Array.isArray(data.timeline)?data.timeline:[]),...escPowertrain.events]
      .sort((a,b)=>(timelineSeconds(a?.time)??0)-(timelineSeconds(b?.time)??0));
  }

  const combinedAiAlerts=[
    ...(data.ai?.alerts||[]),
    ...buildTx16ActivationAlerts(data.timeline),
    ...disarmedMovement.alerts,
    ...escPowertrain.alerts
  ];
"""
if old not in s:
    raise SystemExit('AI alert integration anchor not found')
s=s.replace(old,new,1)

row_anchor="""    if(item.eventType==='DISARMED_PHYSICAL_MOVEMENT')rowClass+=' disarmed-movement-row';
"""
row_repl=row_anchor+"""    if(item.eventType==='ESC_POWERTRAIN_FAULT')rowClass+=' esc-fault-row';
"""
if row_anchor not in s:
    raise SystemExit('Timeline row anchor not found')
s=s.replace(row_anchor,row_repl,1)

p.write_text(s,encoding='utf-8')
print('ESC fault diagnosis patch applied')
