from pathlib import Path
import unittest


class UserFacingAiLabelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("index.html").read_text(encoding="utf-8")

    def test_user_facing_ai_branding_is_removed(self):
        required = [
            "<title>TLOG Analyzer v1.3.3 «3D Lazy FIX»</title>",
            ">🚁 TLOG ANALYZER<",
            ">ТЕХНІЧНИЙ ВИСНОВОК<",
            ">ПОГЛИБЛЕНИЙ АНАЛІЗ ПОЛЬОТУ<",
            ">🎥 ВІДЕО + TLOG<",
            "<h2>Технічний висновок</h2>",
            "результати аналізу",
            "автоматичний аналіз кадрів на цьому етапі ще не виконується",
        ]
        for text in required:
            self.assertIn(text, self.html)

        forbidden = [
            "<title>AI — TLOG Analyzer",
            ">🚁 AI<",
            "AI ВИСНОВОК",
            "AI ЕКСПЕРТНИЙ ВИСНОВОК",
            "AI — ВІДЕО + TLOG",
            "<h2>AI-висновок</h2>",
            "не інтерпретуються AI",
        ]
        for text in forbidden:
            self.assertNotIn(text, self.html)


if __name__ == "__main__":
    unittest.main()
