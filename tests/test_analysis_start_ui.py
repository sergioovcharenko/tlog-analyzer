from pathlib import Path
import unittest


class AnalysisStartUiContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path('index.html').read_text(encoding='utf-8')

    def test_browser_title_is_plain(self):
        self.assertIn('<title>TLOG Analyzer</title>', self.html)
        self.assertNotIn('<title>TLOG Analyzer v', self.html)

    def test_analysis_wait_overlay_is_removed(self):
        forbidden = [
            'temporaryAnalysisWaitOverlay',
            'ensureTemporaryAnalysisWaitOverlay',
            'showTemporaryAnalysisWaitOverlay',
            'hideTemporaryAnalysisWaitOverlay',
            'НЕ ТОРОПИСЬ!',
            'TLOG аналізується…',
        ]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, self.html)


if __name__ == '__main__':
    unittest.main()
