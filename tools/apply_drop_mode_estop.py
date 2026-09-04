from pathlib import Path

path = Path("index.html")
s = path.read_text(encoding="utf-8")


def replace_once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"missing marker: {label}")
    s = s.replace(old, new, 1)


replace_once(
    ".file-size{color:var(--text-muted);font-size:13px;margin-top:4px}\n",
    ".file-size{color:var(--text-muted);font-size:13px;margin-top:4px}\n"
    ".drop-system-picker{margin-top:16px;padding:14px 16px;border:1px solid var(--border-color);border-radius:8px;background:var(--bg-card);display:flex;gap:12px;align-items:center;flex-wrap:wrap}\n"
    ".drop-system-picker label{font-size:12px;font-weight:800;color:var(--text-muted);text-transform:uppercase;letter-spacing:.4px}\n"
    ".drop-system-picker select{background:#0f141c;color:var(--text-main);border:1px solid var(--border-highlight);border-radius:6px;padding:9px 12px;font-weight:800}\n",
    "drop picker css",
)

replace_once(
    "/* Functional groups: SC+SF = dual drop (red), SD+SH = single drop (yellow). */\n"
    ".tx16-chip.drop-control{color:#fca5a5!important;border-color:rgba(239,68,68,.72)!important;background:rgba(239,68,68,.10)!important;font-weight:800}\n"
    ".tx16-chip.drop-control b{color:#fecaca!important}\n"
    ".tx16-chip.single-drop-control{color:#fde68a!important;border-color:rgba(245,158,11,.78)!important;background:rgba(245,158,11,.10)!important;font-weight:800}\n"
    ".tx16-chip.single-drop-control b{color:#fef3c7!important}\n"
    ".tx16-chip.drop-control.changed{box-shadow:0 0 0 1px rgba(239,68,68,.35) inset}\n"
    ".tx16-chip.single-drop-control.changed{box-shadow:0 0 0 1px rgba(245,158,11,.35) inset}\n",
    "/* Functional groups: SC+SF = drop system (red), SD+SH = EMERGENCY STOP (yellow). */\n"
    ".tx16-chip.drop-control{color:#fca5a5!important;border-color:rgba(239,68,68,.72)!important;background:rgba(239,68,68,.10)!important;font-weight:800}\n"
    ".tx16-chip.drop-control b{color:#fecaca!important}\n"
    ".tx16-chip.emergency-control{color:#fde68a!important;border-color:rgba(245,158,11,.78)!important;background:rgba(245,158,11,.10)!important;font-weight:800}\n"
    ".tx16-chip.emergency-control b{color:#fef3c7!important}\n"
    ".tx16-chip.drop-control.changed{box-shadow:0 0 0 1px rgba(239,68,68,.35) inset}\n"
    ".tx16-chip.emergency-control.changed{box-shadow:0 0 0 1px rgba(245,158,11,.35) inset}\n",
    "emergency css",
)

replace_once(
    '  <input id="fileInput" type="file" accept=".tlog">\n',
    '  <input id="fileInput" type="file" accept=".tlog">\n\n'
    '  <div class="drop-system-picker">\n'
    '    <label for="dropSystemType">Система скиду</label>\n'
    '    <select id="dropSystemType">\n'
    '      <option value="dual" selected>ПОДВІЙНА</option>\n'
    '      <option value="single">ОДИНОЧНА</option>\n'
    '    </select>\n'
    '  </div>\n',
    "drop selector html",
)

old_helpers = """function tx16SingleDropSafetyState(pwm){
  const pos=tx16ThreePos(pwm);
  if(pos===1||pos===2)return 'ЗАПОБІЖНИК АКТИВОВАНИЙ';
  if(pos===3)return 'ЗАПОБІЖНИК ЗНЯТО';
  return '—';
}
"""
new_helpers = """function tx16SingleDropSafetyState(pwm){
  const pos=tx16ThreePos(pwm);
  if(pos===1||pos===2)return 'ЗАПОБІЖНИК АКТИВОВАНИЙ';
  if(pos===3)return 'ЗНЯТО З ЗАПОБІЖНИКА';
  return '—';
}
function tx16EmergencyStopSafetyState(pwm){
  const pos=tx16ThreePos(pwm);
  if(pos===1||pos===2)return 'ЗАПОБІЖНИК АКТИВОВАНИЙ';
  if(pos===3)return 'ЗАПОБІЖНИК ЗНЯТО';
  return '—';
}
function currentDropSystemType(){
  const value=document.getElementById('dropSystemType')?.value;
  return value==='single'?'single':'dual';
}
function tx16DropSafetyState(pwm,dropSystemType=currentDropSystemType()){
  return dropSystemType==='single'?tx16SingleDropSafetyState(pwm):tx16DualDropSafetyState(pwm);
}
"""
replace_once(old_helpers, new_helpers, "safety helpers")

