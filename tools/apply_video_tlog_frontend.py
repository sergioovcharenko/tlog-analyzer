from pathlib import Path


INDEX = Path("index.html")
STYLE_MARKER = "/* VIDEO_TLOG_FRONTEND_V1 */"
HTML_MARKER = "<!-- VIDEO_TLOG_FRONTEND_V1 -->"
JS_MARKER = "// VIDEO_TLOG_FRONTEND_V1"
ROI_STYLE_MARKER = "/* VIDEO_TLOG_ROI_V1 */"
ROI_OVERLAY_MARKER = "<!-- VIDEO_TLOG_ROI_OVERLAY_V1 -->"
ROI_CONTROLS_MARKER = "<!-- VIDEO_TLOG_ROI_CONTROLS_V1 -->"
ROI_JS_MARKER = "// VIDEO_TLOG_ROI_V1"

STYLE = r'''
<style>
/* VIDEO_TLOG_FRONTEND_V1 */
.video-assist-card{margin-top:18px;padding:16px 18px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-card)}
.video-assist-toggle{display:flex;align-items:center;gap:10px;font-weight:800;cursor:pointer}
.video-assist-toggle input{width:18px;height:18px;accent-color:var(--accent)}
#videoUploadPanel{margin-top:14px;padding-top:14px;border-top:1px solid var(--border-color)}
#videoUploadPanel[hidden]{display:none!important}
.video-assist-file-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.video-assist-file-btn{display:inline-flex;align-items:center;justify-content:center;min-height:38px;padding:8px 12px;border:1px solid #3b82f6;border-radius:7px;background:rgba(59,130,246,.1);color:#93c5fd;font-weight:800;cursor:pointer}
#videoFileInput{display:none}
#videoSelectedName{color:var(--text-muted);font-size:12px;overflow-wrap:anywhere}
.video-preview-shell{margin-top:12px;max-width:780px;background:#05080d;border:1px solid var(--border-color);border-radius:8px;overflow:hidden}
#videoPreview{display:block;width:100%;max-height:440px;background:#000}
#videoPreview:not([src]){display:none}
#videoAssistStatus{margin-top:10px;color:var(--text-muted);font-size:12px;line-height:1.45}
</style>
'''.strip()

ROI_STYLE = r'''
<style>
/* VIDEO_TLOG_ROI_V1 */
.video-preview-shell{position:relative}
#videoRoiOverlay{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;touch-action:none}
#videoRoiOverlay.roi-drawing{pointer-events:auto;cursor:crosshair}
.video-roi-tools{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:12px}
.video-roi-tools select,.video-roi-tools button{min-height:36px;border:1px solid var(--border-highlight);border-radius:6px;background:var(--input-bg);color:var(--text-main);padding:7px 10px;font-weight:700}
.video-roi-tools button{cursor:pointer}
#videoAddRoi{border-color:#22c55e;color:#86efac;background:rgba(34,197,94,.08)}
#videoClearRois{border-color:#ef4444;color:#fca5a5;background:rgba(239,68,68,.07)}
#videoRoiList{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}
.video-roi-chip{display:inline-flex;align-items:center;gap:6px;padding:5px 8px;border:1px solid #334155;border-radius:999px;background:#0d131a;color:#cbd5e1;font-size:11px}
.video-roi-chip button{border:0;background:transparent;color:#f87171;cursor:pointer;font-weight:900;padding:0}
#videoRoiHint{margin-top:7px;color:var(--text-muted);font-size:11px}
</style>
'''.strip()

HTML = r'''
  <!-- VIDEO_TLOG_FRONTEND_V1 -->
  <div class="video-assist-card" id="videoAssistCard">
    <label class="video-assist-toggle" for="videoFlightEnabled">
      <input id="videoFlightEnabled" type="checkbox">
      <span>🎥 Є відео польоту</span>
    </label>
    <div id="videoUploadPanel" hidden>
      <div class="video-assist-file-row">
        <label class="video-assist-file-btn" for="videoFileInput">📹 ОБРАТИ MP4 / MOV</label>
        <input id="videoFileInput" type="file" accept="video/mp4,video/quicktime,.mp4,.mov">
        <span id="videoSelectedName">Відео не вибрано</span>
      </div>
      <div class="video-preview-shell">
        <video id="videoPreview" controls preload="metadata" playsinline></video>
      </div>
      <div id="videoAssistStatus">Відео буде оброблятися тільки після увімкнення режиму та синхронізації з TLOG.</div>
    </div>
  </div>
'''.rstrip()

