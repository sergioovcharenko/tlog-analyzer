from pathlib import Path


INDEX = Path("index.html")
STYLE_MARKER = "/* VIDEO_TLOG_SYNC_V1 */"
HTML_MARKER = "<!-- VIDEO_TLOG_SYNC_V1 -->"
JS_MARKER = "// VIDEO_TLOG_SYNC_V1"

STYLE = r'''
<style>
/* VIDEO_TLOG_SYNC_V1 */
.video-sync-panel{margin-top:12px;padding:12px;border:1px solid #334155;border-radius:8px;background:#0b1118}
.video-sync-actions{display:flex;gap:8px;flex-wrap:wrap}
.video-sync-actions button{min-height:36px;padding:7px 11px;border:1px solid #3b82f6;border-radius:6px;background:rgba(59,130,246,.09);color:#bfdbfe;font-weight:800;cursor:pointer}
#tlogSelectAnchor.is-waiting{border-color:#f59e0b;color:#fde68a;background:rgba(245,158,11,.10)}
#videoSyncPair{margin-top:9px;font:700 12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:#94a3b8}
#videoSyncPair.is-ready{color:#86efac}
.tl-item.video-sync-candidate{outline:1px solid rgba(245,158,11,.55);outline-offset:-1px}
</style>
'''.strip()

HTML = r'''
      <!-- VIDEO_TLOG_SYNC_V1 -->
      <div class="video-sync-panel" id="videoSyncPanel">
        <div class="video-sync-actions">
          <button id="videoSetAnchor" type="button">⏱ Взяти поточний час відео</button>
          <button id="tlogSelectAnchor" type="button">🎯 Вибрати момент TLOG</button>
        </div>
        <div id="videoSyncPair">відео — ↔ TLOG —</div>
      </div>
'''.rstrip()

JS = r'''
// VIDEO_TLOG_SYNC_V1
let awaitingTlogAnchor=false;
const VideoSyncUI={
  videoAnchor:document.getElementById('videoSetAnchor'),
  tlogAnchor:document.getElementById('tlogSelectAnchor'),
  pair:document.getElementById('videoSyncPair')
};

function formatVideoSyncTime(seconds){
  const value=Number(seconds);
  if(!Number.isFinite(value))return '—';
  const sign=value<0?'-':'';
  const abs=Math.abs(value);
  const minutes=Math.floor(abs/60);
  const secs=abs-minutes*60;
  return `${sign}${String(minutes).padStart(2,'0')}:${secs.toFixed(3).padStart(6,'0')}`;
}

function updateVideoSyncPair(){
  if(!VideoSyncUI.pair)return;
  VideoSyncUI.pair.textContent=`відео ${formatVideoSyncTime(videoAnchorSec)} ↔ TLOG ${formatVideoSyncTime(tlogAnchorSec)}`;
  const ready=canRunVideoAssistedAnalysis();
  VideoSyncUI.pair.classList.toggle('is-ready',ready);
  if(ready){
    if(VideoUI.status)VideoUI.status.textContent='Синхронізація готова. Натисни «ПОВТОРИТИ АНАЛІЗ» для відео + TLOG.';
    if(!UI.btn.disabled){UI.btn.textContent='🚀 АНАЛІЗ ВІДЕО + TLOG';UI.btn.className='analyze active';}
  }
}

function setAwaitingTlogAnchor(enabled){
  awaitingTlogAnchor=!!enabled;
  VideoSyncUI.tlogAnchor?.classList.toggle('is-waiting',awaitingTlogAnchor);
  document.querySelectorAll('#timelineContainer .tl-item[data-time]').forEach(row=>row.classList.toggle('video-sync-candidate',awaitingTlogAnchor));
}

VideoSyncUI.videoAnchor?.addEventListener('click',()=>{
  if(!videoFile||!VideoUI.preview?.src){
    UI.error.textContent='❌ Спочатку обери відео';
    UI.error.style.display='block';
    return;
  }
  videoAnchorSec=Number(VideoUI.preview.currentTime||0);
  updateVideoSyncPair();
  UI.error.style.display='none';
});

VideoSyncUI.tlogAnchor?.addEventListener('click',()=>{
  const rows=document.querySelectorAll('#timelineContainer .tl-item[data-time]');
  if(!rows.length){
    UI.error.textContent='❌ Спочатку виконай звичайний TLOG-аналіз, щоб з’явився Timeline';
    UI.error.style.display='block';
    return;
  }
  setAwaitingTlogAnchor(true);
  if(VideoUI.status)VideoUI.status.textContent='Натисни потрібний рядок у Timeline — його час стане TLOG-якорем.';
  document.getElementById('timelineContainer')?.scrollIntoView({behavior:'smooth',block:'center'});
});

document.getElementById('timelineContainer')?.addEventListener('click',event=>{
  if(!awaitingTlogAnchor)return;
  const row=event.target.closest('.tl-item[data-time]');
  if(!row)return;
  event.preventDefault();
  event.stopPropagation();
  const seconds=timelineSeconds(row.dataset.time);
  if(!Number.isFinite(seconds)){
    UI.error.textContent='❌ Не вдалося прочитати час цього рядка Timeline';
    UI.error.style.display='block';
    return;
  }
  tlogAnchorSec=seconds;
  setAwaitingTlogAnchor(false);
  updateVideoSyncPair();
  UI.error.style.display='none';
},{capture:true});

VideoUI.input?.addEventListener('change',()=>setTimeout(updateVideoSyncPair,0));
VideoUI.enabled?.addEventListener('change',()=>{if(!videoEnabled){setAwaitingTlogAnchor(false);updateVideoSyncPair();}});
'''.rstrip()


def insert_once(source, marker, anchor, payload, before=True):
    if marker in source:
        return source
    if anchor not in source:
        raise SystemExit(f"anchor not found: {anchor[:100]!r}")
    return source.replace(anchor, payload + "\n\n" + anchor, 1) if before else source.replace(anchor, anchor + "\n\n" + payload, 1)


def main():
    source = INDEX.read_text(encoding="utf-8")
    source = insert_once(source, STYLE_MARKER, "</head>", STYLE, True)
    source = insert_once(source, HTML_MARKER, '      <div id="videoAssistStatus">', HTML, True)
    source = insert_once(source, JS_MARKER, "function canRunVideoAssistedAnalysis(){", JS, True)
    INDEX.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
