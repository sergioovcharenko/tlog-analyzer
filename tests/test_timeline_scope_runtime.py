from pathlib import Path
import re
import subprocess
import tempfile
import unittest

HTML = Path('index.html').read_text(encoding='utf-8')


def extract_function(name):
    start = HTML.find(f'function {name}(')
    if start < 0:
        raise AssertionError(f'{name} not found')
    brace = HTML.find('{', start)
    depth = 0
    in_str = None
    esc = False
    for i in range(brace, len(HTML)):
        c = HTML[i]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == in_str:
                in_str = None
            continue
        if c in ('\"', "'", '`'):
            in_str = c
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return HTML[start:i+1]
    raise AssertionError(f'unclosed function {name}')


class TimelineScopeRuntimeTests(unittest.TestCase):
    def test_global_detectors_can_parse_timeline_time_without_renderresults_scope(self):
        detector_start = HTML.find('function detectDisarmedPhysicalMovement(')
        self.assertGreaterEqual(detector_start, 0)
        prefix = HTML[:detector_start]

        # Only a helper declared before the global detector is actually visible to it.
        helper = ''
        helper_pos = prefix.rfind('function timelineSeconds(')
        if helper_pos >= 0:
            helper = extract_function('timelineSeconds')

        detector = extract_function('detectDisarmedPhysicalMovement')
        js = helper + '\n' + detector + r'''
const out = detectDisarmedPhysicalMovement({
  flight:{flightSessionCount:0},
  timeline:[
    {eventType:'SNAPSHOT',time:'00:00.000',alt:'0.0 m',dist:'0.0 m',attitude:{roll:0,pitch:0}},
    {eventType:'SNAPSHOT',time:'00:02.000',alt:'1.0 m',dist:'3.0 m',attitude:{roll:20,pitch:0}}
  ]
});
if(!out || !Array.isArray(out.events)) process.exit(3);
'''
        with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8', delete=False) as f:
            f.write(js)
            path = f.name
        p = subprocess.run(['node', path], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, msg=(p.stderr or p.stdout))


if __name__ == '__main__':
    unittest.main()
