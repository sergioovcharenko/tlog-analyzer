from pathlib import Path

p = Path("index.html")
s = p.read_text(encoding="utf-8")

# 1) AI control analysis: confirmed aircraft mapping and Emergency Stop logic.
start = s.index("  // V23.11 — короткий підсумок фактичних активацій TX16S")
end = s.index("\n  const combinedAiAlerts=[", start)
new = r'''  // TX16S: підтверджена схема цього борта.
  // SA=CH7, SB=CH8 — VTX; SC=CH15 + SF=CH10 — система скиду;
  // SD=CH13 + SH=CH6 — EMERGENCY STOP; LS=CH12; RS=CH9.
  // Аналіз лише читає RC_CHANNELS і не відправляє команди на борт.
  function timelineSeconds(t){
    const m=String(t||'').match(/(-?)(\d+):(\d+(?:\.\d+)?)/);
    if(!m)return null;
    const v=(+m[2])*60+(+m[3]);
    return m[1]==='-'?-v:v;
  }

  function buildTx16ActivationAlerts(timeline){
    const rows=Array.isArray(timeline)?timeline:[];
    const dropEvents=[];
    const emergencyEvents=[];
    const emergencyBlocked=[];
    let prevSf=null, prevSh=null;
    let shStart=null;

    rows.forEach((row,idx)=>{
      if(!row)return;
      const sc=rcPwmValue(row,15);
      const sd=rcPwmValue(row,13);
      const sf=tx16HighActive(rcPwmValue(row,10));
      const sh=tx16HighActive(rcPwmValue(row,6));
      const scState=tx16ThreePosHuman(sc);
      const sdState=tx16ThreePosHuman(sd);

      if(sf!==null){
        if(prevSf===false && sf===true){
          dropEvents.push({time:row.time||'',selector:scState,pwm:rcPwmValue(row,10)});
        }
        prevSf=sf;
      }

      if(sh!==null){
        if(prevSh===false && sh===true){
          if(sdState==='ДО СЕБЕ'){
            shStart={time:row.time||'',seconds:timelineSeconds(row.time),pwm:rcPwmValue(row,6)};
          }else{
            emergencyBlocked.push({time:row.time||'',selector:sdState,pwm:rcPwmValue(row,6)});
          }
        }
        if(prevSh===true && sh===false && shStart){
          const endSec=timelineSeconds(row.time);
          const duration=(shStart.seconds!==null&&endSec!==null)?Math.max(0,endSec-shStart.seconds):null;
          emergencyEvents.push({time:shStart.time,endTime:row.time||'',duration,pwm:shStart.pwm});
          shStart=null;
        }
        prevSh=sh;
      }

      if(idx===rows.length-1 && shStart){
        const endSec=timelineSeconds(row.time);
        const duration=(shStart.seconds!==null&&endSec!==null)?Math.max(0,endSec-shStart.seconds):null;
        emergencyEvents.push({time:shStart.time,endTime:row.time||'',duration,pwm:shStart.pwm});
        shStart=null;
      }
    });

    const out=[];
    if(dropEvents.length){
      dropEvents.forEach((ev,i)=>{
        const n=dropEvents.length>1?` №${i+1}`:'';
        out.push(`<span class="ai-jump" data-jump-time="${ev.time}">🎚 <b>СКИД${n} — SC + SF:</b> ${ev.time}; SC (запобіжник): ${ev.selector}; SF (активатор): УВІМКНЕНО${typeof ev.pwm==='number'?` (${Math.round(ev.pwm)} us)`:''}. Натисніть, щоб перейти до Timeline.</span>`);
      });
      const kind=dropEvents.length===1?'ОДИНОЧНИЙ СКИД':`ПОДВІЙНИЙ / ПОВТОРНИЙ СКИД (${dropEvents.length} активації)`;
      out.push(`🎚 <b>Підсумок системи скиду:</b> ${kind}.`);
    }else{
      out.push('🎚 <b>SC + SF:</b> активацій системи скиду у TLOG не зафіксовано.');
    }

    if(emergencyEvents.length){
      emergencyEvents.forEach((ev,i)=>{
        const n=emergencyEvents.length>1?` №${i+1}`:'';
        const d=typeof ev.duration==='number'?`${ev.duration.toFixed(2)} с`:'невідомо';
        const ten=(typeof ev.duration==='number'&&ev.duration>=9.8)?' • утримано приблизно 10 с':'';
        out.push(`<span class="ai-jump" data-jump-time="${ev.time}">🛑 <b>EMERGENCY STOP${n} — команда активатора:</b> ${ev.time}; SD: ДО СЕБЕ (запобіжник дозволив); SH утримувався ${d}${ten}. Натисніть, щоб перейти до Timeline.</span>`);
      });
    }else{
      out.push('🛑 <b>EMERGENCY STOP:</b> валідної активації SD=ДО СЕБЕ + SH не зафіксовано.');
    }
    emergencyBlocked.forEach(ev=>{
      out.push(`⚠️ <b>SH натиснуто без дозволу Emergency Stop:</b> ${ev.time}; SD: ${ev.selector}. Як Emergency Stop не зараховано.`);
    });
    return out;
  }
'''
s = s[:start] + new + s[end:]

