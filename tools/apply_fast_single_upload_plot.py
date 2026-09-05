from pathlib import Path

BACKEND = Path('backend/main.py')
FRONTEND = Path('index.html')
MARKER = '# FAST_SINGLE_UPLOAD_PLOT_V1'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    return text.replace(old, new, 1)


def patch_backend(text):
    if MARKER in text:
        return text

    text = replace_once(text, 'import webbrowser\n', 'import webbrowser\nimport uuid\n', 'uuid import')

    cache_helpers = '''\n\n# FAST_SINGLE_UPLOAD_PLOT_V1\n# Keep the already-uploaded TLOG briefly so the graph request does not upload it again.\nPLOT_FILE_CACHE = {}\nPLOT_FILE_CACHE_TTL_SEC = 15 * 60\n\n\ndef _cleanup_plot_file_cache():\n    now = time.time()\n    expired = [\n        token for token, item in list(PLOT_FILE_CACHE.items())\n        if now - float(item.get("created", 0.0)) > PLOT_FILE_CACHE_TTL_SEC\n    ]\n    for token in expired:\n        item = PLOT_FILE_CACHE.pop(token, None) or {}\n        path = item.get("path")\n        if path and os.path.exists(path):\n            try:\n                os.unlink(path)\n            except OSError:\n                pass\n\n\ndef _register_plot_file(path):\n    _cleanup_plot_file_cache()\n    token = uuid.uuid4().hex\n    PLOT_FILE_CACHE[token] = {"path": path, "created": time.time()}\n    return token\n\n\ndef _consume_plot_file(token):\n    _cleanup_plot_file_cache()\n    item = PLOT_FILE_CACHE.pop(str(token or ""), None)\n    if not item:\n        return None\n    path = item.get("path")\n    return path if path and os.path.exists(path) else None\n'''
    text = replace_once(text, '# ============================================================\n# HEALTH\n# ============================================================\n', cache_helpers + '\n\n# ============================================================\n# HEALTH\n# ============================================================\n', 'health section')

    text = replace_once(
        text,
        '    try:\n        mav = mavutil.mavlink_connection(temp.name)\n',
        '    plot_token = None\n\n    try:\n        mav = mavutil.mavlink_connection(temp.name)\n',
        'analyze parse start',
    )

    old_loop = '''        # Read every decoded MAVLink message so the plot catalog is truly dynamic.\n        # Specialized analysis below still reacts only to the message types it knows.\n        while True:\n            msg = mav.recv_match(blocking=False)\n'''
    new_loop = '''        # Fast analyzer path: decode only messages used by the flight analysis.\n        # The full dynamic MAVLink catalog is parsed later from the same server-side file.\n        needed_messages = [\n            "HEARTBEAT", "SYS_STATUS", "VFR_HUD", "EFI_STATUS", "ALTITUDE",\n            "LOCAL_POSITION_NED", "GLOBAL_POSITION_INT", "RC_CHANNELS",\n            "RADIO", "RADIO_STATUS", "ATTITUDE", "VIBRATION",\n            "TEMPERATURE", "HIGHRES_IMU", "SCALED_PRESSURE",\n            "SCALED_PRESSURE2", "SCALED_PRESSURE3", "MCU_STATUS",\n            "STATUSTEXT", "ESC_TELEMETRY_1_TO_4", "PARAM_VALUE",\n        ]\n\n        while True:\n            msg = mav.recv_match(type=needed_messages, blocking=False)\n'''
    text = replace_once(text, old_loop, new_loop, 'filtered loop')

    text = replace_once(
        text,
        '        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)\n        board_messages = build_board_messages(raw_timeline, base_t)\n\n        return {\n            "success": True,\n',
        '        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)\n        board_messages = build_board_messages(raw_timeline, base_t)\n        plot_token = _register_plot_file(temp.name)\n\n        return {\n            "success": True,\n            "plotToken": plot_token,\n',
        'plot token result',
    )

    text = replace_once(
        text,
        '''    finally:\n        if os.path.exists(temp.name):\n            try:\n                os.unlink(temp.name)\n            except Exception:\n                pass\n''',
        '''    finally:\n        if plot_token is None and os.path.exists(temp.name):\n            try:\n                os.unlink(temp.name)\n            except Exception:\n                pass\n''',
        'analyze cleanup',
    )

    start = text.index('# LAZY_MAVLINK_PLOT_ENDPOINT')
    end = text.index('if __name__ == "__main__":', start)
    endpoint = '''# LAZY_MAVLINK_PLOT_ENDPOINT\n# Dynamic graph parsing reuses the TLOG already uploaded by /analyze.\n@app.post("/mavlink-plot")\nasync def mavlink_plot_on_demand(token: str):\n    temp_path = _consume_plot_file(token)\n    mav = None\n    if not temp_path:\n        return {\n            "success": False,\n            "error": "TLOG для графіка вже недоступний. Запусти аналіз файлу ще раз.",\n        }\n    try:\n        collector = MavlinkPlotCollector(max_points_per_series=1200)\n        first_timestamp = None\n        arm_timestamp = None\n        was_armed = False\n        mav = mavutil.mavlink_connection(temp_path, robust_parsing=True)\n\n        while True:\n            msg = mav.recv_match(blocking=False)\n            if msg is None:\n                break\n            msg_type = msg.get_type()\n            t_stamp = getattr(msg, "_timestamp", 0.0)\n            if not valid_number(t_stamp) or float(t_stamp) <= 0:\n                continue\n            t_stamp = float(t_stamp)\n            if first_timestamp is None:\n                first_timestamp = t_stamp\n\n            if msg_type == "HEARTBEAT" and msg.get_srcComponent() == 1:\n                armed = bool(\n                    getattr(msg, "base_mode", 0)\n                    & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED\n                )\n                if armed and not was_armed and arm_timestamp is None:\n                    arm_timestamp = t_stamp\n                was_armed = armed\n\n            try:\n                collector.add(msg_type, msg.to_dict(), t_stamp)\n            except Exception:\n                continue\n\n        base_timestamp = float(arm_timestamp or first_timestamp or 0.0)\n        return {\n            "success": True,\n            "mavlink_plot": collector.build(base_timestamp),\n        }\n    except Exception as exc:\n        return {"success": False, "error": f"MAVLink plot: {exc}"}\n    finally:\n        try:\n            if mav is not None:\n                mav.close()\n        except Exception:\n            pass\n        if temp_path and os.path.exists(temp_path):\n            try:\n                os.unlink(temp_path)\n            except OSError:\n                pass\n\n'''
    text = text[:start] + endpoint + text[end:]
    return text


