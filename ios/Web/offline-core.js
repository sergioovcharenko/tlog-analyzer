(function(){
  'use strict';

  function bytesFromBase64(base64){
    const raw = atob(base64);
    const out = new Uint8Array(raw.length);
    for(let i=0;i<raw.length;i++) out[i]=raw.charCodeAt(i);
    return out;
  }

  function formatBytes(n){
    if(!Number.isFinite(n)) return '—';
    if(n<1024) return n+' B';
    if(n<1024*1024) return (n/1024).toFixed(1)+' KB';
    return (n/1024/1024).toFixed(1)+' MB';
  }

  window.iOSTLOGBridge = {
    receiveFile(payload){
      const status=document.getElementById('status');
      const name=document.getElementById('name');
      const size=document.getElementById('size');
      const engine=document.getElementById('engine');

      name.textContent=payload?.name||'—';
      size.textContent=formatBytes(Number(payload?.size));
      status.textContent='Файл отримано локально. Дані не відправляються в інтернет.';

      const bytes=bytesFromBase64(String(payload?.base64||''));
      window.__iosTlogBytes=bytes;

      engine.className='ok';
      engine.textContent='Файл у пам\'яті: '+bytes.length+' байт. Наступний етап — локальний MAVLink parser та перенесення правил аналізу.';
    },
    showNativeError(message){
      const status=document.getElementById('status');
      status.textContent='Помилка: '+message;
      status.className='warn';
    }
  };
})();
