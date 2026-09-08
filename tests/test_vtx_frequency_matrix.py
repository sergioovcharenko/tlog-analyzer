from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
BACKEND = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")


class VtxFrequencyMatrixTest(unittest.TestCase):
    def test_matrix_has_fixed_52_55_58_rows_and_three_channels_each(self):
        self.assertIn("ВИКОРИСТАНІ VTX ЧАСТОТИ", INDEX)
        self.assertIn("'5.2':[5180,5240,5300]", INDEX)
        self.assertIn("'5.5':[5520,5580,5640]", INDEX)
        self.assertIn("'5.8':[5700,5765,5825]", INDEX)
        self.assertIn("vtx-frequency-grid", INDEX)

    def test_cell_main_label_is_frequency_dash_count_without_switch_word(self):
        self.assertIn("${freq} — ${item.switches}", INDEX)
        self.assertNotIn("${item.frequency} MHz — ${item.switches} перемикань", INDEX)

    def test_backend_averages_every_radio_dbm_sample_by_active_vtx_frequency(self):
        self.assertIn("vtx_dbm_stats", BACKEND)
        self.assertIn("vtx_state = get_vtx_state(ch7_current, ch8_current)", BACKEND)
        self.assertIn('bucket["sum"] += float(dbm_val)', BACKEND)
        self.assertIn('bucket["samples"] += 1', BACKEND)
        self.assertIn('"frequencyDbmStats": [', BACKEND)
        self.assertIn('"avgDbm": round(bucket["sum"] / bucket["samples"], 1)', BACKEND)

    def test_minus_128_is_included_in_frequency_average(self):
        self.assertIn("if dbm_val != 0:", BACKEND)
        self.assertNotIn("dbm_val > -128", BACKEND)
        self.assertNotIn("dbm_val != -128", BACKEND)

    def test_frontend_uses_backend_average_and_marks_best_and_worst(self):
        self.assertIn("frequencyDbmStats", INDEX)
        self.assertIn("avgDbm", INDEX)
        self.assertIn("stableFrequency", INDEX)
        self.assertIn("worstFrequency", INDEX)
        self.assertIn("vtx-frequency-best", INDEX)
        self.assertIn("vtx-frequency-worst", INDEX)
        self.assertIn("AVG ${item.avgDbm.toFixed(1)} dBm", INDEX)

    def test_minus_85_is_only_a_normality_reference_not_an_average_filter(self):
        self.assertIn("VTX_NORMAL_DBM_LIMIT=-85", INDEX)
        self.assertNotIn("dbm<=VTX_NORMAL_DBM_LIMIT", INDEX)
        self.assertNotIn("dropDbmSum", INDEX)
        self.assertNotIn("avgDropDbm", INDEX)


if __name__ == "__main__":
    unittest.main()
