from pathlib import Path

HTML = Path("index.html")
text = HTML.read_text(encoding="utf-8")

CSS_MARKER = ".board-message[data-board-time]{cursor:pointer"
if CSS_MARKER not in text:
    anchor = ".board-message-current{outline:2px solid #38bdf8;outline-offset:-1px;box-shadow:0 0 0 3px rgba(56,189,248,.10)}"
    addition = anchor + "\n.board-message[data-board-time]{cursor:pointer;transition:background .12s ease,transform .12s ease}\n.board-message[data-board-time]:hover{filter:brightness(1.14);transform:translateX(1px)}"
    if anchor not in text:
        raise SystemExit("board message CSS anchor not found")
    text = text.replace(anchor, addition, 1)

if "function boardMessageLevelFromText" not in text:
    anchor = "function dashboardBoardEvents(){\n"
    helper = """function boardMessageLevelFromText(text,fallback='info'){
  const lower=String(text||'').toLowerCase();
  if(/crash:|potential thrust loss|thrust loss/.test(lower))return 'error';
  if(/ekf variance|stopped aiding|need position estimate|requires position|smartrtl deactivated|smartrtl failed|bad position|buffer full|prearm:/.test(lower))return 'warning';
  return fallback;
}
function dashboardBoardEvents(){
"""
    if anchor not in text:
        raise SystemExit("dashboardBoardEvents anchor not found")
    text = text.replace(anchor, helper, 1)

old_raw = "events.push({time_ms:t,text,level:['error','warning','info','recovery'].includes(m.level)?m.level:'info',kind:'statustext'});"
new_raw = "const rawLevel=['error','warning','info','recovery'].includes(m.level)?m.level:'info';\n    events.push({time_ms:t,text,level:boardMessageLevelFromText(text,rawLevel),kind:'statustext'});"
if old_raw in text:
    text = text.replace(old_raw, new_raw, 1)
elif new_raw not in text:
    raise SystemExit("raw board message classification anchor not found")

old_fallback = "const level=row?.isError===true||/(FAIL|LOSS|ERROR|CRASH|THRUST)/.test(eventType)?'error':(/WARN/.test(eventType)?'warning':'info');\n      events.push({time_ms:t,text:systemText,level,kind:'statustext'});"
new_fallback = "const baseLevel=row?.isError===true||/(FAIL|LOSS|ERROR|CRASH|THRUST)/.test(eventType)?'error':(/WARN/.test(eventType)?'warning':'info');\n      const level=boardMessageLevelFromText(systemText,baseLevel);\n      events.push({time_ms:t,text:systemText,level,kind:'statustext'});"
if old_fallback in text:
    text = text.replace(old_fallback, new_fallback, 1)
elif new_fallback not in text:
    raise SystemExit("timeline board message classification anchor not found")

old_render = """function renderBoardMessagesAtTime(timeMs){
  const root=document.getElementById('boardMessagesList');if(!root)return;
  const rows=dashboardBoardEvents();
  if(!rows.length){root.innerHTML='<div class=\"board-message-empty\">Немає повідомлень борта або перемикань режиму</div>';return;}
  root.innerHTML=rows.map(m=>{const current=Number.isFinite(Number(timeMs))&&Math.abs(Number(m.time_ms)-Number(timeMs))<=BOARD_MESSAGE_WINDOW_MS?' board-message-current':'';const modeClass=m.kind==='mode'?' board-message-mode':'';return `<div class=\"board-message board-message-${m.level}${modeClass}${current}\"><span class=\"board-message-time\">${formatGraphTime(Number(m.time_ms))}</span>${dynamicEscapeHtml(m.text)}</div>`;}).join('');
  const current=root.querySelector('.board-message-current');if(current)current.scrollIntoView({block:'nearest'});
}
"""
new_render = """function renderBoardMessagesAtTime(timeMs){
  const root=document.getElementById('boardMessagesList');if(!root)return;
  const rows=dashboardBoardEvents();
  if(!rows.length){root.innerHTML='<div class=\"board-message-empty\">Немає повідомлень борта або перемикань режиму</div>';return;}
  root.innerHTML=rows.map(m=>{const current=Number.isFinite(Number(timeMs))&&Math.abs(Number(m.time_ms)-Number(timeMs))<=BOARD_MESSAGE_WINDOW_MS?' board-message-current':'';const modeClass=m.kind==='mode'?' board-message-mode':'';return `<div class=\"board-message board-message-${m.level}${modeClass}${current}\" data-board-time=\"${Number(m.time_ms)}\" title=\"Перейти до цього моменту на графіку\"><span class=\"board-message-time\">${formatGraphTime(Number(m.time_ms))}</span>${dynamicEscapeHtml(m.text)}</div>`;}).join('');
  root.querySelectorAll('[data-board-time]').forEach(el=>{
    el.addEventListener('click',()=>{
      graphViewerState.pinned=true;
      selectGraphTime(Number(el.dataset.boardTime));
    });
  });
  const current=root.querySelector('.board-message-current');if(current)current.scrollIntoView({block:'nearest'});
}
"""
if old_render in text:
    text = text.replace(old_render, new_render, 1)
elif new_render not in text:
    raise SystemExit("board message render anchor not found")

HTML.write_text(text, encoding="utf-8")
