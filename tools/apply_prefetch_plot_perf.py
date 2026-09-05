from pathlib import Path

BACKEND = Path('backend/main.py')
FRONTEND = Path('index.html')
MARKER = '# PREFETCH_THROTTLED_MAVLINK_PLOT_V1'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    return text.replace(old, new, 1)


def patch_backend(text):
    if MARKER in text:
        return text

    endpoint_marker = '# LAZY_MAVLINK_PLOT_ENDPOINT\n'
    text = replace_once(
        text,
        endpoint_marker,
        (
            MARKER + '\n'
            '# Dynamic plot samples are capped to about 10 Hz per MAVLink message type.\n'
            '# This keeps the dynamic catalog useful while avoiding expensive msg.to_dict()\n'
            '# conversion for every high-rate ATTITUDE/IMU/ESC packet.\n'
            'PLOT_SAMPLE_INTERVAL_SEC = 0.10\n\n'
            + endpoint_marker
        ),
        'lazy endpoint marker',
    )

    text = replace_once(
        text,
        '        collector = MavlinkPlotCollector(max_points_per_series=1200)\n        first_timestamp = None\n',
        '        collector = MavlinkPlotCollector(max_points_per_series=1200)\n        last_plot_sample = {}\n        first_timestamp = None\n',
        'collector init',
    )

    old_collect = '''            try:\n                collector.add(msg_type, msg.to_dict(), t_stamp)\n            except Exception:\n                continue\n'''
    new_collect = '''            last_sample = last_plot_sample.get(msg_type)\n            should_collect = (\n                last_sample is None\n                or t_stamp - last_sample >= PLOT_SAMPLE_INTERVAL_SEC\n            )\n            if should_collect:\n                try:\n                    collector.add(msg_type, msg.to_dict(), t_stamp)\n                    last_plot_sample[msg_type] = t_stamp\n                except Exception:\n                    continue\n'''
    text = replace_once(text, old_collect, new_collect, 'collector add')
    return text


def patch_frontend(text):
    if 'function prefetchDynamicMavlinkPlot(result)' in text:
        return text

    old_helper = '''async function ensureDynamicMavlinkPlot(result){\n  if(result?.mavlink_plot?.groups)return result.mavlink_plot;\n  const plotToken=result?.plotToken;\n  if(!plotToken)throw new Error('Сервер не повернув токен TLOG для графіка. Запусти аналіз ще раз.');\n\n  const controller=new AbortController();\n  const timeout=setTimeout(()=>controller.abort(),300000);\n  try{\n    const response=await fetch(API_BASE_URL+'/mavlink-plot?token='+encodeURIComponent(plotToken),{\n      method:'POST',signal:controller.signal\n    });\n    const text=await response.text();\n    if(!response.ok)throw new Error('MAVLink графік HTTP '+response.status+': '+text.slice(0,500));\n    let payload;\n    try{payload=JSON.parse(text);}catch(e){throw new Error('Сервер графіків повернув не JSON.');}\n    if(!payload||payload.success===false)throw new Error(payload?.error||'Не вдалося побудувати MAVLink графіки.');\n    result.mavlink_plot=payload.mavlink_plot||{groups:{}};\n    return result.mavlink_plot;\n  }catch(error){\n    if(error?.name==='AbortError')throw new Error('Побудова MAVLink графіків перевищила 5 хв.');\n    throw error;\n  }finally{\n    clearTimeout(timeout);\n  }\n}\n'''

    new_helper = '''async function ensureDynamicMavlinkPlot(result){\n  if(result?.mavlink_plot?.groups)return result.mavlink_plot;\n  if(result?._mavlinkPlotPromise)return result._mavlinkPlotPromise;\n  const plotToken=result?.plotToken;\n  if(!plotToken)throw new Error('Сервер не повернув токен TLOG для графіка. Запусти аналіз ще раз.');\n\n  result._mavlinkPlotPromise=(async()=>{\n    const controller=new AbortController();\n    const timeout=setTimeout(()=>controller.abort(),300000);\n    try{\n      const response=await fetch(API_BASE_URL+'/mavlink-plot?token='+encodeURIComponent(plotToken),{\n        method:'POST',signal:controller.signal\n      });\n      const text=await response.text();\n      if(!response.ok)throw new Error('MAVLink графік HTTP '+response.status+': '+text.slice(0,500));\n      let payload;\n      try{payload=JSON.parse(text);}catch(e){throw new Error('Сервер графіків повернув не JSON.');}\n      if(!payload||payload.success===false)throw new Error(payload?.error||'Не вдалося побудувати MAVLink графіки.');\n      result.mavlink_plot=payload.mavlink_plot||{groups:{}};\n      return result.mavlink_plot;\n    }catch(error){\n      result._mavlinkPlotPromise=null;\n      if(error?.name==='AbortError')throw new Error('Побудова MAVLink графіків перевищила 5 хв.');\n      throw error;\n    }finally{\n      clearTimeout(timeout);\n    }\n  })();\n  return result._mavlinkPlotPromise;\n}\n\nfunction prefetchDynamicMavlinkPlot(result){\n  if(!result?.plotToken||result?.mavlink_plot?.groups||result?._mavlinkPlotPromise)return;\n  setTimeout(()=>{\n    ensureDynamicMavlinkPlot(result).catch(()=>{});\n  },150);\n}\n'''

    text = replace_once(text, old_helper, new_helper, 'dynamic plot helper')

    old_render = '''  if(graphBtn){\n    const hasGraph=buildGraphMetricRegistry(data?.graph_data||{}).some(x=>x.available);\n    graphBtn.hidden=!hasGraph;\n    graphBtn.onclick=async()=>{\n'''
    new_render = '''  if(graphBtn){\n    const hasGraph=buildGraphMetricRegistry(data?.graph_data||{}).some(x=>x.available);\n    graphBtn.hidden=!hasGraph;\n    graphBtn.onclick=async()=>{\n'''
    # Keep the button block unchanged; insert prefetch after the block closes.
    if old_render not in text:
        raise SystemExit('graph button anchor not found')

    old_after = '''    };\n  }\n  renderAnalysisFingerprint(data);\n'''
    new_after = '''    };\n  }\n  prefetchDynamicMavlinkPlot(data);\n  renderAnalysisFingerprint(data);\n'''
    text = replace_once(text, old_after, new_after, 'render prefetch hook')
    return text


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