def patch_frontend(text):
    if 'const plotToken=result?.plotToken;' in text and "/mavlink-plot?token=" in text:
        return text

    old = '''async function ensureDynamicMavlinkPlot(result){\n  if(result?.mavlink_plot?.groups)return result.mavlink_plot;\n  if(!selectedFile)throw new Error('TLOG файл більше не доступний. Завантаж його повторно.');\n\n  const controller=new AbortController();\n  const timeout=setTimeout(()=>controller.abort(),300000);\n  try{\n    const formData=new FormData();\n    formData.append('file',selectedFile,selectedFile.name);\n    const response=await fetch(API_BASE_URL+'/mavlink-plot',{\n      method:'POST',body:formData,signal:controller.signal\n    });\n'''
    new = '''async function ensureDynamicMavlinkPlot(result){\n  if(result?.mavlink_plot?.groups)return result.mavlink_plot;\n  const plotToken=result?.plotToken;\n  if(!plotToken)throw new Error('Сервер не повернув токен TLOG для графіка. Запусти аналіз ще раз.');\n\n  const controller=new AbortController();\n  const timeout=setTimeout(()=>controller.abort(),300000);\n  try{\n    const response=await fetch(API_BASE_URL+'/mavlink-plot?token='+encodeURIComponent(plotToken),{\n      method:'POST',signal:controller.signal\n    });\n'''
    return replace_once(text, old, new, 'frontend lazy request')


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
