from pathlib import Path

BACKEND = Path('backend/main.py')
HTML = Path('index.html')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f'anchor not found: {label}')
    return text.replace(old, new, 1)


backend = BACKEND.read_text(encoding='utf-8')
backend = replace_once(
    backend,
    '        min_dbm = 0\n        telem_rssi_raw = None\n',
    '        min_dbm = 0\n        # RADIO_DBM_SUMMARY_V1 — average every valid RADIO/RADIO_STATUS dBm sample.\n        # -128 dBm is intentionally INCLUDED in the arithmetic mean.\n        dbm_sum = 0.0\n        dbm_sample_count = 0\n        telem_rssi_raw = None\n',
    'radio accumulator init',
)
backend = replace_once(
    backend,
    '                curr_dbm = dbm_val\n\n                if dbm_val != 0 and (min_dbm == 0 or dbm_val < min_dbm):\n',
    '                curr_dbm = dbm_val\n\n                if dbm_val != 0:\n                    dbm_sum += float(dbm_val)\n                    dbm_sample_count += 1\n\n                if dbm_val != 0 and (min_dbm == 0 or dbm_val < min_dbm):\n',
    'radio accumulator update',
)
backend = replace_once(
    backend,
    '                "maxThrottle": f"{round(max_throttle)}%",\n',
    '                "avgDbm": (\n                    round(dbm_sum / dbm_sample_count, 1)\n                    if dbm_sample_count > 0\n                    else None\n                ),\n                "worstDbm": (round(min_dbm) if min_dbm != 0 else None),\n                "dbmSampleCount": dbm_sample_count,\n                "maxThrottle": f"{round(max_throttle)}%",\n',
    'radio response fields',
)
BACKEND.write_text(backend, encoding='utf-8')

html = HTML.read_text(encoding='utf-8')
html = replace_once(
    html,
    "    ${createCard('RC RSSI',data.radio?.rssi||'—')}\n    ${createCard('RADIO STATUS',data.radio?.telemRssi||'—')}\n",
    "    ${createCard('MIN RSSI',data.radio?.rssi||'—','Найнижчий RC RSSI за весь TLOG')}\n    ${createCard(\n      'RADIO dBm',\n      typeof data.radio?.worstDbm==='number'\n        ?`MAX ${data.radio.worstDbm} dBm`\n        :'—',\n      typeof data.radio?.avgDbm==='number'\n        ?`Середнє: ${data.radio.avgDbm.toFixed(1)} dBm (включно з -128)`\n        :'Середнє значення недоступне'\n    )}\n",
    'health radio cards',
)
for old in (
    "    ${createCard('Діапазон CH7',video.band?video.band+' GHz':'—')}\n",
    "    ${createCard('Канал CH8',video.channel||'—')}\n",
    "    ${createCard('CH7 PWM',video.ch7Pwm?video.ch7Pwm+' us':'—')}\n",
    "    ${createCard('CH8 PWM',video.ch8Pwm?video.ch8Pwm+' us':'—')}\n",
):
    html = html.replace(old, '')
HTML.write_text(html, encoding='utf-8')
