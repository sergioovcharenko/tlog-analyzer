from pathlib import Path
import re


INDEX = Path("index.html")
STYLE_MARKER = "/* VIDEO_FLIGHT_TIME_AUTO_SYNC_V1 */"
HTML_MARKER = "<!-- VIDEO_FLIGHT_TIME_AUTO_SYNC_V1 -->"
JS_MARKER = "// VIDEO_FLIGHT_TIME_AUTO_SYNC_V1"

STYLE = r'''
<style>
/* VIDEO_FLIGHT_TIME_AUTO_SYNC_V1 */
.video-auto-sync-panel{margin-top:10px;padding-top:10px;border-top:1px solid #253244}
#videoAutoSync{min-height:36px;padding:7px 11px;border:1px solid #22c55e;border-radius:6px;background:rgba(34,197,94,.09);color:#bbf7d0;font-weight:800;cursor:pointer}
#videoAutoSync:disabled{opacity:.55;cursor:wait}
#videoAutoSyncStatus{margin-top:8px;color:#cbd5e1;font-size:12px;line-height:1.45}
#videoAutoSyncConfidence{display:inline-block;margin-top:7px;padding:3px 7px;border:1px solid #475569;border-radius:999px;color:#cbd5e1;font-size:11px;font-weight:800}
#videoAutoSyncConfidence[hidden]{display:none!important}
.video-auto-sync-candidate-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:8px}
.video-auto-sync-candidate-row[hidden]{display:none!important}
#videoAutoSyncCandidate,#videoAutoSyncApplyCandidate{min-height:34px;border:1px solid #475569;border-radius:6px;background:#0d131a;color:#e2e8f0;padding:6px 9px}
#videoAutoSyncApplyCandidate{cursor:pointer;font-weight:800}
</style>
'''.strip()

HTML = r'''
        <!-- VIDEO_FLIGHT_TIME_AUTO_SYNC_V1 -->
        <div class="video-auto-sync-panel">
          <button id="videoAutoSync" type="button">⚡ Автосинхронізація по Flight Time</button>
          <div id="videoAutoSyncStatus">Автосинхронізація ще не запускалась.</div>
          <div id="videoAutoSyncConfidence" hidden></div>
          <div class="video-auto-sync-candidate-row" hidden>
            <select id="videoAutoSyncCandidate" aria-label="Політ для автосинхронізації"></select>
            <button id="videoAutoSyncApplyCandidate" type="button">Застосувати вибраний політ</button>
          </div>
        </div>
'''.rstrip()