replace_once(
    "    sc:tx16DualDropSafetyState(r.sc), sf:tx16TwoPosHuman(r.sf,false),\n    sd:tx16SingleDropSafetyState(r.sd), sh:tx16TwoPosHuman(r.sh,true),\n",
    "    sc:tx16DropSafetyState(r.sc), sf:tx16TwoPosHuman(r.sf,false),\n    sd:tx16EmergencyStopSafetyState(r.sd), sh:tx16TwoPosHuman(r.sh,true),\n",
    "normalized states",
)

replace_once(
    "  return `<div class=\"tl-tx16s\">${chip('SA','sa')}${chip('SB','sb')}${chip('SC','sc','drop-control')}${chip('SF','sf','drop-control'+sfActive)}${chip('SD','sd','single-drop-control')}${chip('SH','sh','single-drop-control'+shActive)}</div>`;\n",
    "  return `<div class=\"tl-tx16s\">${chip('SA','sa')}${chip('SB','sb')}${chip('SC','sc','drop-control')}${chip('SF','sf','drop-control'+sfActive)}${chip('SD','sd','emergency-control')}${chip('SH','sh','emergency-control'+shActive)}</div>`;\n",
    "timeline chips",
)

replace_once(
    "    ${createCard('SC — CH15',uiSwitchSummary(collectChannel(15),tx16DualDropSafetyState),'Подвійний скид: ВІД СЕБЕ — запобіжник; СЕРЕДИНА — R; ДО СЕБЕ — L')}\n"
    "    ${createCard('SF — CH10',uiSwitchSummary(collectChannel(10),p=>tx16TwoPosHuman(p,false)),'Активатор подвійного скиду; скид рахується лише коли SC вибрано R або L')}\n"
    "    ${createCard('SD — CH13',uiSwitchSummary(collectChannel(13),tx16SingleDropSafetyState),'Одиночний скид: ВІД СЕБЕ/СЕРЕДИНА — запобіжник; ДО СЕБЕ — запобіжник знято')}\n"
    "    ${createCard('SH — CH6',uiSwitchSummary(collectChannel(6),p=>tx16TwoPosHuman(p,true)),'Активатор одиночного скиду; скид рахується лише коли SD=ЗАПОБІЖНИК ЗНЯТО')}\n",
    "    ${createCard('SC — CH15',uiSwitchSummary(collectChannel(15),p=>tx16DropSafetyState(p)),'Система скиду: ПОДВІЙНА — ВІД СЕБЕ запобіжник, СЕРЕДИНА R, ДО СЕБЕ L; ОДИНОЧНА — лише ДО СЕБЕ знімає запобіжник')}\n"
    "    ${createCard('SF — CH10',uiSwitchSummary(collectChannel(10),p=>tx16TwoPosHuman(p,false)),'Активатор системи скиду; трактування SC залежить від вибраного типу системи')}\n"
    "    ${createCard('SD — CH13',uiSwitchSummary(collectChannel(13),tx16EmergencyStopSafetyState),'EMERGENCY STOP: ВІД СЕБЕ/СЕРЕДИНА — запобіжник; ДО СЕБЕ — запобіжник знято')}\n"
    "    ${createCard('SH — CH6',uiSwitchSummary(collectChannel(6),p=>tx16TwoPosHuman(p,true)),'EMERGENCY STOP: активатор примусової зупинки моторів; валідно лише коли SD=ЗАПОБІЖНИК ЗНЯТО')}\n",
    "channel cards",
)

start = s.find("  function buildTx16ActivationAlerts(timeline){")
end = s.find("\n\n  const disarmedMovement=detectDisarmedPhysicalMovement(data);", start)
if start < 0 or end < 0:
    raise SystemExit("missing buildTx16ActivationAlerts section")
