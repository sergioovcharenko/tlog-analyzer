from pathlib import Path

path = Path("index.html")
s = path.read_text(encoding="utf-8")


def replace_once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"missing marker: {label}")
    s = s.replace(old, new, 1)


# Remove manual system selector UI/CSS.
replace_once(
    ".drop-system-picker{margin-top:16px;padding:14px 16px;border:1px solid var(--border-color);border-radius:8px;background:var(--bg-card);display:flex;gap:12px;align-items:center;flex-wrap:wrap}\n"
    ".drop-system-picker label{font-size:12px;font-weight:800;color:var(--text-muted);text-transform:uppercase;letter-spacing:.4px}\n"
    ".drop-system-picker select{background:#0f141c;color:var(--text-main);border:1px solid var(--border-highlight);border-radius:6px;padding:9px 12px;font-weight:800}\n",
    "",
    "drop selector css",
)
replace_once(
    '  <div class="drop-system-picker">\n'
    '    <label for="dropSystemType">Система скиду</label>\n'
    '    <select id="dropSystemType">\n'
    '      <option value="dual" selected>ПОДВІЙНА</option>\n'
    '      <option value="single">ОДИНОЧНА</option>\n'
    '    </select>\n'
    '  </div>\n',
    "",
    "drop selector html",
)

# Keep both interpretation helpers, but display SC neutrally until the whole log is evaluated.
replace_once(
    "function currentDropSystemType(){\n"
    "  const value=document.getElementById('dropSystemType')?.value;\n"
    "  return value==='single'?'single':'dual';\n"
    "}\n"
    "function tx16DropSafetyState(pwm,dropSystemType=currentDropSystemType()){\n"
    "  return dropSystemType==='single'?tx16SingleDropSafetyState(pwm):tx16DualDropSafetyState(pwm);\n"
    "}\n",
    "function tx16DropSafetyState(pwm){\n"
    "  const pos=tx16ThreePos(pwm);\n"
    "  if(pos===1)return 'ЗАПОБІЖНИК АКТИВОВАНИЙ';\n"
    "  if(pos===2)return 'СЕРЕДИНА';\n"
    "  if(pos===3)return 'ДО СЕБЕ';\n"
    "  return '—';\n"
    "}\n",
    "drop state display helper",
)

replace_once(
    "    ${createCard('SC — CH15',uiSwitchSummary(collectChannel(15),p=>tx16DropSafetyState(p)),'Система скиду: ПОДВІЙНА — ВІД СЕБЕ запобіжник, СЕРЕДИНА R, ДО СЕБЕ L; ОДИНОЧНА — лише ДО СЕБЕ знімає запобіжник')}\n"
    "    ${createCard('SF — CH10',uiSwitchSummary(collectChannel(10),p=>tx16TwoPosHuman(p,false)),'Активатор системи скиду; трактування SC залежить від вибраного типу системи')}\n",
    "    ${createCard('SC — CH15',uiSwitchSummary(collectChannel(15),p=>tx16DropSafetyState(p)),'Запобіжник системи скиду. Тип системи (одиночна/подвійна) визначається автоматично за поведінкою SC + SF у логу')}\n"
    "    ${createCard('SF — CH10',uiSwitchSummary(collectChannel(10),p=>tx16TwoPosHuman(p,false)),'Активатор системи скиду; аналізатор автоматично оцінює тип системи за положенням SC у моменти активації SF')}\n",
    "drop channel descriptions",
)

start = s.find("  function buildTx16ActivationAlerts(timeline,dropSystemType){")
end = s.find("\n\n  const disarmedMovement=detectDisarmedPhysicalMovement(data);", start)
if start < 0 or end < 0:
    raise SystemExit("missing buildTx16ActivationAlerts section")

