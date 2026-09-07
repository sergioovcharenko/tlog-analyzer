from pathlib import Path


INDEX = Path("index.html")
MARKER = "UI_CLEANUP_V1"
OLD_ALTITUDE_CSS = ".tl-altitude-cell{display:flex;flex-direction:column;align-items:flex-start;justify-content:center;gap:2px;white-space:nowrap;min-width:0}"
NEW_ALTITUDE_CSS = ".tl-altitude-cell{display:flex!important;flex-direction:column!important;align-items:flex-start!important;justify-content:center!important;gap:2px!important;white-space:nowrap!important;min-width:0}"

STYLE = r'''
<style>
/* UI_CLEANUP_V1 — presentation only; telemetry values/calculations are untouched. */
.ai-list{
  display:grid!important;
  grid-template-columns:1fr;
  gap:6px!important;
  margin:0!important;
  padding:0!important;
  list-style:none!important;
}
.ai-list li.ai-alert-row{
  display:block;
  width:100%;
  margin:0!important;
  padding:8px 10px!important;
  min-height:36px;
  border:1px solid var(--border-color);
  border-left:3px solid transparent;
  border-radius:6px;
  background:#0f141c;
  line-height:1.35!important;
  overflow-wrap:anywhere;
}
.ai-list li.ai-alert-row.ai-clickable{margin-left:0!important}
.ai-list li.ai-alert-needs-attention{
  border-left-color:var(--warning)!important;
  background:rgba(245,158,11,.065)!important;
}
.ai-list li.ai-alert-row.alert-critical{
  border-left-color:var(--danger)!important;
  background:rgba(239,68,68,.075)!important;
}
.ai-list li.ai-alert-row.alert-attention{
  border-left-color:#f97316!important;
  background:rgba(249,115,22,.065)!important;
}
.ai-list li.ai-alert-row.alert-warning{
  border-left-color:#eab308!important;
  background:rgba(234,179,8,.055)!important;
}
.ai-list li.ai-alert-row.alert-info{
  border-left-color:#3b82f6!important;
  background:rgba(59,130,246,.035)!important;
}
.ai-list li.ai-alert-hidden-debug{display:none!important}

/* Stack descent speed directly below altitude instead of consuming horizontal space. */
.tl-altitude-cell{display:flex!important;flex-direction:column!important;align-items:flex-start!important;justify-content:center!important;gap:2px!important;white-space:nowrap!important;min-width:0}
.land-vspeed-inline{display:block!important;margin:0!important;font-size:10px!important;line-height:1.05!important;color:#7dd3fc!important;font-weight:800!important;white-space:nowrap}
</style>
'''

SCRIPT = r'''
<script>
(function(){
  'use strict';
  // UI_CLEANUP_V1
  const PERF_DIAGNOSTIC_PREFIXES=[
    '🚀 VFR_HUD raw:',
    '⚡ EFI_STATUS індекс:',
    '🔬 MAVLink профіль:',
    '⏱ Швидкість аналізу backend:'
  ];
  const ATTENTION_PATTERNS=[
    'критич', 'аномал', 'несправн', 'обірвав', 'втрат', 'потрібна перевірка',
    'потрібно перевір', 'увага', 'ризик', 'перегрів', 'асиметр', 'не зафіксовано',
    '-128 dbm', 'thrust loss', 'поза сектор'
  ];

  function tidyAiAlertRows(){
    const aiAlerts=document.getElementById('aiAlerts');
    if(!aiAlerts)return;
    aiAlerts.querySelectorAll(':scope > li').forEach(li=>{
      const text=String(li.textContent||'').replace(/\s+/g,' ').trim();
      li.classList.add('ai-alert-row');
      const isDebug=PERF_DIAGNOSTIC_PREFIXES.some(prefix=>text.startsWith(prefix));
      li.classList.toggle('ai-alert-hidden-debug',isDebug);
      if(isDebug)return;
      const lower=text.toLowerCase();
      const alreadyMarked=li.classList.contains('alert-critical')||
        li.classList.contains('alert-attention')||li.classList.contains('alert-warning');
      const needsAttention=alreadyMarked||ATTENTION_PATTERNS.some(pattern=>lower.includes(pattern));
      li.classList.toggle('ai-alert-needs-attention',needsAttention);
    });
  }

  function bindAiAlertCleanup(){
    const aiAlerts=document.getElementById('aiAlerts');
    if(!aiAlerts)return;
    tidyAiAlertRows();
    const observer=new MutationObserver(()=>tidyAiAlertRows());
    observer.observe(aiAlerts,{childList:true,subtree:true,characterData:true});
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',bindAiAlertCleanup,{once:true});
  }else{
    bindAiAlertCleanup();
  }
})();
</script>
'''


def main():
    text = INDEX.read_text(encoding="utf-8")
    if MARKER in text:
        if OLD_ALTITUDE_CSS in text:
            text = text.replace(OLD_ALTITUDE_CSS, NEW_ALTITUDE_CSS, 1)
            INDEX.write_text(text, encoding="utf-8")
            print("Updated UI cleanup LAND stack")
        else:
            print("UI cleanup already applied")
        return
    if "</head>" not in text or "</body>" not in text:
        raise SystemExit("index.html is missing </head> or </body>")
    text = text.replace("</head>", STYLE + "\n</head>", 1)
    text = text.replace("</body>", SCRIPT + "\n</body>", 1)
    INDEX.write_text(text, encoding="utf-8")
    print("Applied UI cleanup")


if __name__ == "__main__":
    main()
