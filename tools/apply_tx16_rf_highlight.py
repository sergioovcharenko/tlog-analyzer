from pathlib import Path

path = Path("index.html")
html = path.read_text(encoding="utf-8")

css_marker = ".tx16-chip.rf-control{color:#7dd3fc!important;"
if css_marker not in html:
    anchor = "/* Functional groups: SC+SF = drop system (red), SD+SH = EMERGENCY STOP (yellow). */"
    css = """/* RF controls: SA+SB = video band/channel (blue). */
.tx16-chip.rf-control{color:#7dd3fc!important;border-color:rgba(56,189,248,.82)!important;background:rgba(14,116,144,.12)!important;font-weight:800;box-shadow:inset 0 0 0 1px rgba(125,211,252,.10),0 0 10px rgba(56,189,248,.10)}
.tx16-chip.rf-control b{color:#bae6fd!important}
"""
    if anchor not in html:
        raise SystemExit("TX16 functional-group CSS anchor not found")
    html = html.replace(anchor, css + anchor, 1)

old = "${chip('SA','sa')}${chip('SB','sb')}${chip('SC','sc','drop-control')}"
new = "${chip('SA','sa','rf-control')}${chip('SB','sb','rf-control')}${chip('SC','sc','drop-control')}"
if old in html:
    html = html.replace(old, new, 1)
elif new not in html:
    raise SystemExit("TX16 SA/SB chip render anchor not found")

path.write_text(html, encoding="utf-8")
print("Applied SA/SB blue RF highlight")