JS = r'''
// VIDEO_FLIGHT_TIME_AUTO_SYNC_V1
const FlightTimeSyncUI={
  button:document.getElementById('videoAutoSync'),
  status:document.getElementById('videoAutoSyncStatus'),
  confidence:document.getElementById('videoAutoSyncConfidence'),
  candidate:document.getElementById('videoAutoSyncCandidate'),
  applyCandidate:document.getElementById('videoAutoSyncApplyCandidate'),
  candidateRow:document.querySelector('.video-auto-sync-candidate-row')
};

function flightTimeRoi(){
  return videoRois.find(roi=>String(roi?.label||'').trim()==='Flight Time')||null;
}

function resetAutoSyncUi(){
  if(FlightTimeSyncUI.status)FlightTimeSyncUI.status.textContent='Автосинхронізація ще не запускалась.';
  if(FlightTimeSyncUI.confidence){FlightTimeSyncUI.confidence.hidden=true;FlightTimeSyncUI.confidence.textContent='';}
  if(FlightTimeSyncUI.candidate){FlightTimeSyncUI.candidate.innerHTML='';}
  if(FlightTimeSyncUI.candidateRow)FlightTimeSyncUI.candidateRow.hidden=true;
}

function autoSyncConfidenceText(value){
  return ({high:'висока',medium:'середня',low:'низька'})[String(value||'').toLowerCase()]||'невідома';
}

function applyAutoSyncResult(autoSync){
  if(!autoSync||autoSync.status!=='success'||autoSync.confidence==='low')return false;
  const va=Number(autoSync.videoAnchorSec);
  const ta=Number(autoSync.tlogAnchorSec);
  if(!Number.isFinite(va)||!Number.isFinite(ta))return false;
  videoAnchorSec=va;
  tlogAnchorSec=ta;
  updateVideoSyncPair();
  return true;
}

function renderAutoSyncResult(autoSync){
  if(FlightTimeSyncUI.candidateRow)FlightTimeSyncUI.candidateRow.hidden=true;
  if(FlightTimeSyncUI.candidate)FlightTimeSyncUI.candidate.innerHTML='';
  if(FlightTimeSyncUI.confidence){
    FlightTimeSyncUI.confidence.hidden=!autoSync;
    FlightTimeSyncUI.confidence.textContent=autoSync?`Впевненість: ${autoSyncConfidenceText(autoSync.confidence)}`:'';
  }
  if(!autoSync){
    if(FlightTimeSyncUI.status)FlightTimeSyncUI.status.textContent='Сервер не повернув результат автосинхронізації.';
    return;
  }
  if(autoSync.status==='success'){
    applyAutoSyncResult(autoSync);
    const sample=(autoSync.samples||[])[0]||{};
    const flightTime=Number(sample.flightTimeSec);
    const mapped=Number(sample.mappedTlogSec);
    const offset=Number(autoSync.offsetSec);
    const pieces=[];
    if(Number.isFinite(flightTime))pieces.push(`Flight Time ${formatVideoSyncTime(flightTime)}`);
    if(autoSync.selectedFlight!=null)pieces.push(`Політ №${autoSync.selectedFlight}`);
    if(Number.isFinite(mapped))pieces.push(`TLOG ${formatVideoSyncTime(mapped)}`);
    if(Number.isFinite(offset))pieces.push(`зсув ${formatVideoSyncTime(offset)}`);
    if(FlightTimeSyncUI.status)FlightTimeSyncUI.status.textContent=pieces.join(' → ')||'Автосинхронізацію виконано.';
    return;
  }
  if(autoSync.status==='ambiguous'){
    const candidates=Array.isArray(autoSync.candidates)?autoSync.candidates:[];
    if(FlightTimeSyncUI.status)FlightTimeSyncUI.status.textContent='Знайдено кілька можливих польотів. Обери потрібний.';
    if(FlightTimeSyncUI.candidate){
      FlightTimeSyncUI.candidate.innerHTML=candidates.map(item=>`<option value="${Number(item.number)}" data-offset="${Number(item.offsetSec)}">Політ №${Number(item.number)} • зсув ${formatVideoSyncTime(Number(item.offsetSec))}</option>`).join('');
    }
    if(FlightTimeSyncUI.candidateRow)FlightTimeSyncUI.candidateRow.hidden=!candidates.length;
    return;
  }
  const warning=(autoSync.warnings||[])[0]||'Не вдалося стабільно прочитати Flight Time.';
  if(FlightTimeSyncUI.status)FlightTimeSyncUI.status.textContent=warning;
}

async function runFlightTimeAutoSync(){
  if(!selectedFile){throw new Error('Спочатку виконай TLOG-аналіз.');}
  if(!videoFile){throw new Error('Спочатку обери MP4 або MOV.');}
  const roi=flightTimeRoi();
  if(!roi){throw new Error('Намалюй ROI та вибери тип «Flight Time».');}
  if(FlightTimeSyncUI.status)FlightTimeSyncUI.status.textContent='Читаю Flight Time на кількох кадрах…';
  const formData=new FormData();
  formData.append('file',selectedFile,selectedFile.name);
  formData.append('video',videoFile,videoFile.name);
  formData.append('rois_json',JSON.stringify(videoRois));
  formData.append('auto_sync','true');
  formData.append('flight_time_roi_json',JSON.stringify(roi));
  const response=await fetch(API_BASE_URL+'/analyze-video',{method:'POST',body:formData});
  if(!response.ok)throw new Error(`HTTP ${response.status}`);
  const data=await response.json();
  window.__lastAnalysisResult=data;
  renderVideoAnalysisSection(data);
  const autoSync=data?.videoAnalysis?.autoSync||null;
  renderAutoSyncResult(autoSync);
  return autoSync;
}

FlightTimeSyncUI.button?.addEventListener('click',async()=>{
  FlightTimeSyncUI.button.disabled=true;
  UI.error.style.display='none';
  try{
    await runFlightTimeAutoSync();
  }catch(error){
    const message=error?.message||String(error||'Невідома помилка');
    if(FlightTimeSyncUI.status)FlightTimeSyncUI.status.textContent=`Автосинхронізація не виконана: ${message}`;
    UI.error.textContent=`❌ ${message}`;
    UI.error.style.display='block';
  }finally{
    FlightTimeSyncUI.button.disabled=false;
  }
});

FlightTimeSyncUI.applyCandidate?.addEventListener('click',()=>{
  const option=FlightTimeSyncUI.candidate?.selectedOptions?.[0];
  const offset=Number(option?.dataset?.offset);
  if(!Number.isFinite(offset))return;
  videoAnchorSec=0;
  tlogAnchorSec=offset;
  updateVideoSyncPair();
  if(FlightTimeSyncUI.status)FlightTimeSyncUI.status.textContent=`Обрано ${option.textContent}. Синхронізація готова.`;
});

VideoUI.input?.addEventListener('change',()=>resetAutoSyncUi());
VideoUI.enabled?.addEventListener('change',()=>{if(!videoEnabled)resetAutoSyncUi();});
'''.rstrip()

