from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class DashboardSummaryVtxEngineTest(unittest.TestCase):
    def test_engine_load_card_shows_average_for_flight(self):
        self.assertIn("function summarizeEngineLoad", INDEX)
        self.assertIn("СЕРЕДНЄ ЗА ПОЛІТ", INDEX)
        self.assertIn("Engine Load", INDEX)

    def test_radio_card_prioritizes_average_and_keeps_worst_value(self):
        self.assertIn("СЕРЕДНЄ", INDEX)
        self.assertIn("Найгірше:", INDEX)
        self.assertIn("data.radio?.avgDbm", INDEX)
        self.assertIn("data.radio?.worstDbm", INDEX)

    def test_vtx_card_lists_detected_frequencies_and_selection_counts(self):
        self.assertIn("function summarizeVtxFrequencySelections", INDEX)
        self.assertIn("ВІДЕОЧАСТОТИ ЗА ПОЛІТ", INDEX)
        self.assertIn("перемикан", INDEX)
        self.assertNotIn("createCard('VTX відеочастота'", INDEX)


if __name__ == "__main__":
    unittest.main()
