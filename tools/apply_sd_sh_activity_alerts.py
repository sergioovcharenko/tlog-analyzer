from pathlib import Path

INDEX = Path("index.html")
MARKER = "SD_SH_ACTIVITY_ALERTS_V1"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Missing anchor: {label}")
    return text.replace(old, new, 1)


def main():
    text = INDEX.read_text(encoding="utf-8")
    if MARKER in text:
        print("SD/SH activity alerts already applied")
        return

    text = replace_once(
        text,
        "    const scTransitions=[];\n    const sfActivations=[];\n    let prevSf=null, prevSh=null, prevScPos=null;",
        "    const scTransitions=[];\n    const sfActivations=[];\n    // SD_SH_ACTIVITY_ALERTS_V1 — report physical SD/SH activity separately\n    // from a confirmed EMERGENCY STOP command.\n    const sdTransitions=[];\n    const shActivations=[];\n    let prevSf=null, prevSh=null, prevScPos=null, prevSdPos=null;",
        "activation state arrays",
    )

    sc_block = """      if(scPos){
        if(prevScPos!==null&&scPos!==prevScPos){
          scTransitions.push({time:row.time||'',from:prevScPos,to:scPos});
        }
        prevScPos=scPos;
      }
"""
    sd_block = sc_block + """
      if(sdPos){
        if(prevSdPos!==null&&sdPos!==prevSdPos){
          sdTransitions.push({time:row.time||'',from:prevSdPos,to:sdPos});
        }
        prevSdPos=sdPos;
      }
"""
    text = replace_once(text, sc_block, sd_block, "SC transition block")

    sh_anchor = """      if(sh!==null){
        if(prevSh===false && sh===true && sdPos===3){
"""
    sh_replacement = """      if(sh!==null){
        if(prevSh===false && sh===true){
          shActivations.push({time:row.time||'',sdPos,pwm:rcPwmValue(row,6)});
        }
        if(prevSh===false && sh===true && sdPos===3){
"""
    text = replace_once(text, sh_anchor, sh_replacement, "SH activation block")

    sf_summary = """    if(sfActivations.length){
      const first=sfActivations[0];
      out.push(`<span class=\"ai-jump\" data-jump-time=\"${first.time}\">🎚 <b>SF: зафіксовано ${sfActivations.length} активацій.</b>${first.time?` Перша — ${first.time}.`:''} Натисніть, щоб перейти до першої активації.</span>`);
    }
"""
    sd_sh_summary = sf_summary + """
    if(sdTransitions.length){
      const first=sdTransitions[0];
      out.push(`<span class=\"ai-jump\" data-jump-time=\"${first.time}\">🎚 <b>SD: зафіксовано ${sdTransitions.length} перемикань.</b>${first.time?` Перше — ${first.time}.`:''} Натисніть, щоб перейти до першого перемикання.</span>`);
    }
    if(shActivations.length){
      const first=shActivations[0];
      out.push(`<span class=\"ai-jump\" data-jump-time=\"${first.time}\">🎚 <b>SH: зафіксовано ${shActivations.length} натискань.</b>${first.time?` Перше — ${first.time}.`:''} Натисніть, щоб перейти до першого натискання.</span>`);
    }
    if(sdTransitions.length&&shActivations.length&&!emergencyStopEvents.length){
      const firstActivity=[...sdTransitions,...shActivations]
        .filter(ev=>ev&&ev.time)
        .sort((a,b)=>(timelineSeconds(a.time)??Infinity)-(timelineSeconds(b.time)??Infinity))[0];
      const jump=firstActivity?.time||'';
      out.push(`<span class=\"ai-jump\"${jump?` data-jump-time=\"${jump}\"`:''}>🟡 <b>SD/SH активувались, але одночасну команду EMERGENCY STOP не підтверджено.</b> SD та SH фіксуються окремо; EMERGENCY STOP зараховується лише коли SH натиснуто при SD=ЗАПОБІЖНИК ЗНЯТО.</span>`);
    }
"""
    text = replace_once(text, sf_summary, sd_sh_summary, "SF summary block")

    text = replace_once(
        text,
        "// SD=CH13 + SH=CH6 — одиночний скид. LS/RS у UI не показуються.",
        "// SD=CH13 + SH=CH6 — EMERGENCY STOP. LS/RS у UI не показуються.",
        "renderResults TX16 comment",
    )
    text = replace_once(
        text,
        "SA/SB керують VTX; SC+SF — подвійний скид; SD+SH — одиночний скид. Аналіз лише читає RC_CHANNELS.",
        "SA/SB керують VTX; SC+SF — система скиду; SD+SH — EMERGENCY STOP. Аналіз лише читає RC_CHANNELS.",
        "TX16 sticks note",
    )

    INDEX.write_text(text, encoding="utf-8")
    print("Applied SD/SH activity alerts")


if __name__ == "__main__":
    main()
