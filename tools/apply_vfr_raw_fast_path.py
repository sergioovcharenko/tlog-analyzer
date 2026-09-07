from pathlib import Path

path = Path('backend/main.py')
text = path.read_text(encoding='utf-8')
original = text

if 'VFR_RAW_FAST_PATH_V1' in text:
    print('VFR raw fast path already applied')
    raise SystemExit(0)

old = '''try:\n    from backend.indexed_tlog import build_indexed_numeric_series\nexcept ImportError:\n    from indexed_tlog import build_indexed_numeric_series\n'''
new = '''try:\n    from backend.indexed_tlog import build_indexed_numeric_series\nexcept ImportError:\n    from indexed_tlog import build_indexed_numeric_series\ntry:\n    from backend.raw_vfr import build_raw_vfr_hud_series_from_reader\nexcept ImportError:\n    from raw_vfr import build_raw_vfr_hud_series_from_reader\n'''
if old not in text:
    raise SystemExit('indexed_tlog import marker not found')
text = text.replace(old, new, 1)

old = '''        _perf["efi_indexed_decoded_count"] = int((efi_indexed or {}).get("decoded_count", 0))\n\n        # Base\n'''
new = '''        _perf["efi_indexed_decoded_count"] = int((efi_indexed or {}).get("decoded_count", 0))\n\n        # VFR_RAW_FAST_PATH_V1 — reuse the already-built pymavlink mmap index and\n        # unpack every VFR_HUD payload directly from bytes, avoiding a pymavlink\n        # message object for this high-rate stream. Full recv_match fallback remains.\n        _vfr_raw_start = time.perf_counter()\n        vfr_raw = build_raw_vfr_hud_series_from_reader(mav)\n        _perf["vfr_raw_ms"] = round((time.perf_counter() - _vfr_raw_start) * 1000.0, 1)\n        vfr_raw_enabled = vfr_raw is not None\n        vfr_raw_samples = list((vfr_raw or {}).get("samples", []))\n        vfr_raw_sample_index = 0\n        _perf["vfr_raw_enabled"] = bool(vfr_raw_enabled)\n        _perf["vfr_raw_input_count"] = int((vfr_raw or {}).get("input_count", 0))\n        _perf["vfr_raw_decoded_count"] = int((vfr_raw or {}).get("decoded_count", 0))\n\n        # Base\n'''
if old not in text:
    raise SystemExit('EFI metrics marker not found')
text = text.replace(old, new, 1)

marker = '''        # ====================================================\n        # MAVLINK LOOP\n        # ====================================================\n'''
helper = '''        def apply_raw_vfr_row(row, timestamp):\n            nonlocal latest_baro_alt, curr_azimuth, ground_baro_alt, baro_rel_alt\n            nonlocal max_speed, total_distance_travelled, curr_ground_speed\n            nonlocal last_ground_speed_timestamp, max_throttle\n\n            alt_val = row.get("alt")\n            if valid_number(alt_val):\n                latest_baro_alt = float(alt_val)\n                if ground_baro_alt is None:\n                    ground_baro_alt = latest_baro_alt\n                baro_rel_alt = max(0.0, latest_baro_alt - ground_baro_alt)\n                if global_rel_alt is None:\n                    update_flight_altitude(baro_rel_alt, timestamp, "BARO")\n\n            heading_val = row.get("heading")\n            if valid_number(heading_val):\n                heading_val = float(heading_val)\n                if 0.0 <= heading_val <= 360.0:\n                    curr_azimuth = heading_val % 360.0\n\n            ground_speed_val = row.get("groundspeed")\n            if valid_number(ground_speed_val):\n                ground_speed = max(0.0, float(ground_speed_val))\n                max_speed = max(max_speed, ground_speed)\n                if last_ground_speed_timestamp is not None and is_currently_armed:\n                    ground_dt = float(timestamp) - last_ground_speed_timestamp\n                    if 0.0 < ground_dt <= 5.0:\n                        total_distance_travelled += ground_speed * ground_dt\n                curr_ground_speed = ground_speed\n                last_ground_speed_timestamp = float(timestamp)\n\n            throttle_val = row.get("throttle")\n            if valid_number(throttle_val):\n                throttle_val = max(0.0, min(100.0, float(throttle_val)))\n                max_throttle = max(max_throttle, throttle_val)\n\n'''
if marker not in text:
    raise SystemExit('MAVLINK LOOP marker not found')
