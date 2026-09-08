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

    def test_frequency_stability_uses_only_drop_zone_from_minus_85_to_minus_128(self):
        self.assertIn("VTX_NORMAL_DBM_LIMIT=-85", INDEX)
        self.assertIn("VTX_MIN_DBM=-128", INDEX)
        self.assertIn("dropDbmSum", INDEX)
        self.assertIn("dropDbmSamples", INDEX)
        self.assertIn("avgDropDbm", INDEX)
        self.assertIn("dbm<=VTX_NORMAL_DBM_LIMIT&&dbm>=VTX_MIN_DBM", INDEX)
        self.assertIn("stableFrequency", INDEX)
        self.assertIn("vtx-frequency-best", INDEX)

    def test_good_dbm_values_do_not_pull_drop_average_up(self):
        self.assertNotIn("item.dbmSum+=dbm", INDEX)
        self.assertIn("item.dropDbmSum+=dbm", INDEX)
        self.assertIn("AVG ПРОСІДАННЯ", INDEX)

    def test_minus_128_is_included_in_drop_average(self):
        self.assertIn("dbm>=VTX_MIN_DBM", INDEX)
        self.assertNotIn("dbm>-128", INDEX)
        self.assertNotIn("dbm!==-128", INDEX)


if __name__ == "__main__":
    unittest.main()
