from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')
marker = 'MOBILE_LAND_VSPEED_BUTTONS_V1'

if marker not in s:
    css = r'''
<style>
/* MOBILE_LAND_VSPEED_BUTTONS_V1 */
@media(max-width:767px){
  .tl-altitude-cell{flex-direction:column!important;align-items:flex-start!important;justify-content:center!important;gap:2px!important;overflow:hidden!important}
  .tl-altitude-cell .land-vspeed-inline{display:block!important;max-width:100%!important;font-size:9px!important;line-height:1.05!important;overflow:hidden!important;text-overflow:clip!important}
  #graphViewerBtn{right:12px!important;bottom:12px!important}
  #scrollTopBtn{right:12px!important;bottom:72px!important}
}
</style>
'''
    if '</head>' not in s:
        raise SystemExit('head anchor not found')
    s = s.replace('</head>', css + '\n</head>', 1)

p.write_text(s, encoding='utf-8')
print('Applied mobile LAND speed/button layout fix')
