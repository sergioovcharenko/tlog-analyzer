from pathlib import Path
import re

path = Path('index.html')
text = path.read_text(encoding='utf-8')
original = text

text, title_count = re.subn(
    r'<title>TLOG Analyzer[^<]*</title>',
    '<title>TLOG Analyzer</title>',
    text,
    count=1,
)
if title_count != 1:
    raise SystemExit('Expected exactly one TLOG Analyzer title')

pattern = re.compile(
    r"\n<script>\s*\(function\(\)\{\s*function ensureTemporaryAnalysisWaitOverlay\(\)\{.*?</script>\s*<!-- TEMP_ANALYSIS_WAIT_OVERLAY_END -->",
    re.S,
)
text, overlay_count = pattern.subn(
    '\n<!-- TEMP_ANALYSIS_WAIT_OVERLAY_END -->',
    text,
    count=1,
)
if overlay_count != 1 and 'temporaryAnalysisWaitOverlay' in text:
    raise SystemExit('Could not remove the analysis wait overlay script safely')

if text == original:
    print('No analysis-start UI changes needed')
else:
    path.write_text(text, encoding='utf-8')
    print('Applied simple browser title and removed analysis wait overlay')
