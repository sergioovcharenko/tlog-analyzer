from pathlib import Path


INDEX = Path("index.html")
STYLE_MARKER = "/* VIDEO_TLOG_FRONTEND_V1 */"
HTML_MARKER = "<!-- VIDEO_TLOG_FRONTEND_V1 -->"
JS_MARKER = "// VIDEO_TLOG_FRONTEND_V1"

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

    html_anchor = '  <button class="analyze" id="analyzeButton" disabled>⏳ АНАЛІЗ...</button>'
    source = insert_once(source, HTML_MARKER, html_anchor, HTML, before=True)

    js_anchor = "// REPORT_EXPORT_V1"
    source = insert_once(source, JS_MARKER, js_anchor, JS, before=True)

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