ROI_OVERLAY = r'''
        <!-- VIDEO_TLOG_ROI_OVERLAY_V1 -->
        <canvas id="videoRoiOverlay" aria-label="Зони аналізу відео"></canvas>
'''.rstrip()

ROI_CONTROLS = r'''
      <!-- VIDEO_TLOG_ROI_CONTROLS_V1 -->
      <div class="video-roi-tools">
        <select id="videoRoiLabel" aria-label="Тип зони відео">
          <option>Напруга</option>
          <option>dBm</option>
          <option>Режим</option>
          <option>Попередження</option>
          <option>Відеоканал</option>
          <option>Інше</option>
        </select>
        <button id="videoAddRoi" type="button">➕ Додати зону</button>
        <button id="videoClearRois" type="button">🗑 Очистити зони</button>
      </div>
      <div id="videoRoiList"></div>
      <div id="videoRoiHint">Натисни «Додати зону», потім протягни прямокутник поверх потрібного елемента на відео.</div>
'''.rstrip()

JS = r'''
// VIDEO_TLOG_FRONTEND_V1
let videoEnabled=false;
let videoFile=null;
let videoPreviewUrl=null;
let videoRois=[];
let videoAnchorSec=null;
let tlogAnchorSec=null;

const VideoUI={
  enabled:document.getElementById('videoFlightEnabled'),
  panel:document.getElementById('videoUploadPanel'),
  input:document.getElementById('videoFileInput'),
  preview:document.getElementById('videoPreview'),
  name:document.getElementById('videoSelectedName'),
  status:document.getElementById('videoAssistStatus')
};

function revokeVideoPreviewUrl(){
  if(videoPreviewUrl){
    URL.revokeObjectURL(videoPreviewUrl);
    videoPreviewUrl=null;
  }
}

function clearVideoFileState(){
  revokeVideoPreviewUrl();
  videoFile=null;
  videoRois=[];
  videoAnchorSec=null;
  tlogAnchorSec=null;
  if(VideoUI.input)VideoUI.input.value='';
  if(VideoUI.preview){
    VideoUI.preview.removeAttribute('src');
    try{VideoUI.preview.load();}catch(_){ }
  }
  if(VideoUI.name)VideoUI.name.textContent='Відео не вибрано';
  if(VideoUI.status)VideoUI.status.textContent='Відео буде оброблятися тільки після увімкнення режиму та синхронізації з TLOG.';
}

function resetVideoAssistState(){
  clearVideoFileState();
  videoEnabled=false;
  if(VideoUI.enabled)VideoUI.enabled.checked=false;
  if(VideoUI.panel)VideoUI.panel.hidden=true;
}

VideoUI.enabled?.addEventListener('change',()=>{
  videoEnabled=!!VideoUI.enabled.checked;
  if(VideoUI.panel)VideoUI.panel.hidden=!videoEnabled;
  if(!videoEnabled)clearVideoFileState();
});

VideoUI.input?.addEventListener('change',event=>{
  const file=event.target.files?.[0]||null;
  if(!file){clearVideoFileState();return;}
  const name=String(file.name||'');
  if(!/\.(mp4|mov)$/i.test(name)){
    clearVideoFileState();
    UI.error.textContent='❌ Для відео потрібен файл MP4 або MOV';
    UI.error.style.display='block';
    return;
  }
  revokeVideoPreviewUrl();
  videoFile=file;
  videoRois=[];
  videoAnchorSec=null;
  tlogAnchorSec=null;
  videoPreviewUrl=URL.createObjectURL(videoFile);
  if(VideoUI.preview)VideoUI.preview.src=videoPreviewUrl;
  if(VideoUI.name)VideoUI.name.textContent=`${name} • ${formatBytes(file.size)}`;
  if(VideoUI.status)VideoUI.status.textContent='Відео вибрано. Спочатку виконай TLOG-аналіз, потім синхронізуй час.';
  UI.error.style.display='none';
});

function canRunVideoAssistedAnalysis(){
  return videoEnabled && !!videoFile && Number.isFinite(videoAnchorSec) && Number.isFinite(tlogAnchorSec);
}
'''.rstrip()