FINAL_OPTIONS = [
    "Flight Time",
    "Напруга АКБ",
    "Ампераж",
    "dBm",
    "RSSI",
    "VISP",
    "Режим",
    "Попередження",
    "Інше",
]


def main():
    source = INDEX.read_text(encoding="utf-8")

    if STYLE_MARKER not in source:
        if "</head>" not in source:
            raise SystemExit("head anchor not found")
        source = source.replace("</head>", STYLE + "\n</head>", 1)

    select_pattern = re.compile(r'(<select id="videoRoiLabel"[^>]*>).*?(</select>)', re.S)
    match = select_pattern.search(source)
    if not match:
        raise SystemExit("videoRoiLabel select not found")
    option_lines = "\n".join(f"          <option>{label}</option>" for label in FINAL_OPTIONS)
    replacement = match.group(1) + "\n" + option_lines + "\n        " + match.group(2)
    source = source[:match.start()] + replacement + source[match.end():]

    if HTML_MARKER not in source:
        html_anchor = '        <div id="videoSyncPair">відео — ↔ TLOG —</div>'
        if html_anchor not in source:
            raise SystemExit("videoSyncPair anchor not found")
        source = source.replace(html_anchor, html_anchor + "\n" + HTML, 1)

    if JS_MARKER not in source:
        js_anchor = "VideoUI.input?.addEventListener('change',()=>setTimeout(updateVideoSyncPair,0));"
        if js_anchor not in source:
            raise SystemExit("sync JS anchor not found")
        source = source.replace(js_anchor, JS + "\n\n" + js_anchor, 1)

    clear_anchor = "  tlogAnchorSec=null;\n  if(VideoUI.input)VideoUI.input.value='';"
    clear_replacement = "  tlogAnchorSec=null;\n  resetAutoSyncUi();\n  if(VideoUI.input)VideoUI.input.value='';"
    if clear_replacement not in source:
        if clear_anchor not in source:
            raise SystemExit("clearVideoFileState anchor not found")
        source = source.replace(clear_anchor, clear_replacement, 1)

    INDEX.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
