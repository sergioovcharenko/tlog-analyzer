from pathlib import Path

BACKEND = Path('backend/main.py')
FRONTEND = Path('index.html')
MARKER = '# LAZY_MAVLINK_PLOT_ENDPOINT'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    return text.replace(old, new, 1)


def patch_backend(text):
    if MARKER in text:
        return text

    text = replace_once(
        text,
        '''        # Dynamic chart-only catalog. Existing analysis branches remain unchanged.\n        mavlink_plot_collector = MavlinkPlotCollector(max_points_per_series=1200)\n\n''',
        '',
        'collector init',
    )
    text = replace_once(
        text,
        '''            if t_stamp > 0:\n                try:\n                    mavlink_plot_collector.add(msg_type, msg.to_dict(), t_stamp)\n                except Exception:\n                    pass\n\n                current_timestamp = t_stamp\n''',
        '''            if t_stamp > 0:\n                current_timestamp = t_stamp\n''',
        'collector add',
    )
    text = replace_once(
        text,
        '''        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)\n        mavlink_plot = mavlink_plot_collector.build(base_t)\n        board_messages = build_board_messages(raw_timeline, base_t)\n''',
        '''        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)\n        board_messages = build_board_messages(raw_timeline, base_t)\n''',
        'collector build',
    )
    text = replace_once(
        text,
        '''            "graph_data": graph_data,\n            "mavlink_plot": mavlink_plot,\n            "board_messages": board_messages,\n''',
        '''            "graph_data": graph_data,\n            "board_messages": board_messages,\n''',
        'analyze result plot field',
    )

    endpoint = r'''

# LAZY_MAVLINK_PLOT_ENDPOINT
# Heavy dynamic MAVLink catalog is intentionally separated from /analyze.
# The browser calls this endpoint only when the user opens the graph viewer.
@app.post("/mavlink-plot")
async def mavlink_plot_on_demand(file: UploadFile = File(...)):
    temp_path = None
    mav = None
    try:
        suffix = Path(file.filename or "flight.tlog").suffix or ".tlog"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)

        collector = MavlinkPlotCollector(max_points_per_series=1200)
        base_timestamp = None
        mav = mavutil.mavlink_connection(temp_path, robust_parsing=True)

        while True:
            msg = mav.recv_match(blocking=False)
            if msg is None:
                break
            msg_type = msg.get_type()
            t_stamp = getattr(msg, "_timestamp", 0.0)
            if not valid_number(t_stamp) or float(t_stamp) <= 0:
                continue
            t_stamp = float(t_stamp)
            if base_timestamp is None:
                base_timestamp = t_stamp
            try:
                collector.add(msg_type, msg.to_dict(), t_stamp)
            except Exception:
                continue

        base_timestamp = float(base_timestamp or 0.0)
        return {
            "success": True,
            "mavlink_plot": collector.build(base_timestamp),
        }
    except Exception as exc:
        return {"success": False, "error": f"MAVLink plot: {exc}"}
    finally:
        try:
            if mav is not None:
                mav.close()
        except Exception:
            pass
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass

'''
    anchor = 'if __name__ == "__main__":'
    if anchor not in text:
        raise SystemExit('backend main anchor not found')
    return text.replace(anchor, endpoint + anchor, 1)


def patch_frontend(text):
    if 'async function ensureDynamicMavlinkPlot(result)' in text:
        return text

    api_anchor = "const API_BASE_URL = 'https://tlog-analyzer-api.onrender.com';\n"
    helper = r'''

async function ensureDynamicMavlinkPlot(result){
  if(result?.mavlink_plot?.groups)return result.mavlink_plot;
  if(!selectedFile)throw new Error('TLOG файл більше не доступний. Завантаж його повторно.');

  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),300000);
  try{
    const formData=new FormData();
    formData.append('file',selectedFile,selectedFile.name);
    const response=await fetch(API_BASE_URL+'/mavlink-plot',{
      method:'POST',body:formData,signal:controller.signal
    });
    const text=await response.text();
    if(!response.ok)throw new Error('MAVLink графік HTTP '+response.status+': '+text.slice(0,500));
    let payload;
    try{payload=JSON.parse(text);}catch(e){throw new Error('Сервер графіків повернув не JSON.');}
    if(!payload||payload.success===false)throw new Error(payload?.error||'Не вдалося побудувати MAVLink графіки.');
    result.mavlink_plot=payload.mavlink_plot||{groups:{}};
    return result.mavlink_plot;
  }catch(error){
    if(error?.name==='AbortError')throw new Error('Побудова MAVLink графіків перевищила 5 хв.');
    throw error;
  }finally{
    clearTimeout(timeout);
  }
}
'''
    text = replace_once(text, api_anchor, api_anchor + helper, 'API_BASE_URL')

    old_click = '    graphBtn.onclick=()=>openGraphViewer(data);'
    new_click = r'''    graphBtn.onclick=async()=>{
      const oldText=graphBtn.textContent;
      graphBtn.disabled=true;
      graphBtn.textContent='Завантаження графіків...';
      try{
        await ensureDynamicMavlinkPlot(data);
        openGraphViewer(data);
      }catch(err){
        UI.error.textContent='❌ '+(err?.message||err);
        UI.error.style.display='block';
      }finally{
        graphBtn.disabled=false;
        graphBtn.textContent=oldText;
      }
    };'''
    return replace_once(text, old_click, new_click, 'graph button click')


def main():
    backend = BACKEND.read_text(encoding='utf-8')
    frontend = FRONTEND.read_text(encoding='utf-8')
    new_backend = patch_backend(backend)
    new_frontend = patch_frontend(frontend)
    if new_backend != backend:
        BACKEND.write_text(new_backend, encoding='utf-8')
        print('patched backend/main.py')
    if new_frontend != frontend:
        FRONTEND.write_text(new_frontend, encoding='utf-8')
        print('patched index.html')
    if new_backend == backend and new_frontend == frontend:
        print('already patched')


if __name__ == '__main__':
    main()
