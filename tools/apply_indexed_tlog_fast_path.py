from pathlib import Path

path = Path("backend/main.py")
text = path.read_text(encoding="utf-8")

if "INDEXED_EFI_STATUS_V1" in text:
    print("Indexed EFI_STATUS fast path already applied")
    raise SystemExit(0)

old = '''try:
    from backend.ai_reconstruction import build_ai_reconstruction, build_ai_reconstruction_facts
except ImportError:
    from ai_reconstruction import build_ai_reconstruction, build_ai_reconstruction_facts
'''
new = '''try:
    from backend.ai_reconstruction import build_ai_reconstruction, build_ai_reconstruction_facts
except ImportError:
    from ai_reconstruction import build_ai_reconstruction, build_ai_reconstruction_facts

try:
    from backend.indexed_tlog import build_indexed_numeric_series
except ImportError:
    from indexed_tlog import build_indexed_numeric_series
'''
if old not in text:
    raise SystemExit("AI import marker not found")
text = text.replace(old, new, 1)

old = '''    try:
        mav = mavutil.mavlink_connection(temp.name)

        # Base
'''
new = '''    try:
        mav = mavutil.mavlink_connection(temp.name)

        # INDEXED_EFI_STATUS_V1 — use pymavlink's mmap offset index to decode
        # at most one EFI_STATUS sample per 200 ms bucket. If indexing is not
        # available, the main recv_match loop automatically keeps EFI_STATUS.
        _efi_index_start = time.perf_counter()
        efi_indexed = build_indexed_numeric_series(
            temp.name, "EFI_STATUS", "engine_load", interval_s=0.2
        )
        _perf["efi_index_ms"] = round((time.perf_counter() - _efi_index_start) * 1000.0, 1)
        efi_indexed_enabled = efi_indexed is not None
        efi_engine_load_samples = list((efi_indexed or {}).get("samples", []))
        efi_sample_index = 0
        _perf["efi_indexed_enabled"] = bool(efi_indexed_enabled)
        _perf["efi_indexed_input_count"] = int((efi_indexed or {}).get("input_count", 0))
        _perf["efi_indexed_decoded_count"] = int((efi_indexed or {}).get("decoded_count", 0))

        # Base
'''
if old not in text:
    raise SystemExit("mav connection marker not found")
text = text.replace(old, new, 1)

old = '''        needed_messages = [
            "HEARTBEAT", "SYS_STATUS", "VFR_HUD", "EFI_STATUS", "ALTITUDE",
            "LOCAL_POSITION_NED", "GLOBAL_POSITION_INT", "RC_CHANNELS",
            "RADIO", "RADIO_STATUS", "ATTITUDE", "VIBRATION",
            "TEMPERATURE", "HIGHRES_IMU", "SCALED_PRESSURE",
            "SCALED_PRESSURE2", "SCALED_PRESSURE3", "MCU_STATUS",
            "STATUSTEXT", "ESC_TELEMETRY_1_TO_4", "PARAM_VALUE",
        ]
'''
new = '''        needed_messages = [
            "HEARTBEAT", "SYS_STATUS", "VFR_HUD", "ALTITUDE",
            "LOCAL_POSITION_NED", "GLOBAL_POSITION_INT", "RC_CHANNELS",
            "RADIO", "RADIO_STATUS", "ATTITUDE", "VIBRATION",
            "TEMPERATURE", "HIGHRES_IMU", "SCALED_PRESSURE",
            "SCALED_PRESSURE2", "SCALED_PRESSURE3", "MCU_STATUS",
            "STATUSTEXT", "ESC_TELEMETRY_1_TO_4", "PARAM_VALUE",
        ]
        if not efi_indexed_enabled:
            needed_messages.append("EFI_STATUS")
'''
if old not in text:
    raise SystemExit("needed_messages marker not found")
text = text.replace(old, new, 1)

old = '''            if t_stamp > 0:
                current_timestamp = t_stamp

                if first_timestamp is None:
                    first_timestamp = t_stamp

                # 1 Hz telemetry timeline while ARMED.
'''
new = '''            if t_stamp > 0:
                current_timestamp = t_stamp

                if first_timestamp is None:
                    first_timestamp = t_stamp

                if efi_indexed_enabled:
                    while (
                        efi_sample_index < len(efi_engine_load_samples)
                        and efi_engine_load_samples[efi_sample_index][0] <= current_timestamp
                    ):
                        indexed_engine_load = efi_engine_load_samples[efi_sample_index][1]
                        if valid_number(indexed_engine_load):
                            curr_engine_load = max(0.0, min(100.0, float(indexed_engine_load)))
                        efi_sample_index += 1

                # 1 Hz telemetry timeline while ARMED.
'''
if old not in text:
    raise SystemExit("timestamp marker not found")
text = text.replace(old, new, 1)

old = '''        ai_alerts.append(
            "🔬 <b>MAVLink профіль:</b> "
'''
new = '''        ai_alerts.append(
            "⚡ <b>EFI_STATUS індекс:</b> "
            + (
                f"увімкнено; в TLOG {_perf['efi_indexed_input_count']} повідомлень, "
                f"декодовано {_perf['efi_indexed_decoded_count']} (5 Гц), "
                f"підготовка {_perf['efi_index_ms'] / 1000.0:.2f} с."
                if _perf.get("efi_indexed_enabled")
                else "недоступний — використано повний сумісний EFI_STATUS шлях."
            )
        )

        ai_alerts.append(
            "🔬 <b>MAVLink профіль:</b> "
'''
if old not in text:
    raise SystemExit("profile alert marker not found")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Applied indexed EFI_STATUS fast path")
