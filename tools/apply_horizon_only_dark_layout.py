from pathlib import Path
import re

PATH = Path('index.html')
BASE_MARKER = '/* HORIZON_ONLY_DARK_V1 */'
RESTORE_MARKER = '/* RESTORE_DASHBOARD_V2_MOVE_SUMMARY_V1 */'
text = PATH.read_text(encoding='utf-8')

if RESTORE_MARKER in text:
    raise SystemExit(0)
if BASE_MARKER not in text:
    raise SystemExit('HORIZON_ONLY_DARK_V1 marker not found')

# Keep the approved dark-only horizon layout, but stop rewriting the whole DOM
# on every mutation. The summary already calls applyHorizonOnlyDarkLayout()
# after each graph-time update, so the move stays scoped to the graph dashboard.
observer_re = re.compile(
    r"\n\(function\(\)\{\n  let queued=false;.*?new MutationObserver\(schedule\)\.observe\(document\.documentElement,\{childList:true,subtree:true\}\);\n\}\)\(\);",
    re.S,
)
replacement = '\n' + RESTORE_MARKER
text, count = observer_re.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit('global horizon MutationObserver block not found')

PATH.write_text(text, encoding='utf-8')
