from pathlib import Path


INDEX = Path("index.html")
STYLE_MARKER = "/* VIDEO_TLOG_RESULTS_V1 */"
HTML_MARKER = "<!-- VIDEO_TLOG_RESULTS_V1 -->"
JS_MARKER = "// VIDEO_TLOG_RESULTS_V1"
CALL_MARKER = "renderVideoAnalysisSection(data);"

STYLE = r'''
<style>
/* VIDEO_TLOG_RESULTS_V1 */
.video-analysis-results{margin:26px 0 8px}
.video-analysis-results[hidden]{display:none!important}
.video-analysis-shell{border:1px solid #334155;border-left:4px solid #f59e0b;border-radius:9px;background:var(--bg-card);padding:18px}
.video-analysis-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:14px}
.video-analysis-stat{border:1px solid var(--border-color);border-radius:7px;background:var(--bg-header);padding:10px 12px}
.video-analysis-stat b{display:block;color:#f1f5f9;font-size:15px;margin-top:3px}
.video-analysis-stat span{color:var(--text-muted);font-size:11px;text-transform:uppercase;font-weight:800}
.video-analysis-subtitle{margin:15px 0 7px;color:#cbd5e1;font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.35px}
.video-analysis-list{margin:0;padding-left:20px;color:#dbeafe;font-size:12px;line-height:1.55}
.video-analysis-list li{margin:5px 0}
.video-analysis-empty{color:var(--text-muted);font-size:12px;line-height:1.5}
.video-analysis-warning{color:#fde68a}
.video-analysis-correlation{border-left:3px solid #60a5fa;padding-left:9px}
</style>
'''.strip()

HTML = r'''
    <!-- VIDEO_TLOG_RESULTS_V1 -->
    <section id="videoAnalysisSection" class="video-analysis-results" hidden>
      <div class="section-title">🎥 AI — ВІДЕО + TLOG</div>
      <div class="video-analysis-shell">
        <div id="videoAnalysisSummary" class="video-analysis-summary"></div>
        <div class="video-analysis-subtitle">Попередження</div>
        <div id="videoAnalysisWarnings"></div>
        <div class="video-analysis-subtitle">Спостереження з відео</div>
        <div id="videoAnalysisObservations"></div>
        <div class="video-analysis-subtitle">Часові збіги з TLOG</div>
        <div id="videoAnalysisCorrelations"></div>
      </div>
    </section>
'''.rstrip()

