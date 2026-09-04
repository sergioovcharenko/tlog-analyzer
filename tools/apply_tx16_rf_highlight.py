from pathlib import Path

path = Path("index.html")
html = path.read_text(encoding="utf-8")

# Timeline chips: SA/SB blue RF styling.
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

# Large TX16 detail cards: same blue RF styling as timeline chips.
large_css_marker = ".switch-card.rf-control{border-color:rgba(56,189,248,.82)!important;"
if large_css_marker not in html:
    anchor = ".switch-card{border:1px solid #263548;border-radius:7px;background:#0a1017;padding:9px 10px;min-width:0}"
    css = """
.switch-card.rf-control{border-color:rgba(56,189,248,.82)!important;background:rgba(14,116,144,.12)!important;box-shadow:inset 0 0 0 1px rgba(125,211,252,.10),0 0 12px rgba(56,189,248,.12)}
.switch-card.rf-control .switch-name{color:#bae6fd!important}
.switch-card.rf-control .switch-channel{color:#7dd3fc!important}
.switch-card.rf-control .switch-state,.switch-card.rf-control .switch-state b{color:#7dd3fc!important}
"""
    if anchor not in html:
        raise SystemExit("Large TX16 card CSS anchor not found")
    html = html.replace(anchor, anchor + css, 1)

old_card = "const card=(name,ch,state,cls='')=>`<div class=\"switch-card\"><div class=\"switch-name\">${name}</div><div class=\"switch-channel\">CH${ch} • ${pwm(rcPwmValue(item,ch))}</div><div class=\"switch-state ${cls}\"><b>${state}</b></div></div>`;"
new_card = "const card=(name,ch,state,cls='')=>{const rf=cls==='rf-control';const cardCls=rf?' rf-control':'';const stateCls=rf?'':cls;return `<div class=\"switch-card${cardCls}\"><div class=\"switch-name\">${name}</div><div class=\"switch-channel\">CH${ch} • ${pwm(rcPwmValue(item,ch))}</div><div class=\"switch-state ${stateCls}\"><b>${state}</b></div></div>`;};"
if old_card in html:
    html = html.replace(old_card, new_card, 1)
elif new_card not in html:
    raise SystemExit("Large TX16 card renderer anchor not found")

old_sb = "const sbPos=tx16ThreePos(sb); const sbText=sbPos?`K${sbPos}`:'—';"
new_sb = "const sbPos=tx16ThreePos(sb); const sbText=sbPos?`${tx16VtxFrequency(band,sbPos)} MHz`:'—';"
if old_sb in html:
    html = html.replace(old_sb, new_sb, 1)
elif new_sb not in html:
    raise SystemExit("Large TX16 SB text anchor not found")

old_calls = "${card('SA',7,bandText)}${card('SB',8,sbText)}"
new_calls = "${card('SA',7,bandText,'rf-control')}${card('SB',8,sbText,'rf-control')}"
if old_calls in html:
    html = html.replace(old_calls, new_calls, 1)
elif new_calls not in html:
    raise SystemExit("Large TX16 SA/SB card calls anchor not found")

path.write_text(html, encoding="utf-8")
print("Applied SA/SB blue RF highlight to timeline and detail cards; SB detail now shows MHz")