ROI_JS = r'''
// VIDEO_TLOG_ROI_V1
const VideoRoiUI={
  overlay:document.getElementById('videoRoiOverlay'),
  label:document.getElementById('videoRoiLabel'),
  add:document.getElementById('videoAddRoi'),
  clear:document.getElementById('videoClearRois'),
  list:document.getElementById('videoRoiList'),
  hint:document.getElementById('videoRoiHint')
};
let videoRoiDrawing=false;
let videoRoiStart=null;
let videoRoiDraft=null;

function videoContentRect(){
  const video=VideoUI.preview;
  if(!video)return {x:0,y:0,width:0,height:0};
  const width=video.clientWidth||0;
  const height=video.clientHeight||0;
  const sourceW=video.videoWidth||0;
  const sourceH=video.videoHeight||0;
  if(!width||!height||!sourceW||!sourceH)return {x:0,y:0,width,height};
  const sourceAspect=sourceW/sourceH;
  const boxAspect=width/height;
  if(boxAspect>sourceAspect){
    const contentW=height*sourceAspect;
    return {x:(width-contentW)/2,y:0,width:contentW,height};
  }
  const contentH=width/sourceAspect;
  return {x:0,y:(height-contentH)/2,width,height:contentH};
}

function resizeVideoRoiOverlay(){
  const canvas=VideoRoiUI.overlay;
  const video=VideoUI.preview;
  if(!canvas||!video)return;
  const width=Math.max(1,Math.round(video.clientWidth||1));
  const height=Math.max(1,Math.round(video.clientHeight||1));
  if(canvas.width!==width)canvas.width=width;
  if(canvas.height!==height)canvas.height=height;
  renderVideoRois();
}

function sourceRoiToDisplayRect(roi){
  const video=VideoUI.preview;
  const content=videoContentRect();
  if(!video?.videoWidth||!video?.videoHeight||!content.width||!content.height)return null;
  return {
    x:content.x+(roi.x/video.videoWidth)*content.width,
    y:content.y+(roi.y/video.videoHeight)*content.height,
    width:(roi.width/video.videoWidth)*content.width,
    height:(roi.height/video.videoHeight)*content.height
  };
}

function displayRectToSourceRoi(rect,label){
  const video=VideoUI.preview;
  const content=videoContentRect();
  if(!video?.videoWidth||!video?.videoHeight||!content.width||!content.height)return null;
  const x1=Math.max(content.x,Math.min(content.x+content.width,rect.x));
  const y1=Math.max(content.y,Math.min(content.y+content.height,rect.y));
  const x2=Math.max(content.x,Math.min(content.x+content.width,rect.x+rect.width));
  const y2=Math.max(content.y,Math.min(content.y+content.height,rect.y+rect.height));
  const width=Math.max(0,x2-x1);
  const height=Math.max(0,y2-y1);
  if(width<4||height<4)return null;
  return {
    id:`roi-${Date.now()}-${Math.random().toString(16).slice(2,7)}`,
    label:label||'Інше',
    x:Math.round(((x1-content.x)/content.width)*video.videoWidth),
    y:Math.round(((y1-content.y)/content.height)*video.videoHeight),
    width:Math.round((width/content.width)*video.videoWidth),
    height:Math.round((height/content.height)*video.videoHeight)
  };
}

function renderVideoRoiList(){
  if(!VideoRoiUI.list)return;
  VideoRoiUI.list.innerHTML=videoRois.map(roi=>`<span class="video-roi-chip">${roi.label} ${roi.width}×${roi.height}<button type="button" data-roi-delete="${roi.id}" aria-label="Видалити ${roi.label}">×</button></span>`).join('');
  VideoRoiUI.list.querySelectorAll('[data-roi-delete]').forEach(button=>{
    button.addEventListener('click',()=>{
      videoRois=videoRois.filter(roi=>roi.id!==button.dataset.roiDelete);
      renderVideoRois();
    });
  });
}

function renderVideoRois(){
  const canvas=VideoRoiUI.overlay;
  if(!canvas)return;
  const ctx=canvas.getContext('2d');
  if(!ctx)return;
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.lineWidth=2;
  ctx.font='12px sans-serif';
  videoRois.forEach(roi=>{
    const rect=sourceRoiToDisplayRect(roi);
    if(!rect)return;
    ctx.strokeStyle='#22c55e';
    ctx.fillStyle='rgba(34,197,94,.12)';
    ctx.fillRect(rect.x,rect.y,rect.width,rect.height);
    ctx.strokeRect(rect.x,rect.y,rect.width,rect.height);
    ctx.fillStyle='#dcfce7';
    ctx.fillText(roi.label,rect.x+5,Math.max(13,rect.y+14));
  });
  if(videoRoiDraft){
    ctx.strokeStyle='#f59e0b';
    ctx.fillStyle='rgba(245,158,11,.10)';
    ctx.fillRect(videoRoiDraft.x,videoRoiDraft.y,videoRoiDraft.width,videoRoiDraft.height);
    ctx.strokeRect(videoRoiDraft.x,videoRoiDraft.y,videoRoiDraft.width,videoRoiDraft.height);
  }
  renderVideoRoiList();
}

function overlayPoint(event){
  const canvas=VideoRoiUI.overlay;
  const bounds=canvas.getBoundingClientRect();
  const scaleX=canvas.width/Math.max(1,bounds.width);
  const scaleY=canvas.height/Math.max(1,bounds.height);
  return {x:(event.clientX-bounds.left)*scaleX,y:(event.clientY-bounds.top)*scaleY};
}

function clampPointToVideo(point){
  const rect=videoContentRect();
  return {
    x:Math.max(rect.x,Math.min(rect.x+rect.width,point.x)),
    y:Math.max(rect.y,Math.min(rect.y+rect.height,point.y))
  };
}

VideoRoiUI.add?.addEventListener('click',()=>{
  if(!videoFile||!VideoUI.preview?.videoWidth){
    UI.error.textContent='❌ Спочатку обери відео та дочекайся завантаження прев’ю';
    UI.error.style.display='block';
    return;
  }
  resizeVideoRoiOverlay();
  videoRoiDrawing=true;
  VideoRoiUI.overlay?.classList.add('roi-drawing');
  if(VideoRoiUI.hint)VideoRoiUI.hint.textContent='Протягни прямокутник поверх потрібної ділянки відео.';
});

VideoRoiUI.clear?.addEventListener('click',()=>{
  videoRois=[];
  videoRoiDraft=null;
  renderVideoRois();
});

VideoRoiUI.overlay?.addEventListener('pointerdown',event=>{
  if(!videoRoiDrawing)return;
  event.preventDefault();
  const content=videoContentRect();
  const point=overlayPoint(event);
  if(point.x<content.x||point.x>content.x+content.width||point.y<content.y||point.y>content.y+content.height)return;
  videoRoiStart=clampPointToVideo(point);
  videoRoiDraft={x:videoRoiStart.x,y:videoRoiStart.y,width:0,height:0};
  VideoRoiUI.overlay.setPointerCapture?.(event.pointerId);
});

VideoRoiUI.overlay?.addEventListener('pointermove',event=>{
  if(!videoRoiDrawing||!videoRoiStart)return;
  const point=clampPointToVideo(overlayPoint(event));
  videoRoiDraft={
    x:Math.min(videoRoiStart.x,point.x),
    y:Math.min(videoRoiStart.y,point.y),
    width:Math.abs(point.x-videoRoiStart.x),
    height:Math.abs(point.y-videoRoiStart.y)
  };
  renderVideoRois();
});

VideoRoiUI.overlay?.addEventListener('pointerup',event=>{
  if(!videoRoiDrawing||!videoRoiStart)return;
  const point=clampPointToVideo(overlayPoint(event));
  const displayRect={
    x:Math.min(videoRoiStart.x,point.x),
    y:Math.min(videoRoiStart.y,point.y),
    width:Math.abs(point.x-videoRoiStart.x),
    height:Math.abs(point.y-videoRoiStart.y)
  };
  const roi=displayRectToSourceRoi(displayRect,VideoRoiUI.label?.value||'Інше');
  if(roi)videoRois.push(roi);
  videoRoiStart=null;
  videoRoiDraft=null;
  videoRoiDrawing=false;
  VideoRoiUI.overlay.classList.remove('roi-drawing');
  if(VideoRoiUI.hint)VideoRoiUI.hint.textContent=roi?'Зону додано. Можна додати ще одну.':'Зона надто мала — спробуй ще раз.';
  renderVideoRois();
});

VideoUI.preview?.addEventListener('loadedmetadata',resizeVideoRoiOverlay);
VideoUI.preview?.addEventListener('loadeddata',resizeVideoRoiOverlay);
window.addEventListener('resize',resizeVideoRoiOverlay);
VideoUI.input?.addEventListener('change',()=>setTimeout(resizeVideoRoiOverlay,0));
VideoUI.enabled?.addEventListener('change',()=>{if(!videoEnabled){videoRois=[];renderVideoRois();}});
'''.rstrip()


