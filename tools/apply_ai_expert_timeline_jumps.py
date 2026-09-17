from pathlib import Path

INDEX = Path("index.html")
MARKER = "AI_EXPERT_TIMELINE_JUMPS_V1"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if old not in source:
        raise SystemExit(f"AI expert timeline jump anchor not found: {label}")
    return source.replace(old, new, 1)


def main() -> None:
    source = INDEX.read_text(encoding="utf-8")
    if MARKER in source:
        return

    css_anchor = ".ai-expert-chronology{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}\n"
    css = css_anchor + ".ai-expert-chronology li[data-jump-time]{cursor:pointer;border-radius:5px;padding:3px 6px;margin-left:-6px;transition:.15s}\n.ai-expert-chronology li[data-jump-time]:hover,.ai-expert-chronology li[data-jump-time]:focus-visible{background:rgba(59,130,246,.10);color:#bfdbfe;outline:none}\n"
    source = replace_once(source, css_anchor, css, "chronology css")

    renderer_anchor = "function renderAiExpert(expert){"
    helpers = r'''// AI_EXPERT_TIMELINE_JUMPS_V1
function appendExpertChronology(host,events){
  if(!host||!Array.isArray(events)||!events.length)return;
  const section=document.createElement('section');
  section.className='ai-expert-section ai-expert-chronology';
  const heading=document.createElement('h4');heading.textContent='ХРОНОЛОГІЯ КЛЮЧОВИХ ПОДІЙ';
  const list=document.createElement('ul');
  events.forEach(event=>{
    const li=document.createElement('li');
    const time=formatExpertTime(event?.time_s);
    li.textContent=`${time} — ${event?.text||event?.type||'подія'}`;
    if(Number.isFinite(Number(event?.time_s))){
      li.dataset.jumpTime=time;
      li.title='Перейти до рядка Timeline';
      li.tabIndex=0;
      li.setAttribute('role','button');
    }
    list.appendChild(li);
  });
  section.append(heading,list);host.appendChild(section);
}

function jumpAiExpertToTimelineTime(targetTime){
  const timeline=document.getElementById('timelineContainer');
  if(!timeline||!targetTime)return;
  const rows=[...timeline.querySelectorAll('.tl-item[data-time]')];
  let target=rows.find(row=>row.dataset.time===targetTime);
  if(!target){
    const wanted=timelineSeconds(targetTime);
    if(Number.isFinite(wanted)&&rows.length){
      let best=null,bestDiff=Infinity;
      rows.forEach(row=>{
        const value=timelineSeconds(row.dataset.time);
        if(!Number.isFinite(value))return;
        const diff=Math.abs(value-wanted);
        if(diff<bestDiff){bestDiff=diff;best=row;}
      });
      target=best;
    }
  }
  if(!target)return;
  target.scrollIntoView({behavior:'smooth',block:'center',inline:'nearest'});
  target.classList.remove('timeline-jump-highlight');
  void target.offsetWidth;
  target.classList.add('timeline-jump-highlight');
  setTimeout(()=>target.classList.remove('timeline-jump-highlight'),1800);
}

function bindAiExpertTimelineJumps(){
  const block=document.getElementById('aiExpertBlock');
  if(!block)return;
  block.querySelectorAll('.ai-expert-chronology li[data-jump-time]').forEach(li=>{
    if(li.dataset.jumpBound==='1')return;
    const activate=()=>{
      const targetTime=li.dataset.jumpTime;
      if(targetTime)jumpAiExpertToTimelineTime(targetTime);
    };
    li.addEventListener('click',activate);
    li.addEventListener('keydown',event=>{
      if(event.key!=='Enter'&&event.key!==' ')return;
      event.preventDefault();
      activate();
    });
    li.dataset.jumpBound='1';
  });
}

'''
    source = replace_once(source, renderer_anchor, helpers + renderer_anchor, "expert renderer")

    chronology_anchor = "    const chronology=(session.chronology||[]).map(event=>`${formatExpertTime(event.time_s)} — ${event.text||event.type||'подія'}`);\n    appendExpertList(body,'ХРОНОЛОГІЯ КЛЮЧОВИХ ПОДІЙ',chronology,'ai-expert-chronology');\n"
    chronology_replacement = "    appendExpertChronology(body,session.chronology||[]);\n"
    source = replace_once(source, chronology_anchor, chronology_replacement, "expert chronology rendering")

    end_anchor = "  block.hidden=false;\n}\n\nfunction renderResults(data){"
    end_replacement = "  block.hidden=false;\n  bindAiExpertTimelineJumps();\n}\n\nfunction renderResults(data){"
    source = replace_once(source, end_anchor, end_replacement, "expert render completion")

    INDEX.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
