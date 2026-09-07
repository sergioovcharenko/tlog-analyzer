from pathlib import Path

path = Path("backend/main.py")
text = path.read_text(encoding="utf-8")
original = text

if "MAVLINK_RECV_FAST_PATH_V1" in text:
    print("MAVLink recv fast path already applied")
    raise SystemExit(0)

old = '''        needed_messages = [
            "HEARTBEAT", "SYS_STATUS", "VFR_HUD", "EFI_STATUS", "ALTITUDE",
            "LOCAL_POSITION_NED", "GLOBAL_POSITION_INT", "RC_CHANNELS",
            "RADIO", "RADIO_STATUS", "ATTITUDE", "VIBRATION",
            "TEMPERATURE", "HIGHRES_IMU", "SCALED_PRESSURE",
            "SCALED_PRESSURE2", "SCALED_PRESSURE3", "MCU_STATUS",
            "STATUSTEXT", "ESC_TELEMETRY_1_TO_4", "PARAM_VALUE",
        ]
'''
new = '''        # MAVLINK_RECV_FAST_PATH_V1 — recv one decoded frame at a time and
        # filter with an O(1) set locally. This preserves pymavlink post_message
        # side effects while avoiding recv_match's repeated Python list scan.
        needed_messages = {
            "HEARTBEAT", "SYS_STATUS", "VFR_HUD", "EFI_STATUS", "ALTITUDE",
            "LOCAL_POSITION_NED", "GLOBAL_POSITION_INT", "RC_CHANNELS",
            "RADIO", "RADIO_STATUS", "ATTITUDE", "VIBRATION",
            "TEMPERATURE", "HIGHRES_IMU", "SCALED_PRESSURE",
            "SCALED_PRESSURE2", "SCALED_PRESSURE3", "MCU_STATUS",
            "STATUSTEXT", "ESC_TELEMETRY_1_TO_4", "PARAM_VALUE",
        }
'''
if old not in text:
    raise SystemExit("needed_messages marker not found")
text = text.replace(old, new, 1)

old = '''            _perf_recv_start = time.perf_counter()
            msg = mav.recv_match(type=needed_messages, blocking=False)
            _perf_recv_match_ms += (time.perf_counter() - _perf_recv_start) * 1000.0

            if msg is None:
                break

            message_count += 1
            msg_type = msg.get_type()
'''
new = '''            _perf_recv_start = time.perf_counter()
            msg = mav.recv_msg()
            _perf_recv_match_ms += (time.perf_counter() - _perf_recv_start) * 1000.0

            if msg is None:
                break

            msg_type = msg.get_type()
            if msg_type not in needed_messages:
                continue

            message_count += 1
'''
if old not in text:
    raise SystemExit("recv loop marker not found")
text = text.replace(old, new, 1)

text = text.replace(
    'f"recv_match/decode {_perf[\'recv_match_ms\'] / 1000.0:.2f} с; "',
    'f"recv_msg/decode {_perf[\'recv_match_ms\'] / 1000.0:.2f} с; "',
    1,
)

if text == original:
    raise SystemExit("no changes applied")

path.write_text(text, encoding="utf-8")
print("Applied MAVLink recv fast path")