# 2) Replace old FC/FS summary helper with generic channel collector.
old = '''  // FC/FS are derived only from already returned Timeline RC_CHANNELS,\n  // so backend calculations and previous analysis results stay identical.\n  const timelineRows=Array.isArray(data.timeline)?data.timeline:[];\n  const collectChannel=(ch)=>{\n    const vals=timelineRows\n      .map(r=>rcPwmValue(r,ch))\n      .filter(v=>typeof v==='number'&&Number.isFinite(v));\n    if(!vals.length)return {last:null,min:null,max:null};\n    return {last:vals[vals.length-1],min:Math.min(...vals),max:Math.max(...vals)};\n  };\n  const fcUi=collectChannel(15);\n  const fsUi=collectChannel(11);\n  const uiSwitchSummary=(label,obj,stateFn)=>{\n    if(obj.last===null)return '—';\n    return `${stateFn(obj.last)} • ${Math.round(obj.last)} us<br><span style="font-size:11px;color:#64748b">діапазон: ${Math.round(obj.min)}–${Math.round(obj.max)} us</span>`;\n  };\n'''
new = '''  const timelineRows=Array.isArray(data.timeline)?data.timeline:[];\n  const collectChannel=(ch)=>{\n    const vals=timelineRows.map(r=>rcPwmValue(r,ch)).filter(v=>typeof v==='number'&&Number.isFinite(v));\n    if(!vals.length)return {last:null,min:null,max:null};\n    return {last:vals[vals.length-1],min:Math.min(...vals),max:Math.max(...vals)};\n  };\n  const uiSwitchSummary=(obj,stateFn)=>{\n    if(obj.last===null)return '—';\n    return `${stateFn(obj.last)} • ${Math.round(obj.last)} us<br><span style="font-size:11px;color:#64748b">діапазон: ${Math.round(obj.min)}–${Math.round(obj.max)} us</span>`;\n  };\n'''
if old not in s:
    raise SystemExit("old FC/FS helper block not found")
s = s.replace(old, new)

