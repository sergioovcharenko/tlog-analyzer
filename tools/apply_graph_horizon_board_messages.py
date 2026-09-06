from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
marker='GRAPH_HORIZON_BOARD_MESSAGES_V1'
if marker in s:
    raise SystemExit(0)
old="""function applyHorizonOnlyDarkLayout(){
  try{localStorage.setItem('tlog-theme','dark');}catch(_e){}
  document.documentElement.setAttribute('data-tlog-theme','dark');
  const summary=document.getElementById('graphDashboardSummary');
  const attitudePanel=document.getElementById('attitudePanel');
  if(summary&&attitudePanel){
    summary.classList.add('in-attitude');
    if(summary.parentElement!==attitudePanel)attitudePanel.appendChild(summary);
  }
  const attitudeDock=document.querySelector('.graph-dock-panel[data-dock-panel=\"attitude\"]');
  if(attitudeDock)attitudeDock.hidden=false;
  document.querySelectorAll('.graph-dock-panel:not([data-dock-panel=\"attitude\"])').forEach(el=>{el.hidden=true;});
}
/* RESTORE_DASHBOARD_V2_MOVE_SUMMARY_V1 */
"""
new="""function applyHorizonOnlyDarkLayout(){
  try{localStorage.setItem('tlog-theme','dark');}catch(_e){}
  document.documentElement.setAttribute('data-tlog-theme','dark');
  const summary=document.getElementById('graphDashboardSummary');
  const attitudePanel=document.getElementById('attitudePanel');
  const messages=document.getElementById('boardMessagesPanel');
  if(summary&&attitudePanel){
    summary.classList.add('in-attitude');
    if(summary.parentElement!==attitudePanel)attitudePanel.appendChild(summary);
  }
  if(messages&&attitudePanel){
    messages.classList.add('attitude-board-messages');
    if(messages.parentElement!==attitudePanel)attitudePanel.appendChild(messages);
    messages.hidden=false;
  }
  const attitudeDock=document.querySelector('.graph-dock-panel[data-dock-panel=\"attitude\"]');
  if(attitudeDock)attitudeDock.hidden=false;
  document.querySelectorAll('.graph-dock-panel:not([data-dock-panel=\"attitude\"])').forEach(el=>{el.hidden=true;});
}
/* RESTORE_DASHBOARD_V2_MOVE_SUMMARY_V1 */
"""
if old not in s:
    raise SystemExit('anchor not found')
s=s.replace(old,new,1)
css="""

/* GRAPH_HORIZON_BOARD_MESSAGES_V1 */
#attitudePanel .attitude-board-messages{
  display:block!important;
  margin-top:10px!important;
  border:1px solid #27364a!important;
  border-radius:8px!important;
  background:#080d13!important;
  padding:10px!important;
}
#attitudePanel .attitude-board-messages .board-messages-title{
  color:#f8fafc!important;
  font-size:11px!important;
  font-weight:900!important;
}
#attitudePanel .attitude-board-messages .board-messages-subtitle{
  color:#64748b!important;
}
#attitudePanel .attitude-board-messages #boardMessagesList{
  max-height:210px!important;
  overflow:auto!important;
}
"""
s=s.replace('</style>\n</head>',css+'\n</style>\n</head>',1)
p.write_text(s,encoding='utf-8')
