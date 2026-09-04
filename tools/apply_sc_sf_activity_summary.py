from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

start = s.find('  function buildTx16ActivationAlerts(timeline){')
if start < 0:
    raise SystemExit('buildTx16ActivationAlerts start not found')
end_anchor = '\n\n\n  const disarmedMovement=detectDisarmedPhysicalMovement(data);'
end = s.find(end_anchor, start)
if end < 0:
    raise SystemExit('buildTx16ActivationAlerts end anchor not found')

new_func = r'''  function buildTx16ActivationAlerts(timeline){
    const rows=Array.isArray(timeline)?timeline:[];
    const dualDropEvents=[];
    const singleDropEvents=[];
    const scTransitions=[];
    const sfActivations=[];
    let prevScPos=null, prevSf=null, prevSh=null;

    rows.forEach(row=>{
      if(!row)return;
      const sf=tx16HighActive(rcPwmValue(row,10));
      const sh=tx16HighActive(rcPwmValue(row,6));
      const scPos=tx16ThreePos(rcPwmValue(row,15));
      const sdPos=tx16ThreePos(rcPwmValue(row,13));

      if(scPos){
        if(prevScPos!==null && scPos!==prevScPos){
          scTransitions.push({
            time:row.time||'',
            from:prevScPos,
            to:scPos,
            state:tx16DualDropSafetyState(rcPwmValue(row,15))
          });
        }
        prevScPos=scPos;
      }

      if(sf!==null){
        if(prevSf===false && sf===true){
          sfActivations.push({time:row.time||'',scPos,pwm:rcPwmValue(row,10)});
          if(scPos===2||scPos===3){
            const side=scPos===2?'R':'L';
            dualDropEvents.push({
              time:row.time||'',
              side,
              selector:tx16DualDropSafetyState(rcPwmValue(row,15)),
              pwm:rcPwmValue(row,10)
            });
          }
        }
        prevSf=sf;
      }

      if(sh!==null){
        if(prevSh===false && sh===true && sdPos===3){
          singleDropEvents.push({time:row.time||'',pwm:rcPwmValue(row,6)});
        }
        prevSh=sh;
      }
    });

    const out=[];
    if(scTransitions.length){
      const first=scTransitions[0];
      const jump=first.time?` class="ai-jump" data-jump-time="${first.time}"`:'';
      out.push(`<span${jump}>🎚 <b>SC: зафіксовано ${scTransitions.length} перемикань.</b>${first.time?` Перше — ${first.time}. Натисніть, щоб перейти до Timeline.`:''}</span>`);
    }
    if(sfActivations.length){
      const first=sfActivations[0];
      const jump=first.time?` class="ai-jump" data-jump-time="${first.time}"`:'';
      out.push(`<span${jump}>🎚 <b>SF: зафіксовано ${sfActivations.length} активацій.</b>${first.time?` Перша — ${first.time}. Натисніть, щоб перейти до Timeline.`:''}</span>`);
    }
    if((scTransitions.length||sfActivations.length) && dualDropEvents.length===0){
      out.push('🟡 <b>СИСТЕМА ПОДВІЙНОГО СКИДУ:</b> зафіксовано перемикання SC/SF, але валідний скид не підтверджено.');
    }

    dualDropEvents.forEach((ev,i)=>{
      const n=dualDropEvents.length>1?` №${i+1}`:'';
      out.push(`<span class="ai-jump" data-jump-time="${ev.time}">🎚 <b>СКИД ${ev.side}${n} — SC + SF:</b> ${ev.time}; SC: ${ev.selector}; SF: АКТИВАТОР УВІМКНЕНО${typeof ev.pwm==='number'?` (${Math.round(ev.pwm)} us)`:''}. Натисніть, щоб перейти до Timeline.</span>`);
    });
    const sides=new Set(dualDropEvents.map(ev=>ev.side));
    if(sides.has('R')&&sides.has('L')){
      out.push('🎚 <b>ПОДВІЙНИЙ СКИД:</b> зафіксовано валідну активацію R та L.');
    }

    singleDropEvents.forEach((ev,i)=>{
      const n=singleDropEvents.length>1?` №${i+1}`:'';
      out.push(`<span class="ai-jump" data-jump-time="${ev.time}">🎚 <b>ОДИНОЧНИЙ СКИД${n} — SD + SH:</b> ${ev.time}; SD: ЗАПОБІЖНИК ЗНЯТО; SH: АКТИВАТОР УВІМКНЕНО${typeof ev.pwm==='number'?` (${Math.round(ev.pwm)} us)`:''}. Натисніть, щоб перейти до Timeline.</span>`);
    });
    return out;
  }'''

s = s[:start] + new_func + s[end:]
p.write_text(s, encoding='utf-8')
print('SC/SF activity summary patched')