JS = r'''
// VIDEO_TLOG_RESULTS_V1
function videoResultNode(tag,className,text){
  const node=document.createElement(tag);
  if(className)node.className=className;
  if(text!==undefined&&text!==null)node.textContent=String(text);
  return node;
}

function videoResultTime(value){
  const n=Number(value);
  if(!Number.isFinite(n))return '—';
  const minutes=Math.floor(Math.abs(n)/60);
  const seconds=Math.abs(n)-minutes*60;
  return `${n<0?'-':''}${String(minutes).padStart(2,'0')}:${seconds.toFixed(3).padStart(6,'0')}`;
}

function renderVideoAnalysisSection(data){
  const section=document.getElementById('videoAnalysisSection');
  const summary=document.getElementById('videoAnalysisSummary');
  const warningsBox=document.getElementById('videoAnalysisWarnings');
  const observationsBox=document.getElementById('videoAnalysisObservations');
  const correlationsBox=document.getElementById('videoAnalysisCorrelations');
  if(!section||!summary||!warningsBox||!observationsBox||!correlationsBox)return;

  const videoAnalysis=data?.videoAnalysis;
  if(!videoAnalysis){
    section.hidden=true;
    summary.replaceChildren();
    warningsBox.replaceChildren();
    observationsBox.replaceChildren();
    correlationsBox.replaceChildren();
    return;
  }

  section.hidden=false;
  const rois=Array.isArray(videoAnalysis.rois)?videoAnalysis.rois:[];
  const observations=Array.isArray(videoAnalysis.observations)?videoAnalysis.observations:[];
  const correlations=Array.isArray(videoAnalysis.correlations)?videoAnalysis.correlations:[];
  const warnings=Array.isArray(videoAnalysis.warnings)?videoAnalysis.warnings:[];

  summary.replaceChildren();
  const stats=[
    ['Тривалість відео',Number.isFinite(Number(videoAnalysis.videoDurationSec))?`${Number(videoAnalysis.videoDurationSec).toFixed(1)} с`:'—'],
    ['Якір відео',videoResultTime(videoAnalysis.anchorVideoSec)],
    ['Якір TLOG',videoResultTime(videoAnalysis.anchorTlogSec)],
    ['ROI-зони',String(rois.length)],
    ['Кадри для вибірки',videoAnalysis.sampleCount??'—'],
  ];
  stats.forEach(([label,value])=>{
    const card=videoResultNode('div','video-analysis-stat');
    card.append(videoResultNode('span','',label),videoResultNode('b','',value));
    summary.append(card);
  });

  warningsBox.replaceChildren();
  if(warnings.length){
    const list=videoResultNode('ul','video-analysis-list video-analysis-warning');
    warnings.forEach(item=>list.append(videoResultNode('li','',item)));
    warningsBox.append(list);
  }else{
    warningsBox.append(videoResultNode('div','video-analysis-empty','Немає попереджень відеоаналізу.'));
  }

  observationsBox.replaceChildren();
  if(observations.length){
    const list=videoResultNode('ul','video-analysis-list');
    observations.forEach(observation=>{
      const confidence=Number(observation?.confidence);
      const confidenceText=Number.isFinite(confidence)?`${Math.round(confidence*100)}%`:'—';
      const roiLabel=observation?.roiLabel||'Інше';
      const text=`${videoResultTime(observation?.videoTimeSec)} відео / ${videoResultTime(observation?.tlogTimeSec)} TLOG • ${roiLabel} • ${observation?.description||observation?.type||'Спостереження'} • confidence ${confidenceText}`;
      list.append(videoResultNode('li','',text));
    });
    observationsBox.append(list);
  }else{
    observationsBox.append(videoResultNode('div','video-analysis-empty','Синхронізація та ROI готові. На цьому етапі кадри ще не інтерпретуються AI; візуальні спостереження будуть додані окремим етапом.'));
  }

  correlationsBox.replaceChildren();
  if(correlations.length){
    const list=videoResultNode('ul','video-analysis-list');
    correlations.forEach(correlation=>{
      const deltaSec=Number(correlation?.deltaSec);
      const suffix=Number.isFinite(deltaSec)?` Δ ${deltaSec.toFixed(3)} с`:'';
      list.append(videoResultNode('li','video-analysis-correlation',`${correlation?.summary||'Часово близька подія'}${suffix}`));
    });
    correlationsBox.append(list);
  }else{
    correlationsBox.append(videoResultNode('div','video-analysis-empty','Часових збігів відео ↔ TLOG поки немає.'));
  }
}
'''.rstrip()


def insert_once(source, marker, anchor, payload, before=True):
    if marker in source:
        return source
    if anchor not in source:
        raise SystemExit(f"anchor not found: {anchor[:100]!r}")
    return source.replace(anchor, payload + "\n\n" + anchor, 1) if before else source.replace(anchor, anchor + "\n\n" + payload, 1)


def main():
    source=INDEX.read_text(encoding="utf-8")
    source=insert_once(source,STYLE_MARKER,"</head>",STYLE,True)
    source=insert_once(source,HTML_MARKER,'    <div class="section-title">🚁 ДИНАМІКА ПОЛЬОТУ</div>',HTML,True)
    source=insert_once(source,JS_MARKER,"function renderResults(data){",JS,True)
    if CALL_MARKER not in source:
        anchor="function renderResults(data){\n  window.__lastAnalysisResult=data;"
        replacement="function renderResults(data){\n  window.__lastAnalysisResult=data;\n  renderVideoAnalysisSection(data);"
        if anchor not in source:
            raise SystemExit("renderResults call anchor not found")
        source=source.replace(anchor,replacement,1)
    INDEX.write_text(source,encoding="utf-8")


if __name__ == "__main__":
    main()