def insert_once(source: str, marker: str, anchor: str, payload: str, before: bool = True) -> str:
    if marker in source:
        return source
    if anchor not in source:
        raise SystemExit(f"anchor not found for {marker}: {anchor[:80]!r}")
    if before:
        return source.replace(anchor, payload + "\n\n" + anchor, 1)
    return source.replace(anchor, anchor + "\n\n" + payload, 1)


def main():
    source = INDEX.read_text(encoding="utf-8")

    source = insert_once(source, STYLE_MARKER, "</head>", STYLE, before=True)
    source = insert_once(source, ROI_STYLE_MARKER, "</head>", ROI_STYLE, before=True)

    html_anchor = '  <button class="analyze" id="analyzeButton" disabled>⏳ АНАЛІЗ...</button>'
    source = insert_once(source, HTML_MARKER, html_anchor, HTML, before=True)

    overlay_anchor = '        <video id="videoPreview" controls preload="metadata" playsinline></video>'
    source = insert_once(source, ROI_OVERLAY_MARKER, overlay_anchor, ROI_OVERLAY, before=False)

    controls_anchor = '      <div id="videoAssistStatus">'
    source = insert_once(source, ROI_CONTROLS_MARKER, controls_anchor, ROI_CONTROLS, before=True)

    js_anchor = "// REPORT_EXPORT_V1"
    source = insert_once(source, JS_MARKER, js_anchor, JS, before=True)
    source = insert_once(source, ROI_JS_MARKER, "function canRunVideoAssistedAnalysis(){", ROI_JS, before=True)

    # Reset optional-video state together with the existing analyzer reset.
    reset_anchor = "function resetForm(){\n  closeGraphViewer();"
    if "function resetForm(){\n  resetVideoAssistState();" not in source:
        if reset_anchor not in source:
            raise SystemExit("resetForm anchor not found")
        source = source.replace(
            reset_anchor,
            "function resetForm(){\n  resetVideoAssistState();\n  closeGraphViewer();",
            1,
        )

    # Do not start any analysis when video mode is enabled but no clip is selected.
    click_anchor = "UI.btn.addEventListener('click',async()=>{\n  if(!selectedFile)return;"
    click_replacement = "UI.btn.addEventListener('click',async()=>{\n  if(!selectedFile)return;\n  if(videoEnabled&&!videoFile){\n    UI.error.textContent='❌ Обери MP4 або MOV для відеоаналізу';\n    UI.error.style.display='block';\n    return;\n  }"
    if "❌ Обери MP4 або MOV для відеоаналізу" not in source:
        if click_anchor not in source:
            raise SystemExit("analyze button anchor not found")
        source = source.replace(click_anchor, click_replacement, 1)

    # Keep /analyze as the default preflight/TLOG-only path. Once manual anchors
    # exist, append video data and switch only that request to /analyze-video.
    form_anchor = "    formData.append('file',file,file.name);"
    form_payload = r'''    formData.append('file',file,file.name);
    const useVideoAssist=canRunVideoAssistedAnalysis();
    if(useVideoAssist){
      formData.append('video',videoFile,videoFile.name);
      formData.append('video_anchor_sec',String(videoAnchorSec));
      formData.append('tlog_anchor_sec',String(tlogAnchorSec));
      formData.append('rois_json',JSON.stringify(videoRois));
    }
    const analyzeEndpoint=useVideoAssist?'/analyze-video':'/analyze';'''
    if "const analyzeEndpoint=useVideoAssist?'/analyze-video':'/analyze';" not in source:
        if form_anchor not in source:
            raise SystemExit("FormData anchor not found")
        source = source.replace(form_anchor, form_payload, 1)

    fetch_anchor = "    const response=await fetch(API_BASE_URL+'/analyze',{"
    fetch_replacement = "    const response=await fetch(API_BASE_URL+analyzeEndpoint,{"
    if fetch_replacement not in source:
        if fetch_anchor not in source:
            raise SystemExit("analyze fetch anchor not found")
        source = source.replace(fetch_anchor, fetch_replacement, 1)

    INDEX.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
