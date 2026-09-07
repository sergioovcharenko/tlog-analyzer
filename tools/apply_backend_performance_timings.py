from pathlib import Path

path = Path("backend/main.py")
text = path.read_text(encoding="utf-8")
original = text

if "PERFORMANCE_TIMINGS_V1" in text and '"performance": _perf' in text:
    print("Backend performance timings already applied")
    raise SystemExit(0)

old = '''@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    # v1.1 «Швидкість»: preserve v1.0 chunked upload; calculation algorithms unchanged.'''
new = '''@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    # PERFORMANCE_TIMINGS_V1 — lightweight stage profiling; telemetry calculations unchanged.
    _perf_total_start = time.perf_counter()
    _perf_upload_start = _perf_total_start
    _perf = {}

    # v1.1 «Швидкість»: preserve v1.0 chunked upload; calculation algorithms unchanged.'''
if old not in text:
    raise SystemExit("analyze start marker not found")
text = text.replace(old, new, 1)

old = '''    finally:
        temp.close()

    plot_token = None

    try:
        mav = mavutil.mavlink_connection(temp.name)'''
new = '''    finally:
        temp.close()

    _perf["upload_ms"] = round((time.perf_counter() - _perf_upload_start) * 1000.0, 1)
    _perf["file_size_mb"] = round(os.path.getsize(temp.name) / (1024.0 * 1024.0), 2)
    _perf_parse_start = time.perf_counter()

    plot_token = None

    try:
        mav = mavutil.mavlink_connection(temp.name)'''
if old not in text:
    raise SystemExit("upload end marker not found")
text = text.replace(old, new, 1)

old = '''        # Estimate antenna pointing from NED position azimuth + dBm.
        antenna_analysis = analyze_antenna_direction(raw_timeline, first_flight_arm_timestamp)'''
new = '''        _perf["parse_rules_ms"] = round((time.perf_counter() - _perf_parse_start) * 1000.0, 1)
        _perf_timeline_start = time.perf_counter()

        # Estimate antenna pointing from NED position azimuth + dBm.
        antenna_analysis = analyze_antenna_direction(raw_timeline, first_flight_arm_timestamp)'''
if old not in text:
    raise SystemExit("parse/timeline marker not found")
text = text.replace(old, new, 1)

old = '''        # Display
        rssi_percent = ('''
new = '''        _perf["timeline_ms"] = round((time.perf_counter() - _perf_timeline_start) * 1000.0, 1)

        # Display
        rssi_percent = ('''
if old not in text:
    raise SystemExit("timeline end marker not found")
text = text.replace(old, new, 1)

old = '''        # ====================================================
        # AI / FLIGHT ANALYSIS
        # ====================================================

        ai_alerts = []'''
new = '''        # ====================================================
        # AI / FLIGHT ANALYSIS
        # ====================================================

        _perf_summary_start = time.perf_counter()
        ai_alerts = []'''
if old not in text:
    raise SystemExit("summary start marker not found")
text = text.replace(old, new, 1)

old = '''        # AI_RECONSTRUCTION_BACKEND_V1
        _ai_radio_episodes = []'''
new = '''        _perf["summary_rules_ms"] = round((time.perf_counter() - _perf_summary_start) * 1000.0, 1)
        _perf_ai_start = time.perf_counter()

        # AI_RECONSTRUCTION_BACKEND_V1
        _ai_radio_episodes = []'''
if old not in text:
    raise SystemExit("AI reconstruction start marker not found")
text = text.replace(old, new, 1)

old = '''        ai_reconstruction = build_ai_reconstruction(ai_reconstruction_facts)

        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)
        board_messages = build_board_messages(raw_timeline, base_t)
        plot_token = _register_plot_file(temp.name)

        return {
            "success": True,'''
new = '''        ai_reconstruction = build_ai_reconstruction(ai_reconstruction_facts)
        _perf["ai_ms"] = round((time.perf_counter() - _perf_ai_start) * 1000.0, 1)

        _perf_graphs_start = time.perf_counter()
        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)
        board_messages = build_board_messages(raw_timeline, base_t)
        plot_token = _register_plot_file(temp.name)
        _perf["graphs_ms"] = round((time.perf_counter() - _perf_graphs_start) * 1000.0, 1)
        _perf["server_total_ms"] = round((time.perf_counter() - _perf_total_start) * 1000.0, 1)

        ai_alerts.append(
            "⏱ <b>Швидкість аналізу backend:</b> "
            f"файл {_perf['file_size_mb']:.2f} МБ; "
            f"завантаження {_perf['upload_ms'] / 1000.0:.2f} с; "
            f"MAVLink/правила {_perf['parse_rules_ms'] / 1000.0:.2f} с; "
            f"Timeline {_perf['timeline_ms'] / 1000.0:.2f} с; "
            f"підсумкові правила {_perf['summary_rules_ms'] / 1000.0:.2f} с; "
            f"AI {_perf['ai_ms'] / 1000.0:.3f} с; "
            f"графіки {_perf['graphs_ms'] / 1000.0:.2f} с; "
            f"backend разом {_perf['server_total_ms'] / 1000.0:.2f} с."
        )

        return {
            "success": True,
            "performance": _perf,'''
if old not in text:
    raise SystemExit("return/performance marker not found")
text = text.replace(old, new, 1)

if text == original:
    raise SystemExit("no changes applied")

path.write_text(text, encoding="utf-8")
print("Applied backend performance timings")
