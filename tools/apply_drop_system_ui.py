from pathlib import Path

path = Path("index.html")
s = path.read_text(encoding="utf-8")


def replace_exact(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"missing expected block: {label}")
    s = s.replace(old, new)


def replace_section(start: str, end: str, new_block: str, label: str) -> None:
    global s
    a = s.find(start)
    if a < 0:
        raise SystemExit(f"missing section start: {label}")
    b = s.find(end, a)
    if b < 0:
        raise SystemExit(f"missing section end: {label}")
    s = s[:a] + new_block + s[b:]


# 1) Remove camera controls from the TX16S UI state. Raw RC channels remain in TLOG data.
replace_exact(
    "    sc:rcPwmValue(item,15), sf:rcPwmValue(item,10),\n"
    "    sd:rcPwmValue(item,13), sh:rcPwmValue(item,6),\n"
    "    ls:rcPwmValue(item,12), rs:rcPwmValue(item,9)\n",
    "    sc:rcPwmValue(item,15), sf:rcPwmValue(item,10),\n"
    "    sd:rcPwmValue(item,13), sh:rcPwmValue(item,6)\n",
    "TX16 raw state camera controls",
)

# 2) Add human safety-state mappings for dual and single drop selectors.
three_pos_block = """function tx16ThreePosHuman(pwm){
  const pos=tx16ThreePos(pwm);
  if(pos===1)return 'ВІД СЕБЕ';
  if(pos===2)return 'СЕРЕДИНА';
  if(pos===3)return 'ДО СЕБЕ';
  return '—';
}
"""
if "function tx16DualDropSafetyState" not in s:
    replace_exact(
        three_pos_block,
        three_pos_block + """
function tx16DualDropSafetyState(pwm){
  const pos=tx16ThreePos(pwm);
  if(pos===1)return 'ЗАПОБІЖНИК АКТИВОВАНИЙ';
  if(pos===2)return 'ЗНЯТО З ЗАПОБІЖНИКА (R)';
  if(pos===3)return 'ЗНЯТО З ЗАПОБІЖНИКА (L)';
  return '—';
}

function tx16SingleDropSafetyState(pwm){
  const pos=tx16ThreePos(pwm);
  if(pos===1||pos===2)return 'ЗАПОБІЖНИК АКТИВОВАНИЙ';
  if(pos===3)return 'ЗАПОБІЖНИК ЗНЯТО';
  return '—';
}
""",
        "drop safety helpers",
    )

# 3) Normalize TX16S states with functional names instead of physical positions.
replace_section(
    "function tx16NormalizedState(item){",
    "\n\nfunction renderTx16TimelineSummary(item,prevItem){",
    """function tx16NormalizedState(item){
  const r=tx16StateRaw(item);
  const saPos=tx16ThreePos(r.sa), sbPos=tx16ThreePos(r.sb);
  return {
    sa:saPos===1?'5.2 GHz':saPos===2?'5.5 GHz':saPos===3?'5.8 GHz':'—',
    sb:sbPos?`K${sbPos}`:'—',
    sc:tx16DualDropSafetyState(r.sc), sf:tx16TwoPosHuman(r.sf,false),
    sd:tx16SingleDropSafetyState(r.sd), sh:tx16TwoPosHuman(r.sh,true),
    raw:r
  };
}
""",
    "normalized TX16 state",
)

# 4) Compact Timeline chips: SC/SF red, SD/SH yellow; no LS/RS.
replace_section(
    "function renderTx16TimelineSummary(item,prevItem){",
    "\n\n// V23.31 / V24.11:",
    """function renderTx16TimelineSummary(item,prevItem){
  const cur=tx16NormalizedState(item);
  const prev=prevItem?tx16NormalizedState(prevItem):null;
  const any=Object.values(cur.raw).some(v=>typeof v==='number');
  if(!any)return '<span class=\"tx16-empty\">Немає RC-даних</span>';

  const changed=k=>Boolean(prev && prev[k]!=='—' && cur[k]!=='—' && prev[k]!==cur[k]);
  const chip=(label,key,extra='')=>{
    const isChanged=changed(key);
    const cls=`tx16-chip${isChanged?' changed':''}${extra?' '+extra:''}`;
    const title=isChanged?`${label}: ${prev[key]} → ${cur[key]}`:`${label}: ${cur[key]}`;
    const before=isChanged?`${prev[key]} → `:'';
    return `<span class=\"${cls}\" title=\"${title}\"><b>${label}:</b> ${before}${cur[key]}</span>`;
  };

  const sfActive=cur.sf==='УВІМКНЕНО'?' active':'';
  const shActive=(cur.sh==='НАТИСНУТО'&&cur.sd==='ЗАПОБІЖНИК ЗНЯТО')?' active':'';
  return `<div class=\"tl-tx16s\">${chip('SA','sa')}${chip('SB','sb')}${chip('SC','sc','drop-control')}${chip('SF','sf','drop-control'+sfActive)}${chip('SD','sd','single-drop-control')}${chip('SH','sh','single-drop-control'+shActive)}</div>`;
}
""",
    "compact TX16 Timeline summary",
)

