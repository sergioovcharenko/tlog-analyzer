from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')
marker = 'LAND_SUMMARY_FRONTEND_FALLBACK_V1'

if marker not in s:
    anchor = "  const maxCurrentRow=(Array.isArray(data.timeline)?data.timeline:[])\n"
    if anchor not in s:
        raise SystemExit('maxCurrentRow anchor not found')

    helper = r'''  /* LAND_SUMMARY_FRONTEND_FALLBACK_V1
     Build the LAND summary from already-returned Timeline data as a frontend
     fallback. This makes the alert independent of whether the Render backend
     has already redeployed the newer LAND-summary code. */
  function buildLandTransitionAlerts(timeline){
    const rows=Array.isArray(timeline)?timeline:[];
    const transitions=[];
    let prevMode='';

    rows.forEach(row=>{
      const mode=String(row?.mode||'').trim().toUpperCase();
      if(!mode)return;
      if(mode==='LAND'&&prevMode&&prevMode!=='LAND'){
        transitions.push({from:prevMode,time:String(row?.time||'').trim()});
      }
      prevMode=mode;
    });

    if(!transitions.length)return [];
    const first=transitions[0];
    const jumpAttr=first.time?` data-jump-time="${first.time}"`:'';
    let details='';
    if(transitions.length===1){
      details=`${first.from} → LAND${first.time?` о ${first.time}`:''}`;
    }else{
      const last=transitions[transitions.length-1];
      details=`зафіксовано ${transitions.length} переходи; ${first.from} → LAND${first.time?` о ${first.time}`:''}; останній LAND${last.time?` о ${last.time}`:''}`;
    }
    return [`<span class="ai-jump"${jumpAttr}>🛬 <b>Перехід у LAND:</b> ${details}. ${first.time?'Натисніть, щоб перейти до цього моменту в Timeline.':''}</span>`];
  }

'''
    s = s.replace(anchor, helper + anchor, 1)

    combined_anchor = "  const combinedAiAlerts=[\n    ...highCurrentAlerts,\n"
    if combined_anchor not in s:
        raise SystemExit('combinedAiAlerts anchor not found')
    replacement = "  const landTransitionAlerts=buildLandTransitionAlerts(data.timeline);\n  if((data.ai?.alerts||[]).some(a=>String(a).includes('Перехід у LAND:')))landTransitionAlerts.length=0;\n\n  const combinedAiAlerts=[\n    ...highCurrentAlerts,\n    ...landTransitionAlerts,\n"
    s = s.replace(combined_anchor, replacement, 1)

p.write_text(s, encoding='utf-8')
print('Applied LAND summary frontend fallback')
