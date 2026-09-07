from pathlib import Path

MAIN = Path("backend/main.py")
text = MAIN.read_text(encoding="utf-8")

old_signature = '''        def add_event(
            text,
            t_stamp,
            mode,
            is_error=False,
            is_pilot_action=False,
            event_type="SYSTEM",
        ):'''
new_signature = '''        def add_event(
            text,
            t_stamp,
            mode,
            is_error=False,
            is_pilot_action=False,
            event_type="SYSTEM",
            severity=None,
        ):'''

if new_signature not in text:
    if old_signature not in text:
        raise SystemExit("add_event signature anchor not found")
    text = text.replace(old_signature, new_signature, 1)

old_tail = '''                    "eventType": event_type,
                    "isError": is_error,
                }
            )'''
new_tail = '''                    "eventType": event_type,
                    "isError": is_error,
                    "severity": severity,
                }
            )'''

if new_tail not in text:
    if old_tail not in text:
        raise SystemExit("add_event event tail anchor not found")
    text = text.replace(old_tail, new_tail, 1)

MAIN.write_text(text, encoding="utf-8")
print("STATUSTEXT severity passthrough applied")
