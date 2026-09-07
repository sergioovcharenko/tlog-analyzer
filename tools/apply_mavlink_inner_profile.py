from pathlib import Path

path = Path("backend/main.py")
text = path.read_text(encoding="utf-8")

if "MAVLINK_INNER_PROFILE_V1" in text:
    print("MAVLink inner profile already applied")
    raise SystemExit(0)

old = '''        while True:\n            msg = mav.recv_match(type=needed_messages, blocking=False)\n\n            if msg is None:\n                break\n\n            message_count += 1\n            msg_type = msg.get_type()\n            t_stamp = getattr(msg, "_timestamp", 0.0)'''
new = '''        # MAVLINK_INNER_PROFILE_V1 — diagnostic-only profiling of decode vs per-type rule work.\n        _perf_recv_match_ms = 0.0\n        _perf_msg_type_ms = {}\n        _perf_msg_type_count = {}\n        _perf_prev_type = None\n        _perf_prev_start = None\n\n        while True:\n            _perf_loop_now = time.perf_counter()\n            if _perf_prev_type is not None and _perf_prev_start is not None:\n                _perf_msg_type_ms[_perf_prev_type] = (\n                    _perf_msg_type_ms.get(_perf_prev_type, 0.0)\n                    + (_perf_loop_now - _perf_prev_start) * 1000.0\n                )\n                _perf_prev_type = None\n                _perf_prev_start = None\n\n            _perf_recv_start = time.perf_counter()\n            msg = mav.recv_match(type=needed_messages, blocking=False)\n            _perf_recv_match_ms += (time.perf_counter() - _perf_recv_start) * 1000.0\n\n            if msg is None:\n                break\n\n            message_count += 1\n            msg_type = msg.get_type()\n            _perf_msg_type_count[msg_type] = _perf_msg_type_count.get(msg_type, 0) + 1\n            _perf_prev_type = msg_type\n            _perf_prev_start = time.perf_counter()\n            t_stamp = getattr(msg, "_timestamp", 0.0)'''
if old not in text:
    raise SystemExit("MAVLink loop marker not found")
text = text.replace(old, new, 1)

old = '''        _perf["parse_rules_ms"] = round((time.perf_counter() - _perf_parse_start) * 1000.0, 1)\n        _perf_timeline_start = time.perf_counter()'''
new = '''        _perf["parse_rules_ms"] = round((time.perf_counter() - _perf_parse_start) * 1000.0, 1)\n        _perf["recv_match_ms"] = round(_perf_recv_match_ms, 1)\n        _perf["message_processing_ms"] = round(sum(_perf_msg_type_ms.values()), 1)\n        _perf["unattributed_parse_ms"] = round(max(\n            0.0,\n            _perf["parse_rules_ms"] - _perf["recv_match_ms"] - _perf["message_processing_ms"],\n        ), 1)\n        _perf["mavlink_profile"] = [\n            {\n                "type": msg_name,\n                "count": int(_perf_msg_type_count.get(msg_name, 0)),\n                "work_ms": round(work_ms, 1),\n                "avg_us": round(\n                    (work_ms * 1000.0) / max(1, int(_perf_msg_type_count.get(msg_name, 0))),\n                    1,\n                ),\n            }\n            for msg_name, work_ms in sorted(\n                _perf_msg_type_ms.items(),\n                key=lambda item: item[1],\n                reverse=True,\n            )[:12]\n        ]\n        _perf_timeline_start = time.perf_counter()'''
if old not in text:
    raise SystemExit("parse timing marker not found")
text = text.replace(old, new, 1)

old = '''        ai_alerts.append(\n            "⏱ <b>Швидкість аналізу backend:</b> "'''
new = '''        _perf_profile_parts = [\n            f"{item['type']} {item['work_ms'] / 1000.0:.2f} с ({item['count']})"\n            for item in _perf.get("mavlink_profile", [])[:6]\n        ]\n        ai_alerts.append(\n            "🔬 <b>MAVLink профіль:</b> "\n            f"recv_match/decode {_perf['recv_match_ms'] / 1000.0:.2f} с; "\n            f"обробка правил по повідомленнях {_perf['message_processing_ms'] / 1000.0:.2f} с; "\n            f"інше всередині parse {_perf['unattributed_parse_ms'] / 1000.0:.2f} с. "\n            + ("Найдорожчі типи: " + "; ".join(_perf_profile_parts) + "." if _perf_profile_parts else "")\n        )\n\n        ai_alerts.append(\n            "⏱ <b>Швидкість аналізу backend:</b> "'''
if old not in text:
    raise SystemExit("AI performance alert marker not found")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Applied MAVLink inner profile")
