from pathlib import Path

path = Path("index.html")
html = path.read_text(encoding="utf-8")
marker = "TEMP_ANALYSIS_WAIT_OVERLAY_START"

if marker in html:
    print("temporary analysis wait overlay already present")
    raise SystemExit(0)

block = r'''
<!-- TEMP_ANALYSIS_WAIT_OVERLAY_START: remove this whole block when the temporary image is no longer wanted. -->
<script>
(function(){
  const TEMP_WAIT_IMAGE='https://i.imgur.com/CduyK.jpeg';

  function ensureTemporaryAnalysisWaitOverlay(){
    let overlay=document.getElementById('temporaryAnalysisWaitOverlay');
    if(overlay)return overlay;

    overlay=document.createElement('div');
    overlay.id='temporaryAnalysisWaitOverlay';
    overlay.setAttribute('aria-live','polite');
    Object.assign(overlay.style,{
      position:'fixed',
      inset:'0',
      zIndex:'100000',
      display:'none',
      alignItems:'center',
      justifyContent:'center',
      padding:'24px',
      background:'rgba(3,7,12,.92)',
      backdropFilter:'blur(4px)'
    });

    const card=document.createElement('div');
    Object.assign(card.style,{
      width:'min(92vw,760px)',
      maxHeight:'92vh',
      overflow:'auto',
      padding:'18px',
      border:'1px solid #334155',
      borderRadius:'16px',
      background:'#0f141c',
      boxShadow:'0 22px 70px rgba(0,0,0,.6)',
      textAlign:'center'
    });

    const img=document.createElement('img');
    img.src=TEMP_WAIT_IMAGE;
    img.alt='Очікування завершення аналізу TLOG';
    img.referrerPolicy='no-referrer';
    Object.assign(img.style,{
      display:'block',
      width:'100%',
      maxHeight:'68vh',
      objectFit:'contain',
      borderRadius:'10px',
      background:'#090d12'
    });

    const title=document.createElement('div');
    title.textContent='НЕ ТОРОПИСЬ!';
    Object.assign(title.style,{
      marginTop:'14px',
      fontSize:'clamp(26px,5vw,48px)',
      lineHeight:'1.05',
      fontWeight:'900',
      letterSpacing:'1.5px',
      color:'#f8fafc'
    });

    const subtitle=document.createElement('div');
    subtitle.textContent='TLOG аналізується…';
    Object.assign(subtitle.style,{
      marginTop:'8px',
      fontSize:'14px',
      fontWeight:'700',
      color:'#94a3b8'
    });

    card.append(img,title,subtitle);
    overlay.appendChild(card);
    document.body.appendChild(overlay);
    return overlay;
  }

  window.showTemporaryAnalysisWaitOverlay=function showTemporaryAnalysisWaitOverlay(){
    const overlay=ensureTemporaryAnalysisWaitOverlay();
    overlay.style.display='flex';
  };

  window.hideTemporaryAnalysisWaitOverlay=function hideTemporaryAnalysisWaitOverlay(){
    const overlay=document.getElementById('temporaryAnalysisWaitOverlay');
    if(overlay)overlay.style.display='none';
  };

  function analysisFinished(){
    const results=document.querySelector('.results');
    const error=document.querySelector('.error');
    const resultsVisible=results && getComputedStyle(results).display!=='none';
    const errorVisible=error && getComputedStyle(error).display!=='none';
    if(resultsVisible||errorVisible)window.hideTemporaryAnalysisWaitOverlay();
  }

  document.addEventListener('click',function(event){
    const button=event.target.closest('.analyze');
    if(!button || !button.classList.contains('active'))return;
    window.showTemporaryAnalysisWaitOverlay();
  },true);

  const observer=new MutationObserver(analysisFinished);
  document.querySelectorAll('.results,.error').forEach(function(node){
    observer.observe(node,{attributes:true,attributeFilter:['style','class']});
  });
})();
</script>
<!-- TEMP_ANALYSIS_WAIT_OVERLAY_END -->
'''

closing = "</body>"
if closing not in html:
    raise SystemExit("</body> marker not found")

html = html.replace(closing, block + "\n" + closing, 1)
path.write_text(html, encoding="utf-8")
print("temporary analysis wait overlay applied")
