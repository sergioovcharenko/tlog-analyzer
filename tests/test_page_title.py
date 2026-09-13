from pathlib import Path
import unittest

INDEX = Path('index.html').read_text(encoding='utf-8')

class PageTitleTest(unittest.TestCase):
    def test_browser_title_is_clean(self):
        self.assertIn('<title>AI — TLOG Analyzer</title>', INDEX)
        self.assertNotIn('<title>AI — TLOG Analyzer v1.3.3 «3D Lazy FIX»</title>', INDEX)

if __name__ == '__main__':
    unittest.main()
