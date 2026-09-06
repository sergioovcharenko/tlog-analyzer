from pathlib import Path
import re

p = Path('index.html')
s = p.read_text(encoding='utf-8')
marker = 'BOARD_MESSAGES_COMPLETE_LIST_V1'

board_pattern = re.compile(
    r"function dashboardBoardEvents\(\)\{.*?\n\}\nfunction renderBoardMessagesAtTime",
    re.S,
)

replacement = r'''function dashboardBoardEvents(){
  const result=graphViewerState.result||{};
  const events=[];
  const raw=Array.isArray(result.board_messages)?result.board_messages:[];
  raw.forEach(m=>{
    const t=Number(m?.time_ms),text=String(m?.text||'').trim();
    if(!Number.isFinite(t)||!text)return;
    events.push({time_ms:t,text,level:['error','warning','info','recovery'].includes(m.level)?m.level:'info',kind:'statustext'});
  });

  // Keep raw board/system text that is present in Timeline as a fallback,
  // and expose ARM/DISARM state changes that are not necessarily STATUSTEXT.
  const timeline=Array.isArray(result.timeline)?result.timeline:[];
  timeline.forEach(row=>{
    const sec=typeof timelineSeconds==='function'?timelineSeconds(row?.time):null;
    if(sec===null)return;
    const t=sec*1000;
    const eventType=String(row?.eventType||'').trim().toUpperCase();
    const systemText=String(row?.systemText||'').trim();
    if(systemText){
      const level=row?.isError===true||/(FAIL|LOSS|ERROR|CRASH|THRUST)/.test(eventType)?'error':(/WARN/.test(eventType)?'warning':'info');
      events.push({time_ms:t,text:systemText,level,kind:'statustext'});
    }
    if(['ARM','DISARM'].includes(eventType)){
      const text=eventType==='ARM'?'ARM — двигуни активовано':'DISARM — двигуни вимкнено';
      events.push({time_ms:t,text,level:eventType==='DISARM'?'recovery':'info',kind:'state'});
    }
  });

  const d=result.graph_data||{},tt=Array.isArray(d.mode_time_ms)?d.mode_time_ms:[],vv=Array.isArray(d.flight_mode)?d.flight_mode:[];
  let previous=null;
  for(let i=0;i<Math.min(tt.length,vv.length);i++){
    const mode=String(vv[i]||'').trim(),t=Number(tt[i]);
    if(!mode||!Number.isFinite(t))continue;
    if(previous===null){
      events.push({time_ms:t,text:`Початковий режим: ${mode}`,level:'info',kind:'mode'});
    }else if(mode!==previous){
      events.push({time_ms:t,text:`Режим змінено на ${mode}`,level:'info',kind:'mode'});
    }
    previous=mode;
  }

  const seen=new Set();
  return events.sort((a,b)=>a.time_ms-b.time_ms).filter(e=>{
    const key=Math.round(e.time_ms/100)+'|'+e.text;
    if(seen.has(key))return false;
    seen.add(key);
    return true;
  });
}
function renderBoardMessagesAtTime'''

s, n = board_pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'dashboardBoardEvents anchor not found: {n}')

old_sync = "renderGraphDockTx16(timeMs);renderGraphDockData(timeMs);renderSelectedSeriesChips();"
new_sync = "renderGraphDockTx16(timeMs);renderGraphDockData(timeMs);renderBoardMessagesAtTime(timeMs);renderSelectedSeriesChips();"
if new_sync not in s:
    if old_sync not in s:
        raise SystemExit('dashboard sync anchor not found')
    s = s.replace(old_sync, new_sync, 1)

if marker not in s:
    css = r'''
<style>
/* BOARD_MESSAGES_COMPLETE_LIST_V1 */
#attitudePanel .attitude-board-messages #boardMessagesList{
  min-height:180px!important;
  max-height:280px!important;
  overflow-y:auto!important;
  overflow-x:hidden!important;
}
</style>
'''
    if '</head>' not in s:
        raise SystemExit('head anchor not found')
    s = s.replace('</head>', css + '\n</head>', 1)

p.write_text(s, encoding='utf-8')
print('Applied complete board message/event list')
