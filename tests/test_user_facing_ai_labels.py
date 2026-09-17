from pathlib import Path
import unittest


class UserFacingAiLabelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("index.html").read_text(encoding="utf-8")
        cls.backend = Path("backend/main.py").read_text(encoding="utf-8")

    def test_user_facing_ai_branding_is_removed(self):
        required = [
            "<title>TLOG Analyzer v1.3.3 «3D Lazy FIX»</title>",
            ">🚁 TLOG ANALYZER<",
            ">ТЕХНІЧНИЙ ВИСНОВОК<",
            ">ПОГЛИБЛЕНИЙ АНАЛІЗ ПОЛЬОТУ<",
            ">🎥 ВІДЕО + TLOG<",
            "<h2>Технічний висновок</h2>",
            "результати аналізу",
        ]
        for text in required:
            self.assertIn(text, self.html)

        self.assertIn(
            "автоматичний аналіз кадрів на цьому етапі ще не виконується",
            self.html.lower(),
        )

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

    def test_user_facing_backend_warning_does_not_claim_ai(self):
        self.assertIn("Поглиблений аналіз недоступний:", self.backend)
        self.assertNotIn("Експертний AI-аналіз недоступний:", self.backend)


if __name__ == "__main__":
    unittest.main()
