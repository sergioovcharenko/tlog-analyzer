from pathlib import Path
import unittest


class AnalysisWaitOverlayContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path('index.html').read_text(encoding='utf-8')

    def test_wait_overlay_has_no_external_image(self):
        self.assertNotIn('TEMP_WAIT_IMAGE', self.html)
        self.assertNotIn('https://i.imgur.com/CduyK.jpeg', self.html)
        self.assertNotIn("document.createElement('img')", self.html)
        self.assertNotIn('card.append(img,title,subtitle)', self.html)

    def test_wait_overlay_keeps_text_status(self):
        self.assertIn("title.textContent='НЕ ТОРОПИСЬ!'", self.html)
        self.assertIn("subtitle.textContent='TLOG аналізується…'", self.html)
        self.assertIn('card.append(title,subtitle)', self.html)


if __name__ == '__main__':
    unittest.main()
