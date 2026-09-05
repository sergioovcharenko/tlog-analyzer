from pathlib import Path

main_path = Path("backend/main.py")
html_path = Path("index.html")
main = main_path.read_text(encoding="utf-8")
html = html_path.read_text(encoding="utf-8")

# Backend integration -------------------------------------------------------
if "from backend.mavlink_plot import MavlinkPlotCollector, build_board_messages" not in main:
    anchor = "from pymavlink import mavutil\n"
    if anchor not in main:
        raise SystemExit("pymavlink import anchor not found")
    main = main.replace(anchor, anchor + "from backend.mavlink_plot import MavlinkPlotCollector, build_board_messages\n", 1)

if "mavlink_plot_collector = MavlinkPlotCollector" not in main:
    anchor = "        # STATUSTEXT MAVLink2 chunks\n        statustext_chunks = {}\n"
    if anchor not in main:
        raise SystemExit("collector init anchor not found")
    main = main.replace(
        anchor,
        anchor + "\n        # Dynamic chart-only catalog. Existing analysis branches remain unchanged.\n        mavlink_plot_collector = MavlinkPlotCollector(max_points_per_series=1200)\n",
        1,
    )

old_loop = '''        needed_messages = [
            "HEARTBEAT", "SYS_STATUS", "VFR_HUD", "EFI_STATUS", "ALTITUDE",
            "LOCAL_POSITION_NED", "GLOBAL_POSITION_INT", "RC_CHANNELS",
            "RADIO", "RADIO_STATUS", "ATTITUDE", "VIBRATION",
            "TEMPERATURE", "HIGHRES_IMU", "SCALED_PRESSURE",
            "SCALED_PRESSURE2", "SCALED_PRESSURE3", "MCU_STATUS",
            "STATUSTEXT", "ESC_TELEMETRY_1_TO_4", "PARAM_VALUE",
        ]

        while True:
            msg = mav.recv_match(type=needed_messages, blocking=False)
'''
new_loop = '''        # Read every decoded MAVLink message so the plot catalog is truly dynamic.
        # Specialized analysis below still reacts only to the message types it knows.
        while True:
            msg = mav.recv_match(blocking=False)
'''
if old_loop in main:
    main = main.replace(old_loop, new_loop, 1)
elif "msg = mav.recv_match(blocking=False)" not in main:
    raise SystemExit("MAVLink loop anchor not found")

collector_anchor = '''            msg_type = msg.get_type()
            t_stamp = getattr(msg, "_timestamp", 0.0)

            if t_stamp > 0:
'''
collector_insert = '''            msg_type = msg.get_type()
            t_stamp = getattr(msg, "_timestamp", 0.0)

            if t_stamp > 0:
                try:
                    mavlink_plot_collector.add(msg_type, msg.to_dict(), t_stamp)
                except Exception:
                    pass

'''
if "mavlink_plot_collector.add(msg_type, msg.to_dict(), t_stamp)" not in main:
    if collector_anchor not in main:
        raise SystemExit("collector packet anchor not found")
    main = main.replace(collector_anchor, collector_insert, 1)

# Preserve raw STATUSTEXT severity for the synchronized board-message panel.
old_sig = '''            is_error=False,
            is_pilot_action=False,
            event_type="SYSTEM",
        ):
'''
new_sig = '''            is_error=False,
            is_pilot_action=False,
            event_type="SYSTEM",
            severity=None,
        ):
'''
if old_sig in main and '"severity": severity,' not in main:
    main = main.replace(old_sig, new_sig, 1)

if '"severity": severity,' not in main:
    anchor = '''                    "eventType": event_type,
                    "isError": is_error,
'''
    if anchor not in main:
        raise SystemExit("event severity row anchor not found")
    main = main.replace(anchor, '''                    "eventType": event_type,
                    "severity": severity,
                    "isError": is_error,
''', 1)

statustext_call = '''                False,
                event_type,
            )
'''
if "severity=severity" not in main:
    # This exact call occurs inside process_complete_statustext immediately after event_type.
    marker = '''            add_event(
                full_txt,
                timestamp,
                mode,
                bool(thrust_match or is_serious_system_text(full_txt)),
                False,
                event_type,
            )
'''
    replacement = '''            add_event(
                full_txt,
                timestamp,
                mode,
                bool(thrust_match or is_serious_system_text(full_txt)),
                False,
                event_type,
                severity=severity,
            )
'''
    if marker not in main:
        raise SystemExit("STATUSTEXT add_event anchor not found")
    main = main.replace(marker, replacement, 1)

if '"mavlink_plot": mavlink_plot_collector.build(base_t)' not in main:
    anchor = '''        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)

        return {
            "success": True,
            "graph_data": graph_data,
'''
    replacement = '''        graph_data = _build_graph_data(timeline, attitude_graph_samples, base_t)
        mavlink_plot = mavlink_plot_collector.build(base_t)
        board_messages = build_board_messages(raw_timeline, base_t)

        return {
            "success": True,
            "graph_data": graph_data,
            "mavlink_plot": mavlink_plot,
            "board_messages": board_messages,
'''
    if anchor not in main:
        raise SystemExit("API result graph_data anchor not found")
    main = main.replace(anchor, replacement, 1)

main_path.write_text(main, encoding="utf-8")
html_path.write_text(html, encoding="utf-8")
print("Applied dynamic MAVLink backend integration")
