from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend" / "main.py"
MARKER = "# LAND_SUMMARY_LINK_V1"

text = BACKEND.read_text(encoding="utf-8")
if MARKER in text:
    print("LAND summary link already applied")
    raise SystemExit(0)

mode_anchor = '''                    if new_mode and new_mode != current_mode:\n                        if current_mode != "Невідомо":\n'''
mode_replacement = '''                    if new_mode and new_mode != current_mode:\n                        previous_mode = current_mode\n                        if current_mode != "Невідомо":\n'''
if mode_anchor not in text:
    raise SystemExit("mode transition anchor not found")
text = text.replace(mode_anchor, mode_replacement, 1)

land_anchor = '''                        if current_mode == "LAND":\n                            land_mode_triggered = True\n                            active_land_entry = {\n                                "timestamp": current_timestamp,\n                                "altitude": float(curr_alt) if valid_number(curr_alt) else None,\n                                "modeBefore": None,\n                            }\n                            land_entries.append(active_land_entry)\n'''
land_replacement = '''                        if current_mode == "LAND":\n                            land_mode_triggered = True\n                            active_land_entry = {\n                                "timestamp": current_timestamp,\n                                "altitude": float(curr_alt) if valid_number(curr_alt) else None,\n                                "modeBefore": previous_mode if previous_mode != "Невідомо" else None,\n                            }\n                            land_entries.append(active_land_entry)\n'''
if land_anchor not in text:
    raise SystemExit("LAND entry anchor not found")
text = text.replace(land_anchor, land_replacement, 1)

ai_anchor = '''        # Завершення польоту / LAND -> automatic DISARM\n'''
ai_block = '''        # LAND_SUMMARY_LINK_V1 — show every detected transition into LAND in the AI conclusion.\n        # The first transition is clickable through the same Timeline jump mechanism\n        # already used by the other diagnostic alerts.\n        if land_entries:\n            first_land = land_entries[0]\n            first_land_time = format_timeline_time(first_land.get("timestamp"), base_t)\n            first_land_from = first_land.get("modeBefore")\n\n            if len(land_entries) == 1:\n                if first_land_from:\n                    land_transition_text = f"{first_land_from} → LAND о {first_land_time}"\n                else:\n                    land_transition_text = f"LAND о {first_land_time}"\n            else:\n                last_land = land_entries[-1]\n                last_land_time = format_timeline_time(last_land.get("timestamp"), base_t)\n                first_label = (\n                    f"{first_land_from} → LAND о {first_land_time}"\n                    if first_land_from\n                    else f"перший LAND о {first_land_time}"\n                )\n                land_transition_text = (\n                    f"зафіксовано {len(land_entries)} переходи; "\n                    f"{first_label}; останній LAND о {last_land_time}"\n                )\n\n            ai_alerts.append(\n                f'<span class="ai-jump" data-jump-time="{first_land_time}">'\n                f"🛬 <b>Перехід у LAND:</b> {land_transition_text}. "\n                "Натисніть, щоб перейти до цього моменту в Timeline.</span>"\n            )\n\n'''
if ai_anchor not in text:
    raise SystemExit("AI LAND summary anchor not found")
text = text.replace(ai_anchor, ai_block + ai_anchor, 1)

BACKEND.write_text(text, encoding="utf-8")
print("Applied clickable LAND summary link")
