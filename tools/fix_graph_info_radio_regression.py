from pathlib import Path

INDEX = Path('index.html')
ATTITUDE_PATCHER = Path('tools/apply_attitude_dashboard_v22.py')

old = """  if(rssiEl)rssiEl.textContent=rssi===null?'—':`${Math.round(rssi)} %`;\n  if(dbmEl)dbmEl.textContent=dbm===null?'—':`${Math.round(dbm)} dBm`;\n  if(modeEl)modeEl.textContent=modeAtTime();\n"""
new = """  const setRadioTone=(el,tone)=>{\n    const card=el?.closest('.attitude-radio-card');if(!card)return;\n    card.classList.remove('summary-success','summary-warning','summary-danger');\n    if(tone)card.classList.add(tone);\n  };\n  if(rssiEl){rssiEl.textContent=rssi===null?'—':`${Math.round(rssi)} %`;setRadioTone(rssiEl,rssi===null?'':(rssi>=75?'summary-success':(rssi>=40?'summary-warning':'summary-danger')));}\n  if(dbmEl){dbmEl.textContent=dbm===null?'—':`${Math.round(dbm)} dBm`;setRadioTone(dbmEl,dbm===null?'':(dbm>=-70?'summary-success':(dbm>=-85?'summary-warning':'summary-danger')));}\n  if(modeEl)modeEl.textContent=modeAtTime();\n"""

for path in (INDEX, ATTITUDE_PATCHER):
    text = path.read_text(encoding='utf-8')
    if "const setRadioTone=(el,tone)=>" in text:
        print(f'{path}: already preserves radio tones')
        continue
    if old not in text:
        raise SystemExit(f'{path}: RSSI/dBm updater anchor not found')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'{path}: restored RSSI/dBm color thresholds')
