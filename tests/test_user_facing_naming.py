from pathlib import Path
import unittest

# Contract: visible product/report copy must not present the analyzer as AI.


class UserFacingNamingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("index.html").read_text(encoding="utf-8")

    def test_ai_branding_is_removed_from_visible_ui_and_report_copy(self):
        old_visible_labels = [
            "<title>AI — TLOG Analyzer",
            "<h1>🚁 AI</h1>",
            "🤖 AI ВИСНОВОК",
            "🧠 AI ЕКСПЕРТНИЙ ВИСНОВОК",
            "🎥 AI — ВІДЕО + TLOG",
            "AI-висновок у цьому аналізі відсутній.",
            "<h2>AI-висновок</h2>",
            "кадри ще не інтерпретуються AI",
            "AI-висновки або будь-які розрахунки",
        ]
        for label in old_visible_labels:
            with self.subTest(label=label):
                self.assertNotIn(label, self.html)

    def test_new_product_and_analysis_labels_are_present(self):
        expected = [
            "<title>TLOG Analyzer",
            "<h1>🚁 TLOG ANALYZER</h1>",
            "ТЕХНІЧНИЙ ВИСНОВОК",
            "ПОГЛИБЛЕНИЙ АНАЛІЗ ПОЛЬОТУ",
            "🎥 ВІДЕО + TLOG",
            "Технічний висновок у цьому аналізі відсутній.",
            "<h2>Технічний висновок</h2>",
            "автоматичний аналіз кадрів на цьому етапі ще не виконується",
            "результати аналізу або будь-які розрахунки",
        ]
        for label in expected:
            with self.subTest(label=label):
                self.assertIn(label, self.html)


if __name__ == "__main__":
    unittest.main()
