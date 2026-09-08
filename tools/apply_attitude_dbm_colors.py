from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


def main():
    html = INDEX.read_text(encoding="utf-8")

    css_anchor = ".attitude-radio-card b{font-size:10px;color:#7dd3fc;letter-spacing:.07em}.attitude-radio-card span{font-size:15px;color:#f8fafc}"
    css_block = """.attitude-radio-card b{font-size:10px;color:#7dd3fc;letter-spacing:.07em}.attitude-radio-card span{font-size:15px;color:#f8fafc}\n#attitudeDbm.attitude-dbm-good{color:#22c55e!important;background:rgba(34,197,94,.14);border:1px solid rgba(34,197,94,.55);border-radius:5px;padding:3px 7px}\n#attitudeDbm.attitude-dbm-warning{color:#f59e0b!important;background:rgba(245,158,11,.14);border:1px solid rgba(245,158,11,.55);border-radius:5px;padding:3px 7px}\n#attitudeDbm.attitude-dbm-danger{color:#ef4444!important;background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.60);border-radius:5px;padding:3px 7px}\n"""
    if ".attitude-dbm-good" not in html:
        if css_anchor not in html:
            raise SystemExit("attitude radio CSS anchor not found")
        html = html.replace(css_anchor, css_block, 1)

    helper = """function attitudeDbmClass(dbm){\n  if(dbm===null||dbm===undefined)return '';\n  const v=Number(dbm);\n  if(!Number.isFinite(v))return '';\n  if(v>=-85)return 'attitude-dbm-good';\n  if(v>=-99)return 'attitude-dbm-warning';\n  return 'attitude-dbm-danger';\n}\n\n"""
    if "function attitudeDbmClass(dbm)" not in html:
        anchor = "function updateAttitudeAtTime(timeMs){"
        if anchor not in html:
            raise SystemExit("updateAttitudeAtTime anchor not found")
        html = html.replace(anchor, helper + anchor, 1)

    old = "  if(dbmEl)dbmEl.textContent=dbm===null?'—':`${Math.round(dbm)} dBm`;"
    new = """  if(dbmEl){\n    dbmEl.textContent=dbm===null?'—':`${Math.round(dbm)} dBm`;\n    dbmEl.classList.remove('attitude-dbm-good','attitude-dbm-warning','attitude-dbm-danger');\n    const dbmClass=attitudeDbmClass(dbm);\n    if(dbmClass)dbmEl.classList.add(dbmClass);\n  }"""
    if "dbmEl.classList.remove('attitude-dbm-good'" not in html:
        if old not in html:
            raise SystemExit("attitude dBm update anchor not found")
        html = html.replace(old, new, 1)

    INDEX.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
