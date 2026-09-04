from pathlib import Path

backend_path = Path("backend/main.py")
html_path = Path("index.html")
backend = backend_path.read_text(encoding="utf-8")
html = html_path.read_text(encoding="utf-8")

# Include EFI_STATUS in both parser message filters.
old_needed = '"HEARTBEAT", "SYS_STATUS", "VFR_HUD", "ALTITUDE",'
new_needed = '"HEARTBEAT", "SYS_STATUS", "VFR_HUD", "EFI_STATUS", "ALTITUDE",'
if old_needed not in backend:
    raise SystemExit("missing needed_messages marker")
backend = backend.replace(old_needed, new_needed)

# Keep VFR_HUD.throttle only as throttle/maxThrottle telemetry; it must not feed Engine Load.
old_block = '''                # V23.6: Engine Load для Timeline.\n                # VFR_HUD.throttle у ArduPilot/MAVLink передається як 0..100 %.\n                # Зберігаємо саме поточне значення, а max_throttle лишається\n                # окремою статистикою максимального навантаження за політ.\n                throttle_val = getattr(msg, "throttle", None)\n                if valid_number(throttle_val):\n                    throttle_val = max(0.0, min(100.0, float(throttle_val)))\n                    curr_engine_load = throttle_val\n                    max_throttle = max(max_throttle, throttle_val)\n'''
new_block = '''                # VFR_HUD.throttle залишаємо лише як окрему команду throttle / maxThrottle.\n                # Це НЕ Engine Load і не повинно підміняти EFI_STATUS.engine_load.\n                throttle_val = getattr(msg, "throttle", None)\n                if valid_number(throttle_val):\n                    throttle_val = max(0.0, min(100.0, float(throttle_val)))\n                    max_throttle = max(max_throttle, throttle_val)\n'''
if old_block not in backend:
    raise SystemExit("missing VFR_HUD throttle block")
backend = backend.replace(old_block, new_block)

# Read Mission Planner-compatible Engine Load from EFI_STATUS.engine_load.
marker = '''            # ALTITUDE\n            elif msg_type == "ALTITUDE":\n'''
efi_block = '''            # EFI_STATUS — фактичний Engine Load, який показує Mission Planner.\n            elif msg_type == "EFI_STATUS":\n                engine_load_val = getattr(msg, "engine_load", None)\n                if valid_number(engine_load_val):\n                    curr_engine_load = max(0.0, min(100.0, float(engine_load_val)))\n\n            # ALTITUDE\n            elif msg_type == "ALTITUDE":\n'''
if marker not in backend:
    raise SystemExit("missing ALTITUDE marker")
backend = backend.replace(marker, efi_block)

# Update comments wherever snapshots expose engineLoad.
backend = backend.replace(
    '# V23.6: Engine Load = VFR_HUD.throttle у відсотках.',
    '# Engine Load = EFI_STATUS.engine_load у відсотках.'
)
backend = backend.replace(
    '# V23.6: поточне навантаження силової установки.\n        # Для мультикоптера беремо MAVLink VFR_HUD.throttle (0..100 %).\n        # Це командний throttle/engine load, а не CPU load з SYS_STATUS.load.',
    '# Поточний Engine Load з MAVLink EFI_STATUS.engine_load (0..100 %).\n        # VFR_HUD.throttle зберігається окремо лише як throttle/maxThrottle.'
)

# Preserve one decimal in Timeline; keypoints already interpolate exponentially from the decimal value.
if '${load.toFixed(0)}%' not in html:
    raise SystemExit("missing Engine Load render marker")
html = html.replace('${load.toFixed(0)}%', '${load.toFixed(1)}%', 1)

backend_path.write_text(backend, encoding="utf-8")
html_path.write_text(html, encoding="utf-8")