text = text.replace(marker, helper + marker, 1)

old = '''        needed_messages = [\n            "HEARTBEAT", "SYS_STATUS", "VFR_HUD", "ALTITUDE",\n            "LOCAL_POSITION_NED", "GLOBAL_POSITION_INT", "RC_CHANNELS",\n            "RADIO", "RADIO_STATUS", "ATTITUDE", "VIBRATION",\n            "TEMPERATURE", "HIGHRES_IMU", "SCALED_PRESSURE",\n            "SCALED_PRESSURE2", "SCALED_PRESSURE3", "MCU_STATUS",\n            "STATUSTEXT", "ESC_TELEMETRY_1_TO_4", "PARAM_VALUE",\n        ]\n        if not efi_indexed_enabled:\n            needed_messages.append("EFI_STATUS")\n'''
new = '''        needed_messages = [\n            "HEARTBEAT", "SYS_STATUS", "ALTITUDE",\n            "LOCAL_POSITION_NED", "GLOBAL_POSITION_INT", "RC_CHANNELS",\n            "RADIO", "RADIO_STATUS", "ATTITUDE", "VIBRATION",\n            "TEMPERATURE", "HIGHRES_IMU", "SCALED_PRESSURE",\n            "SCALED_PRESSURE2", "SCALED_PRESSURE3", "MCU_STATUS",\n            "STATUSTEXT", "ESC_TELEMETRY_1_TO_4", "PARAM_VALUE",\n        ]\n        if not vfr_raw_enabled:\n            needed_messages.append("VFR_HUD")\n        if not efi_indexed_enabled:\n            needed_messages.append("EFI_STATUS")\n'''
if old not in text:
    raise SystemExit('needed_messages marker not found')
text = text.replace(old, new, 1)

old = '''            if msg is None:\n                break\n\n            message_count += 1\n'''
new = '''            if msg is None:\n                if vfr_raw_enabled:\n                    while vfr_raw_sample_index < len(vfr_raw_samples):\n                        raw_vfr_row = vfr_raw_samples[vfr_raw_sample_index]\n                        apply_raw_vfr_row(raw_vfr_row, raw_vfr_row.get("timestamp", current_timestamp))\n                        vfr_raw_sample_index += 1\n                break\n\n            message_count += 1\n'''
if old not in text:
    raise SystemExit('msg None marker not found')
text = text.replace(old, new, 1)

old = '''                if first_timestamp is None:\n                    first_timestamp = t_stamp\n\n                if efi_indexed_enabled:\n'''
new = '''                if first_timestamp is None:\n                    first_timestamp = t_stamp\n\n                if vfr_raw_enabled:\n                    while (\n                        vfr_raw_sample_index < len(vfr_raw_samples)\n                        and vfr_raw_samples[vfr_raw_sample_index].get("timestamp", 0.0) <= current_timestamp\n                    ):\n                        raw_vfr_row = vfr_raw_samples[vfr_raw_sample_index]\n                        apply_raw_vfr_row(raw_vfr_row, raw_vfr_row.get("timestamp", current_timestamp))\n                        vfr_raw_sample_index += 1\n\n                if efi_indexed_enabled:\n'''
if old not in text:
    raise SystemExit('timestamp injection marker not found')
text = text.replace(old, new, 1)

old = '''        ai_alerts.append(\n            "⚡ <b>EFI_STATUS індекс:</b> "\n'''
new = '''        ai_alerts.append(\n            "🚀 <b>VFR_HUD raw:</b> "\n            + (\n                f"увімкнено; в TLOG {_perf['vfr_raw_input_count']} повідомлень, "\n                f"raw-декодовано {_perf['vfr_raw_decoded_count']}, "\n                f"підготовка {_perf['vfr_raw_ms'] / 1000.0:.2f} с."\n                if _perf.get("vfr_raw_enabled")\n                else "недоступний — використано старий повний VFR_HUD шлях."\n            )\n        )\n\n        ai_alerts.append(\n            "⚡ <b>EFI_STATUS індекс:</b> "\n'''
if old not in text:
    raise SystemExit('EFI alert marker not found')
text = text.replace(old, new, 1)

if text == original:
    raise SystemExit('no changes applied')
path.write_text(text, encoding='utf-8')
print('Applied VFR raw fast path')
