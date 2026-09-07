from pathlib import Path

path = Path("index.html")
text = path.read_text(encoding="utf-8")
original = text

old_grid = """    80px\n    90px\n    70px\n    76px\n    70px\n    100px"""
new_grid = """    80px\n    90px\n    100px\n    82px\n    70px\n    100px"""
if old_grid not in text:
    raise SystemExit("default timeline grid signature not found")
text = text.replace(old_grid, new_grid, 1)

old_gap = """  gap:5px;\n  min-width:1940px"""
new_gap = """  column-gap:12px;\n  row-gap:5px;\n  min-width:1990px"""
if old_gap not in text:
    raise SystemExit("default timeline gap signature not found")
text = text.replace(old_gap, new_gap, 1)

old_responsive = """      76px 84px 66px 70px 66px 94px 70px 64px 52px 70px 78px 160px\n      minmax(205px,1fr) minmax(215px,1fr) 290px minmax(120px,.58fr);\n    gap:4px;\n    min-width:2010px;"""
new_responsive = """      76px 84px 96px 78px 66px 94px 70px 64px 52px 70px 78px 160px\n      minmax(205px,1fr) minmax(215px,1fr) 290px minmax(120px,.58fr);\n    column-gap:10px;\n    row-gap:4px;\n    min-width:2050px;"""
if old_responsive not in text:
    raise SystemExit("responsive timeline grid signature not found")
text = text.replace(old_responsive, new_responsive, 1)

old_cells = """.tl-time{color:var(--accent);font-family:monospace;font-weight:700}\n.tl-mode{color:var(--accent);font-weight:600}\n.tl-badge{font-family:monospace;font-weight:600}"""
new_cells = """.tl-time{color:var(--accent);font-family:monospace;font-weight:700}\n.tl-mode{color:var(--accent);font-weight:600}\n.tl-badge{font-family:monospace;font-weight:600}\n.tl-altitude-cell,.tl-distance-cell{white-space:nowrap}"""
if old_cells not in text:
    raise SystemExit("timeline badge style signature not found")
text = text.replace(old_cells, new_cells, 1)

old_distance = """        <div class=\"tl-badge tl-altitude-cell\">${item.alt||'—'}${landVerticalSpeed}</div>\n        <div class=\"tl-badge\">${item.dist||'—'}</div>"""
new_distance = """        <div class=\"tl-badge tl-altitude-cell\">${item.alt||'—'}${landVerticalSpeed}</div>\n        <div class=\"tl-badge tl-distance-cell\">${item.dist||'—'}</div>"""
if old_distance not in text:
    raise SystemExit("timeline altitude/distance markup signature not found")
text = text.replace(old_distance, new_distance, 1)

if text == original:
    raise SystemExit("no changes applied")

path.write_text(text, encoding="utf-8")
print("Applied timeline altitude/distance spacing fix")
