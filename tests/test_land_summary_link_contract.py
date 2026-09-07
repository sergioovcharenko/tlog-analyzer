from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")


class LandSummaryLinkContractTest(unittest.TestCase):
    def test_land_entry_keeps_previous_mode(self):
        self.assertIn('"modeBefore": previous_mode if previous_mode != "Невідомо" else None', BACKEND)

    def test_ai_summary_contains_clickable_land_transition(self):
        self.assertIn('if land_entries:', BACKEND)
        self.assertIn('<b>Перехід у LAND:</b>', BACKEND)
        self.assertIn('class="ai-jump" data-jump-time=', BACKEND)
        self.assertIn('Натисніть, щоб перейти до цього моменту в Timeline.', BACKEND)


if __name__ == "__main__":
    unittest.main()
