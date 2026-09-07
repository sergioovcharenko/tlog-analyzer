from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')
marker = 'DESKTOP_FLOATING_BUTTONS_V1'

if marker not in s:
    css = r'''
<style>
/* DESKTOP_FLOATING_BUTTONS_V1 */
#graphViewerBtn{right:22px!important;bottom:22px!important}
#scrollTopBtn{right:22px!important;bottom:82px!important}
@media(max-width:767px){
  #graphViewerBtn{right:12px!important;bottom:12px!important}
  #scrollTopBtn{right:12px!important;bottom:72px!important}
}
</style>
'''
    if '</head>' not in s:
        raise SystemExit('head anchor not found')
    s = s.replace('</head>', css + '\n</head>', 1)

p.write_text(s, encoding='utf-8')
print('Applied desktop floating button separation')
