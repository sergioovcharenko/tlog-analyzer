from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')
marker = 'LAND_VSPEED_ALTITUDE_CELL_V1'

if marker not in s:
    css = r'''
<style>
/* LAND_VSPEED_ALTITUDE_CELL_V1 */
.tl-altitude-cell{
  display:flex!important;
  align-items:center!important;
  justify-content:space-between!important;
  gap:6px!important;
  white-space:nowrap!important;
}
.land-vspeed-inline{
  color:#93c5fd!important;
  font-size:10px!important;
  font-weight:800!important;
  white-space:nowrap!important;
}
</style>
'''
    if '</head>' not in s:
        raise SystemExit('head anchor not found')
    s = s.replace('</head>', css + '\n</head>', 1)

anchor = """    const current=typeof item.curr==='number'\n      ?formatCurrentColored(item.curr)\n      :'—';\n\n"""
addition = """    const current=typeof item.curr==='number'\n      ?formatCurrentColored(item.curr)\n      :'—';\n\n    const landVerticalSpeed=typeof item.verticalSpeedDown==='number'&&item.mode==='LAND'\n      ?`<span class=\"land-vspeed-inline\">↓ ${Math.abs(item.verticalSpeedDown).toFixed(2)} м/с</span>`\n      :'';\n\n"""
if 'const landVerticalSpeed=' not in s:
    if anchor not in s:
        raise SystemExit('current anchor not found')
    s = s.replace(anchor, addition, 1)

old_alt = '<div class="tl-badge">${item.alt||\'—\'}</div>'
new_alt = '<div class="tl-badge tl-altitude-cell">${item.alt||\'—\'}${landVerticalSpeed}</div>'
if new_alt not in s:
    if old_alt not in s:
        raise SystemExit('altitude cell anchor not found')
    s = s.replace(old_alt, new_alt, 1)

old_system = "          ${typeof item.verticalSpeedDown==='number'&&item.mode==='LAND'?`<div class=\"esc-no-data\">Vz↓: ${item.verticalSpeedDown.toFixed(2)} м/с</div>`:''}\n"
s = s.replace(old_system, '', 1)

p.write_text(s, encoding='utf-8')
print('Applied LAND vertical speed beside altitude')