new_block = r'''  function inferDropSystemType(timeline){
    const rows=Array.isArray(timeline)?timeline:[];
    let prevSf=null;
    let middleSfActivations=0;
    let towardSfActivations=0;
    let safetySfActivations=0;

    rows.forEach(row=>{
      if(!row)return;
      const sf=tx16HighActive(rcPwmValue(row,10));
      const scPos=tx16ThreePos(rcPwmValue(row,15));
      if(sf!==null){
        if(prevSf===false && sf===true){
          if(scPos===2)middleSfActivations++;
          else if(scPos===3)towardSfActivations++;
          else safetySfActivations++;
        }
        prevSf=sf;
      }
    });

    if(middleSfActivations>0){
      return {
        type:'dual', confidence:'high', middleSfActivations, towardSfActivations, safetySfActivations,
        reason:`SF активувався при SC=СЕРЕДИНА ${middleSfActivations} раз(и); для одиночної системи середнє положення лишається на запобіжнику.`
      };
    }
    if(towardSfActivations>0){
      return {
        type:'single', confidence:'medium', middleSfActivations, towardSfActivations, safetySfActivations,
        reason:`усі робочі активації SF зафіксовані при SC=ДО СЕБЕ (${towardSfActivations}). Це відповідає одиночній системі, але така сама команда можлива як L у подвійній системі.`
      };
    }
    return {
      type:'unknown', confidence:'low', middleSfActivations, towardSfActivations, safetySfActivations,
      reason:'у логу немає достатньої кількості валідних активацій SF при робочих положеннях SC.'
    };
  }

  function buildTx16ActivationAlerts(timeline){
    const rows=Array.isArray(timeline)?timeline:[];
    const inferredDropSystem=inferDropSystemType(rows);
    const dropEvents=[];
    const emergencyStopEvents=[];
    const scTransitions=[];
    const sfActivations=[];
    let prevSf=null, prevSh=null, prevScPos=null;
    let emergencyStart=null;

    rows.forEach(row=>{
      if(!row)return;
      const sf=tx16HighActive(rcPwmValue(row,10));
      const sh=tx16HighActive(rcPwmValue(row,6));
      const scPos=tx16ThreePos(rcPwmValue(row,15));
      const sdPos=tx16ThreePos(rcPwmValue(row,13));
      const rowSec=timelineSeconds(row.time);

      if(scPos){
        if(prevScPos!==null&&scPos!==prevScPos){
          scTransitions.push({time:row.time||'',from:prevScPos,to:scPos});
        }
        prevScPos=scPos;
      }

      if(sf!==null){
        if(prevSf===false && sf===true){
          sfActivations.push({time:row.time||'',scPos,pwm:rcPwmValue(row,10)});
          if(inferredDropSystem.type==='single'){
            if(scPos===3){
              dropEvents.push({time:row.time||'',kind:'single',pwm:rcPwmValue(row,10)});
            }
          }else if(inferredDropSystem.type==='dual'){
            if(scPos===2||scPos===3){
              const side=scPos===2?'R':'L';
              dropEvents.push({time:row.time||'',kind:'dual',side,selector:tx16DualDropSafetyState(rcPwmValue(row,15)),pwm:rcPwmValue(row,10)});
            }
          }else if(scPos===3){
            dropEvents.push({time:row.time||'',kind:'ambiguous',pwm:rcPwmValue(row,10)});
          }
        }
        prevSf=sf;
      }

      if(sh!==null){
        if(prevSh===false && sh===true && sdPos===3){
          emergencyStart={time:row.time||'',startSec:rowSec,lastSec:rowSec,pwm:rcPwmValue(row,6)};
        }else if(emergencyStart&&sh===true&&sdPos===3&&rowSec!==null){
          emergencyStart.lastSec=rowSec;
        }
        if(emergencyStart&&(sh===false||sdPos!==3)){
          const endSec=rowSec!==null?rowSec:emergencyStart.lastSec;
          emergencyStopEvents.push({...emergencyStart,duration:(endSec!==null&&emergencyStart.startSec!==null)?Math.max(0,endSec-emergencyStart.startSec):null});
          emergencyStart=null;
        }
        prevSh=sh;
      }
    });
    if(emergencyStart){
      emergencyStopEvents.push({...emergencyStart,duration:(emergencyStart.lastSec!==null&&emergencyStart.startSec!==null)?Math.max(0,emergencyStart.lastSec-emergencyStart.startSec):null});
    }

    const out=[];
    if(inferredDropSystem.type==='dual'){
      out.push(`🎯 <b>ЙМОВІРНИЙ ТИП СИСТЕМИ СКИДУ: ПОДВІЙНА — висока впевненість.</b> ${inferredDropSystem.reason}`);
    }else if(inferredDropSystem.type==='single'){
      out.push(`🎯 <b>ЙМОВІРНИЙ ТИП СИСТЕМИ СКИДУ: ОДИНОЧНА — середня впевненість.</b> ${inferredDropSystem.reason}`);
    }else{
      out.push(`⚪ <b>ТИП СИСТЕМИ СКИДУ НЕМОЖЛИВО ВИЗНАЧИТИ ОДНОЗНАЧНО.</b> ${inferredDropSystem.reason}`);
    }

    if(scTransitions.length){
      const first=scTransitions[0];
      out.push(`<span class="ai-jump" data-jump-time="${first.time}">🎚 <b>SC: зафіксовано ${scTransitions.length} перемикань.</b>${first.time?` Перше — ${first.time}.`:''} Натисніть, щоб перейти до першого перемикання.</span>`);
    }
    if(sfActivations.length){
      const first=sfActivations[0];
      out.push(`<span class="ai-jump" data-jump-time="${first.time}">🎚 <b>SF: зафіксовано ${sfActivations.length} активацій.</b>${first.time?` Перша — ${first.time}.`:''} Натисніть, щоб перейти до першої активації.</span>`);
    }

    dropEvents.forEach((ev,i)=>{
      const n=dropEvents.length>1?` №${i+1}`:'';
      if(ev.kind==='single'){
        out.push(`<span class="ai-jump" data-jump-time="${ev.time}">🔴 <b>ОДИНОЧНИЙ СКИД${n} — SC + SF:</b> ${ev.time}; SC: ЗНЯТО З ЗАПОБІЖНИКА; SF: АКТИВАТОР УВІМКНЕНО${typeof ev.pwm==='number'?` (${Math.round(ev.pwm)} us)`:''}. Команда підтверджена за каналами пульта; фізичне відділення вантажу TLOG напряму не підтверджує.</span>`);
      }else if(ev.kind==='dual'){
        out.push(`<span class="ai-jump" data-jump-time="${ev.time}">🔴 <b>СКИД ${ev.side}${n} — SC + SF:</b> ${ev.time}; SC: ${ev.selector}; SF: АКТИВАТОР УВІМКНЕНО${typeof ev.pwm==='number'?` (${Math.round(ev.pwm)} us)`:''}. Команда підтверджена за каналами пульта; фізичне відділення вантажу TLOG напряму не підтверджує.</span>`);
      }else{
        out.push(`<span class="ai-jump" data-jump-time="${ev.time}">🟡 <b>КОМАНДА СКИДУ — SC + SF:</b> ${ev.time}; SC=ДО СЕБЕ, SF=УВІМКНЕНО. За цим епізодом неможливо відрізнити одиночну систему від команди L подвійної системи.</span>`);
      }
    });

    if(inferredDropSystem.type==='dual'){
      const sides=new Set(dropEvents.filter(ev=>ev.kind==='dual').map(ev=>ev.side));
      if(sides.has('R')&&sides.has('L')){
        out.push('🔴 <b>ЙМОВІРНО ПОДВІЙНИЙ СКИД:</b> зафіксовано окремі валідні команди R та L. Фізичне відділення двох вантажів потребує додаткового підтвердження за струмом/динамікою.');
      }
    }
    if((scTransitions.length||sfActivations.length)&&!dropEvents.length){
      out.push('🟡 <b>СИСТЕМА СКИДУ:</b> були перемикання SC/SF, але валідний скид не підтверджено.');
    }

    emergencyStopEvents.forEach((ev,i)=>{
      const n=emergencyStopEvents.length>1?` №${i+1}`:'';
      const dur=typeof ev.duration==='number'?ev.duration:null;
      const durationText=dur!==null?` Утримання SH ≈ ${dur.toFixed(1)} с.`:'';
      const cycleText=dur!==null&&dur>=8?' Повний цикл близький до 10 с.':' Для повного циклу очікується утримання близько 10 с.';
      out.push(`<span class="ai-jump" data-jump-time="${ev.time}">🛑 <b>EMERGENCY STOP АКТИВОВАНО${n}:</b> ${ev.time}; SD=ДО СЕБЕ (запобіжник знято) + SH=НАТИСНУТО.${durationText}${cycleText} Це команда примусової зупинки моторів; факт зупинки потрібно підтверджувати за RPM/ESC.</span>`);
    });
    return out;
  }'''

s = s[:start] + new_block + s[end:]

replace_once(
    "  const dropSystemType=currentDropSystemType();\n"
    "  const combinedAiAlerts=[\n"
    "    ...highCurrentAlerts,\n"
    "    ...(data.ai?.alerts||[]),\n"
    "    ...buildTx16ActivationAlerts(data.timeline,dropSystemType),\n",
    "  const combinedAiAlerts=[\n"
    "    ...highCurrentAlerts,\n"
    "    ...(data.ai?.alerts||[]),\n"
    "    ...buildTx16ActivationAlerts(data.timeline),\n",
    "combined alerts automatic drop analysis",
)

path.write_text(s, encoding="utf-8")
