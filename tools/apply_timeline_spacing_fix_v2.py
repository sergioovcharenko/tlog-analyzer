from pathlib import Path

path = Path('index.html')
text = path.read_text(encoding='utf-8')
original = text

replacements = [
    (
        """    80px\n    90px\n    100px\n    82px\n    70px\n    100px""",
        """    80px\n    90px\n    150px\n    90px\n    70px\n    100px""",
        'default timeline altitude/distance columns',
    ),
    (
        """  column-gap:12px;\n  row-gap:5px;\n  min-width:1990px""",
        """  column-gap:14px;\n  row-gap:5px;\n  min-width:2060px""",
        'default timeline spacing',
    ),
    (
        """      76px 84px 96px 78px 66px 94px 70px 64px 52px 70px 78px 160px\n      minmax(205px,1fr) minmax(215px,1fr) 290px minmax(120px,.58fr);\n    column-gap:10px;\n    row-gap:4px;\n    min-width:2050px;""",
        """      76px 84px 140px 86px 66px 94px 70px 64px 52px 70px 78px 160px\n      minmax(205px,1fr) minmax(215px,1fr) 290px minmax(120px,.58fr);\n    column-gap:12px;\n    row-gap:4px;\n    min-width:2110px;""",
        'responsive timeline spacing',
    ),
    (
        ".tl-altitude-cell,.tl-distance-cell{white-space:nowrap}",
        ".tl-altitude-cell,.tl-distance-cell{white-space:nowrap;min-width:0}\n.tl-altitude-cell{padding-right:8px}",
        'timeline cell containment',
    ),
]

for old, new, label in replacements:
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise SystemExit(f'{label} signature not found')

if text == original:
    print('Timeline spacing v2 already applied')
else:
    path.write_text(text, encoding='utf-8')
    print('Applied timeline spacing v2: LAND altitude/vertical-speed and distance are separated')