# 5) Expanded TX16S panel with functional safety labels and no camera controls.
replace_section(
    "function renderTx16Switches(item){",
    "\n\nfunction stickDotPosition(horizontalPct,verticalPct){",
    """function renderTx16Switches(item){
  const sa=rcPwmValue(item,7), sb=rcPwmValue(item,8);
  const sc=rcPwmValue(item,15), sf=rcPwmValue(item,10);
  const sd=rcPwmValue(item,13), sh=rcPwmValue(item,6);
  const sfOn=tx16HighActive(sf), shOn=tx16HighActive(sh);
  const scPos=tx16ThreePos(sc), sdPos=tx16ThreePos(sd);
  const pwm=v=>v===null?'—':`${Math.round(v)} us`;
  const card=(name,ch,state,cls='')=>`<div class=\"switch-card\"><div class=\"switch-name\">${name}</div><div class=\"switch-channel\">CH${ch} • ${pwm(rcPwmValue(item,ch))}</div><div class=\"switch-state ${cls}\"><b>${state}</b></div></div>`;
  const band=tx16ThreePos(sa); const bandText=band===1?'5.2 GHz':band===2?'5.5 GHz':band===3?'5.8 GHz':'—';
  const sbPos=tx16ThreePos(sb); const sbText=sbPos?`K${sbPos}`:'—';
  return `<div class=\"switches-wrap\">
    <div class=\"switches-title\">🎚 TX16S — SA / SB / SC / SF / SD / SH</div>
    <div class=\"switches-grid\">
      ${card('SA',7,bandText)}${card('SB',8,sbText)}
      ${card('SC',15,tx16DualDropSafetyState(sc),scPos===1?'switch-safe':'switch-stop')}
      ${card('SF',10,sfOn===true?'АКТИВАТОР УВІМКНЕНО':sfOn===false?'НЕ АКТИВОВАНО':'ПЕРЕХІДНА ЗОНА',sfOn===true?'switch-stop':'switch-safe')}
      ${card('SD',13,tx16SingleDropSafetyState(sd),sdPos===3?'switch-active':'switch-safe')}
      ${card('SH',6,shOn===true?'АКТИВАТОР УВІМКНЕНО':shOn===false?'НЕ АКТИВОВАНО':'ПЕРЕХІДНА ЗОНА',shOn===true&&sdPos===3?'switch-active':'switch-safe')}
    </div></div>`;
}
""",
    "expanded TX16 panel",
)

# 6) RC cards use the same functional labels and omit LS/RS.
old_cards = """    ${createCard('SC — CH15',uiSwitchSummary(collectChannel(15),tx16ThreePosHuman),'Запобіжник системи скиду; працює у зв’язці з SF')}
    ${createCard('SF — CH10',uiSwitchSummary(collectChannel(10),p=>tx16TwoPosHuman(p,false)),'Активатор системи скиду; аналізується разом із SC')}
    ${createCard('SD — CH13',uiSwitchSummary(collectChannel(13),tx16ThreePosHuman),'3-позиційний запобіжник EMERGENCY STOP; дозвіл лише ДО СЕБЕ')}
    ${createCard('SH — CH6',uiSwitchSummary(collectChannel(6),p=>tx16TwoPosHuman(p,true)),'Активатор EMERGENCY STOP; враховується лише при SD=ДО СЕБЕ')}
    ${createCard('LS — CH12',uiSwitchSummary(collectChannel(12),tx16ThreePosHuman),'Кут нахилу камери')}
    ${createCard('RS — CH9',uiSwitchSummary(collectChannel(9),tx16ThreePosHuman),'Zoom камери: + / нейтраль / −')}
"""
new_cards = """    ${createCard('SC — CH15',uiSwitchSummary(collectChannel(15),tx16DualDropSafetyState),'Подвійний скид: ВІД СЕБЕ — запобіжник; СЕРЕДИНА — R; ДО СЕБЕ — L')}
    ${createCard('SF — CH10',uiSwitchSummary(collectChannel(10),p=>tx16TwoPosHuman(p,false)),'Активатор подвійного скиду; скид рахується лише коли SC вибрано R або L')}
    ${createCard('SD — CH13',uiSwitchSummary(collectChannel(13),tx16SingleDropSafetyState),'Одиночний скид: ВІД СЕБЕ/СЕРЕДИНА — запобіжник; ДО СЕБЕ — запобіжник знято')}
    ${createCard('SH — CH6',uiSwitchSummary(collectChannel(6),p=>tx16TwoPosHuman(p,true)),'Активатор одиночного скиду; скид рахується лише коли SD=ЗАПОБІЖНИК ЗНЯТО')}
"""
replace_exact(old_cards, new_cards, "RC switch cards")

