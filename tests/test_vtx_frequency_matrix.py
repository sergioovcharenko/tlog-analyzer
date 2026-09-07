from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


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

    def test_best_stable_frequency_uses_average_dbm_and_minus_85_normal_limit(self):
        self.assertIn("VTX_STABLE_DBM_LIMIT=-85", INDEX)
        self.assertIn("dbmSum", INDEX)
        self.assertIn("dbmSamples", INDEX)
        self.assertIn("avgDbm", INDEX)
        self.assertIn("stableFrequency", INDEX)
        self.assertIn("item.avgDbm>=VTX_STABLE_DBM_LIMIT", INDEX)
        self.assertIn("vtx-frequency-best", INDEX)

    def test_minus_128_is_not_removed_from_frequency_average(self):
        self.assertNotIn("dbm>-128", INDEX)
        self.assertNotIn("dbm!==-128", INDEX)


if __name__ == "__main__":
    unittest.main()