new_alert_fn = r'''  function buildTx16ActivationAlerts(timeline,dropSystemType){
    const rows=Array.isArray(timeline)?timeline:[];
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
          if(dropSystemType==='single'){
            if(scPos===3){
              dropEvents.push({time:row.time||'',kind:'single',pwm:rcPwmValue(row,10)});
            }
          }else{
            if(scPos===2||scPos===3){
              const side=scPos===2?'R':'L';
              dropEvents.push({time:row.time||'',kind:'dual',side,selector:tx16DualDropSafetyState(rcPwmValue(row,15)),pwm:rcPwmValue(row,10)});
            }
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
      if(dropSystemType==='single'){
        out.push(`<span class="ai-jump" data-jump-time="${ev.time}">🔴 <b>ОДИНОЧНИЙ СКИД${n} — SC + SF:</b> ${ev.time}; SC: ЗНЯТО З ЗАПОБІЖНИКА; SF: АКТИВАТОР УВІМКНЕНО${typeof ev.pwm==='number'?` (${Math.round(ev.pwm)} us)`:''}. Команда скиду підтверджена за каналами пульта; фізичне відділення вантажу TLOG напряму не підтверджує.</span>`);
      }else{
        out.push(`<span class="ai-jump" data-jump-time="${ev.time}">🔴 <b>СКИД ${ev.side}${n} — SC + SF:</b> ${ev.time}; SC: ${ev.selector}; SF: АКТИВАТОР УВІМКНЕНО${typeof ev.pwm==='number'?` (${Math.round(ev.pwm)} us)`:''}. Команда скиду підтверджена за каналами пульта; фізичне відділення вантажу TLOG напряму не підтверджує.</span>`);
      }
    });
    if(dropSystemType==='dual'){
      const sides=new Set(dropEvents.filter(ev=>ev.kind==='dual').map(ev=>ev.side));
      if(sides.has('R')&&sides.has('L')){
        out.push('🔴 <b>ЙМОВІРНО ПОДВІЙНИЙ СКИД:</b> зафіксовано окремі валідні команди R та L. Фізичне відділення двох вантажів потребує додаткового підтвердження за струмом/динамікою.');
      }
    }
    if((scTransitions.length||sfActivations.length)&&!dropEvents.length){
      const typeText=dropSystemType==='single'?'ОДИНОЧНА':'ПОДВІЙНА';
      out.push(`🟡 <b>СИСТЕМА СКИДУ (${typeText}):</b> були перемикання SC/SF, але валідний скид не підтверджено.`);
    }

    emergencyStopEvents.forEach((ev,i)=>{
      const n=emergencyStopEvents.length>1?` №${i+1}`:'';
      const duration=typeof ev.duration==='number'?ev.duration:null;
      const holdText=duration!==null?` SH утримувався приблизно ${duration.toFixed(1)} с.`:'';
      const cycleText=duration!==null&&duration>=9
        ?' Утримання відповідає приблизно 10-секундному циклу E-STOP.'
        :' Повний приблизно 10-секундний цикл E-STOP не підтверджено.';
      out.push(`<span class="ai-jump" data-jump-time="${ev.time}">🛑 <b>EMERGENCY STOP АКТИВОВАНО${n}:</b> ${ev.time}; SD: ЗАПОБІЖНИК ЗНЯТО; SH: АКТИВАТОР УВІМКНЕНО.${holdText}${cycleText} Це команда на примусову зупинку моторів; фактичну зупинку слід підтверджувати за RPM/ESC.</span>`);
    });
    return out;
  }
'''
s = s[:start] + new_alert_fn + s[end:]

replace_once(
    "  const combinedAiAlerts=[\n    ...highCurrentAlerts,\n    ...(data.ai?.alerts||[]),\n    ...buildTx16ActivationAlerts(data.timeline),\n",
    "  const dropSystemType=currentDropSystemType();\n  const combinedAiAlerts=[\n    ...highCurrentAlerts,\n    ...(data.ai?.alerts||[]),\n    ...buildTx16ActivationAlerts(data.timeline,dropSystemType),\n",
    "combined alert call",
)

path.write_text(s, encoding="utf-8")
print("patched index.html for selectable drop system and emergency stop")
