from pathlib import Path

p = Path("backend/main.py")
s = p.read_text(encoding="utf-8")

old_map = '''TX16_SWITCH_CHANNELS = {\n    "SH": 6,\n    "SC": 7,\n    "SD": 8,\n    "SF": 10,\n}\n'''
new_map = '''TX16_SWITCH_CHANNELS = {\n    "SH": 6,\n    "SA": 7,\n    "SB": 8,\n    "SF": 10,\n    "SD": 13,\n    "SC": 15,\n}\n'''
if old_map not in s:
    raise SystemExit("old TX16_SWITCH_CHANNELS mapping not found")
s = s.replace(old_map, new_map, 1)

old_state = '    if name in ("SC", "SD"):\n'
new_state = '    if name in ("SA", "SB", "SC", "SD"):\n'
if old_state not in s:
    raise SystemExit("old three-position TX16 state condition not found")
s = s.replace(old_state, new_state, 1)

# Update the explanatory comment so future edits do not restore the obsolete mapping.
s = s.replace(
    '# V23.9: explicitly track SC / SD / SF / SH by interpreted state,',
    '# TX16: track SA / SB / SC / SD / SF / SH by interpreted state,',
    1,
)
s = s.replace(
    '# not merely by a >250 us raw jump. This fixes missed SF (CH10)\n                # transitions and makes SC/SD changes visible by switch name.',
    '# not merely by a >250 us raw jump. SA/SB are VTX selectors;\n                # SC/SD are safety selectors and SF/SH are activators.',
    1,
)

p.write_text(s, encoding="utf-8")
print("backend TX16 mapping patched")
