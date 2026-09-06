from pathlib import Path

PATH = Path('index.html')
MARKER = '/* TIMELINE_ALWAYS_VISIBLE_SCROLLBAR_V1 */'
text = PATH.read_text(encoding='utf-8')
if MARKER in text:
    raise SystemExit(0)

css = r'''
/* TIMELINE_ALWAYS_VISIBLE_SCROLLBAR_V1 */
.timeline-scrollbar-fixed{position:fixed!important;bottom:0!important;z-index:12000!important;height:18px!important;overflow-x:auto!important;overflow-y:hidden!important;background:var(--bg-main)!important;border-top:1px solid var(--border-color)!important;display:none}
.timeline-scrollbar-inner{height:1px}
'''
text = text.replace('</style>', css + '\n</style>', 1)

js = r'''
<script>
function updateTimelineFloatingScrollbar(){
  const timeline=document.getElementById('timelineContainer');
  const fixedBar=document.getElementById('timelineScrollbarFixed');
  const fixedInner=document.getElementById('timelineScrollbarInner');
  if(!timeline||!fixedBar||!fixedInner)return;
  const rect=timeline.getBoundingClientRect();
  const needsScroll=timeline.scrollWidth>timeline.clientWidth;
  const visible=needsScroll&&rect.top<window.innerHeight&&rect.bottom>0;
  fixedInner.style.width=timeline.scrollWidth+'px';
  fixedBar.style.left=rect.left+'px';
  fixedBar.style.width=rect.width+'px';
  fixedBar.style.display=visible?'block':'none';
  if(visible)fixedBar.scrollLeft=timeline.scrollLeft;
}

function setupTimelineFixedScrollbar(){
  const timeline=document.getElementById('timelineContainer');
  const fixedBar=document.getElementById('timelineScrollbarFixed');
  const fixedInner=document.getElementById('timelineScrollbarInner');
  if(!timeline||!fixedBar||!fixedInner)return;
  fixedInner.style.width=timeline.scrollWidth+'px';
  if(!timeline.dataset.fixedScrollBound){
    timeline.addEventListener('scroll',()=>{
      if(timelineScrollbarSyncing)return;
      timelineScrollbarSyncing=true;
      fixedBar.scrollLeft=timeline.scrollLeft;
      timelineScrollbarSyncing=false;
    });
    timeline.dataset.fixedScrollBound='1';
  }
  if(!fixedBar.dataset.timelineScrollBound){
    fixedBar.addEventListener('scroll',()=>{
      if(timelineScrollbarSyncing)return;
      timelineScrollbarSyncing=true;
      timeline.scrollLeft=fixedBar.scrollLeft;
      timelineScrollbarSyncing=false;
    });
    fixedBar.dataset.timelineScrollBound='1';
  }
  updateTimelineFloatingScrollbar();
}
window.addEventListener('scroll',updateTimelineFloatingScrollbar,{passive:true});
window.addEventListener('resize',updateTimelineFloatingScrollbar);
</script>
'''
text = text.replace('</body>', js + '\n</body>', 1)
PATH.write_text(text, encoding='utf-8')