# 3) RC input cards.
start = s.index("  document.getElementById('rcInputsGrid').innerHTML=`")
end = s.index("\n\n  `;", start) + 5
cards = '''  document.getElementById('rcInputsGrid').innerHTML=`\n    ${createCard('CH1 Roll',data.radioChannels?.ch1||'—')}\n    ${createCard('CH2 Pitch',data.radioChannels?.ch2||'—')}\n    ${createCard('CH3 Throttle',data.radioChannels?.ch3||'—')}\n    ${createCard('CH4 Yaw',data.radioChannels?.ch4||'—')}\n    ${createCard('SA — CH7',uiSwitchSummary(collectChannel(7),p=>`5.${tx16ThreePos(p)===1?'2':tx16ThreePos(p)===2?'5':'8'} GHz`),'Вибір діапазону VTX: 5.2 / 5.5 / 5.8 GHz')}\n    ${createCard('SB — CH8',uiSwitchSummary(collectChannel(8),p=>`K${tx16ThreePos(p)||'—'}`),'Вибір відеоканалу K1 / K2 / K3')}\n    ${createCard('SC — CH15',uiSwitchSummary(collectChannel(15),tx16ThreePosHuman),'Запобіжник системи скиду; працює у зв’язці з SF')}\n    ${createCard('SF — CH10',uiSwitchSummary(collectChannel(10),p=>tx16TwoPosHuman(p,false)),'Активатор системи скиду; аналізується разом із SC')}\n    ${createCard('SD — CH13',uiSwitchSummary(collectChannel(13),tx16ThreePosHuman),'3-позиційний запобіжник EMERGENCY STOP; дозвіл лише ДО СЕБЕ')}\n    ${createCard('SH — CH6',uiSwitchSummary(collectChannel(6),p=>tx16TwoPosHuman(p,true)),'Активатор EMERGENCY STOP; враховується лише при SD=ДО СЕБЕ')}\n    ${createCard('LS — CH12',uiSwitchSummary(collectChannel(12),tx16ThreePosHuman),'Кут нахилу камери')}\n    ${createCard('RS — CH9',uiSwitchSummary(collectChannel(9),tx16ThreePosHuman),'Zoom камери: + / нейтраль / −')}\n    ${createCard(\n      'Радіокалібрування',\n      data.flight?.radioCalibration?.detected ? `ВИЯВЛЕНО • ${data.flight.radioCalibration.confidence??0}%` : 'Не виявлено',\n      data.flight?.radioCalibration?.detected ? `CH: ${(data.flight.radioCalibration.fullRangeChannels||[]).map(x=>'CH'+x).join(', ')||'—'} • переходів: ${data.flight.radioCalibration.transitionCount??0}` : 'Автоматична перевірка проходження CH1–CH4 через MIN/CENTER/MAX'\n    )}\n\n  `;'''
s = s[:start] + cards + s[end:]

# 4) Expanded switch panel.
start = s.index('function renderTx16Switches(item){')
end = s.index('\nfunction stickDotPosition', start)
panel = r'''function renderTx16Switches(item){
  const sa=rcPwmValue(item,7), sb=rcPwmValue(item,8);
  const sc=rcPwmValue(item,15), sf=rcPwmValue(item,10);
  const sd=rcPwmValue(item,13), sh=rcPwmValue(item,6);
  const ls=rcPwmValue(item,12), rs=rcPwmValue(item,9);
  const sfOn=tx16HighActive(sf), shOn=tx16HighActive(sh);
  const sdArmed=tx16ThreePos(sd)===3;
  const pwm=v=>v===null?'—':`${Math.round(v)} us`;
  const card=(name,ch,state,cls='')=>`<div class="switch-card"><div class="switch-name">${name}</div><div class="switch-channel">CH${ch} • ${pwm(rcPwmValue(item,ch))}</div><div class="switch-state ${cls}"><b>${state}</b></div></div>`;
  const band=tx16ThreePos(sa); const bandText=band===1?'5.2 GHz':band===2?'5.5 GHz':band===3?'5.8 GHz':'—';
  const sbPos=tx16ThreePos(sb); const sbText=sbPos?`K${sbPos}`:'—';
  return `<div class="switches-wrap">
    <div class="switches-title">🎚 TX16S — SA / SB / SC / SF / SD / SH / LS / RS</div>
    <div class="switches-grid">
      ${card('SA',7,bandText)}${card('SB',8,sbText)}
      ${card('SC',15,tx16ThreePosHuman(sc),tx16ThreePos(sc)===3?'switch-active':'switch-safe')}
      ${card('SF',10,sfOn===true?'АКТИВАТОР ON':sfOn===false?'OFF':'ПЕРЕХІДНА ЗОНА',sfOn===true?'switch-active':'')}
      ${card('SD',13,`${tx16ThreePosHuman(sd)}${sdArmed?' • E-STOP ARMED':''}`,sdArmed?'switch-stop':'switch-safe')}
      ${card('SH',6,shOn===true?'EMERGENCY ACTIVATOR':shOn===false?'НЕ НАТИСНУТО':'ПЕРЕХІДНА ЗОНА',shOn===true&&sdArmed?'switch-stop':'')}
      ${card('LS',12,tx16ThreePosHuman(ls))}${card('RS',9,tx16ThreePosHuman(rs))}
    </div></div>`;
}
'''
s = s[:start] + panel + s[end:]
s = s.replace('    <div class="sticks-note">FC=CH15 та FS=CH11 додані лише як відображення RC_CHANNELS. Старий аналіз, AI-висновки, дальність, VTX, LINK LOSS та інші розрахунки не змінюються.</div>', '    <div class="sticks-note">SA/SB керують VTX; SC+SF — система скиду; SD+SH — EMERGENCY STOP; LS/RS — камера. Аналіз лише читає RC_CHANNELS.</div>')