# 7) Valid activations only: dual SC+SF and single SD+SH. Invalid presses are not AI events.
replace_section(
    "  function buildTx16ActivationAlerts(timeline){",
    "\n\n  const combinedAiAlerts=[",
    """  function buildTx16ActivationAlerts(timeline){
    const rows=Array.isArray(timeline)?timeline:[];
    const dualDropEvents=[];
    const singleDropEvents=[];
    let prevSf=null, prevSh=null;

    rows.forEach(row=>{
      if(!row)return;
      const sf=tx16HighActive(rcPwmValue(row,10));
      const sh=tx16HighActive(rcPwmValue(row,6));
      const scPos=tx16ThreePos(rcPwmValue(row,15));
      const sdPos=tx16ThreePos(rcPwmValue(row,13));

      if(sf!==null){
        if(prevSf===false && sf===true && (scPos===2||scPos===3)){
          const side=scPos===2?'R':'L';
          dualDropEvents.push({
            time:row.time||'',
            side,
            selector:tx16DualDropSafetyState(rcPwmValue(row,15)),
            pwm:rcPwmValue(row,10)
          });
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
    dualDropEvents.forEach((ev,i)=>{
      const n=dualDropEvents.length>1?` №${i+1}`:'';
      out.push(`<span class=\"ai-jump\" data-jump-time=\"${ev.time}\">🎚 <b>СКИД ${ev.side}${n} — SC + SF:</b> ${ev.time}; SC: ${ev.selector}; SF: АКТИВАТОР УВІМКНЕНО${typeof ev.pwm==='number'?` (${Math.round(ev.pwm)} us)`:''}. Натисніть, щоб перейти до Timeline.</span>`);
    });
    const sides=new Set(dualDropEvents.map(ev=>ev.side));
    if(sides.has('R')&&sides.has('L')){
      out.push('🎚 <b>ПОДВІЙНИЙ СКИД:</b> зафіксовано валідну активацію R та L.');
    }

    singleDropEvents.forEach((ev,i)=>{
      const n=singleDropEvents.length>1?` №${i+1}`:'';
      out.push(`<span class=\"ai-jump\" data-jump-time=\"${ev.time}\">🎚 <b>ОДИНОЧНИЙ СКИД${n} — SD + SH:</b> ${ev.time}; SD: ЗАПОБІЖНИК ЗНЯТО; SH: АКТИВАТОР УВІМКНЕНО${typeof ev.pwm==='number'?` (${Math.round(ev.pwm)} us)`:''}. Натисніть, щоб перейти до Timeline.</span>`);
    });
    return out;
  }
""",
    "drop activation AI alerts",
)

# 8) User-facing labels, notes and colors.
replace_exact(
    "TX16S — SA / SB / SC / SF / SD / SH / LS / RS",
    "TX16S — SA / SB / SC / SF / SD / SH",
    "TX16 title/header",
)
replace_exact(
    "SA/SB керують VTX; SC+SF — система скиду; SD+SH — EMERGENCY STOP; LS/RS — камера. Аналіз лише читає RC_CHANNELS.",
    "SA/SB керують VTX; SC+SF — подвійний скид; SD+SH — одиночний скид. Аналіз лише читає RC_CHANNELS.",
    "TX16 explanatory note",
)
replace_exact(
    "// SD=CH13 + SH=CH6 — EMERGENCY STOP; LS=CH12; RS=CH9.",
    "// SD=CH13 + SH=CH6 — одиночний скид. LS/RS у UI не показуються.",
    "TX16 mapping comment",
)
replace_exact(
    "  if(/EMERGENCY STOP/i.test(text)&&!/не зафіксовано/i.test(text))return 'attention';\n",
    "",
    "obsolete emergency alert classifier",
)

s = s.replace("emergency-control", "single-drop-control")
s = s.replace(
    "/* Functional groups: SC+SF = drop system (red), SD+SH = Emergency Stop (yellow). */",
    "/* Functional groups: SC+SF = dual drop (red), SD+SH = single drop (yellow). */",
)

# Defensive checks: old user-facing semantics must be gone.
for forbidden in ("EMERGENCY STOP", "SD=ДО СЕБЕ + SH", "LS — CH12", "RS — CH9", "chip('LS','ls')", "chip('RS','rs')"):
    if forbidden in s:
        raise SystemExit(f"obsolete UI text still present: {forbidden}")

path.write_text(s, encoding="utf-8")
print("TX16 dual/single drop UI patch applied")