# 5) Remove obsolete FC/FS functions and use real control mapping in Timeline chips.
start = s.index('// TX16S UI-only extension.')
end = s.index('\nfunction renderTx16TimelineSummary', start)
state_block = r'''// Підтверджений/уточнений мапінг TX16S для цього борта.
function tx16StateRaw(item){
  return {
    sa:rcPwmValue(item,7), sb:rcPwmValue(item,8),
    sc:rcPwmValue(item,15), sf:rcPwmValue(item,10),
    sd:rcPwmValue(item,13), sh:rcPwmValue(item,6),
    ls:rcPwmValue(item,12), rs:rcPwmValue(item,9)
  };
}
function tx16NormalizedState(item){
  const r=tx16StateRaw(item);
  const saPos=tx16ThreePos(r.sa), sbPos=tx16ThreePos(r.sb);
  return {
    sa:saPos===1?'5.2 GHz':saPos===2?'5.5 GHz':saPos===3?'5.8 GHz':'—',
    sb:sbPos?`K${sbPos}`:'—',
    sc:tx16ThreePosHuman(r.sc), sf:tx16TwoPosHuman(r.sf,false),
    sd:tx16ThreePosHuman(r.sd), sh:tx16TwoPosHuman(r.sh,true),
    ls:tx16ThreePosHuman(r.ls), rs:tx16ThreePosHuman(r.rs), raw:r
  };
}
'''
s = s[:start] + state_block + s[end:]
old = "  const sfActive=cur.sf==='УВІМКНЕНО'?'active':'';\n  const shActive=cur.sh==='НАТИСНУТО'?'stop':'';\n  const fsActive=cur.fs==='АКТИВОВАНО'?'active':'';\n  return `<div class=\"tl-tx16s\">${chip('SC','sc')}${chip('SD','sd')}${chip('SF','sf',sfActive)}${chip('SH','sh',shActive)}${chip('FC','fc')}${chip('FS','fs',fsActive)}</div>`;"
new = "  const sfActive=cur.sf==='УВІМКНЕНО'?'active':'';\n  const shActive=(cur.sh==='НАТИСНУТО'&&cur.sd==='ДО СЕБЕ')?'stop':'';\n  return `<div class=\"tl-tx16s\">${chip('SA','sa')}${chip('SB','sb')}${chip('SC','sc')}${chip('SF','sf',sfActive)}${chip('SD','sd')}${chip('SH','sh',shActive)}${chip('LS','ls')}${chip('RS','rs')}</div>`;"
if old not in s:
    raise SystemExit("old Timeline chip block not found")
s = s.replace(old, new)
s = s.replace('TX16S — SC / SD / SF / SH / FC / FS', 'TX16S — SA / SB / SC / SF / SD / SH / LS / RS')
s = s.replace('TX16S — SC / SD / SF / SH', 'TX16S — SA / SB / SC / SF / SD / SH / LS / RS')

p.write_text(s, encoding="utf-8")
print("TX16 UI patch applied")
