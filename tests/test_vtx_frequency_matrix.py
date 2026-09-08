from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
BACKEND = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")


class VtxFrequencyMatrixTest(unittest.TestCase):
    def test_matrix_has_fixed_rows(self):
        self.assertIn("ВИКОРИСТАНІ VTX ЧАСТОТИ", INDEX)
        self.assertIn("'5.2':[5180,5240,5300]", INDEX)
        self.assertIn("'5.5':[5520,5580,5640]", INDEX)
        self.assertIn("'5.8':[5700,5765,5825]", INDEX)

    def test_matrix_renders_bands_as_columns_and_k_channels_as_rows(self):
        self.assertIn('class="vtx-frequency-header">5.2</div>', INDEX)
        self.assertIn('class="vtx-frequency-header">5.5</div>', INDEX)
        self.assertIn('class="vtx-frequency-header">5.8</div>', INDEX)
        self.assertIn('class="vtx-frequency-row-label">K1</div>', INDEX)
        self.assertIn('class="vtx-frequency-row-label">K2</div>', INDEX)
        self.assertIn('class="vtx-frequency-row-label">K3</div>', INDEX)
        self.assertIn("VTX_MATRIX_ROWS", INDEX)

    def test_backend_averages_all_raw_dbm_per_active_frequency(self):
        self.assertIn("vtx_dbm_stats", BACKEND)
        self.assertIn("vtx_state = get_vtx_state(ch7_current, ch8_current)", BACKEND)
        self.assertIn('bucket["sum"] += float(dbm_val)', BACKEND)
        self.assertIn('bucket["samples"] += 1', BACKEND)
        self.assertIn('"frequencyDbmStats": [', BACKEND)
        self.assertIn('"avgDbm": round(bucket["sum"] / bucket["samples"], 1)', BACKEND)

    def test_minus_128_is_included(self):
        self.assertIn("if dbm_val != 0:", BACKEND)
        self.assertNotIn("dbm_val > -128", BACKEND)
        self.assertNotIn("dbm_val != -128", BACKEND)

    def test_frontend_marks_best_green_and_worst_red(self):
        self.assertIn("video.frequencyDbmStats", INDEX)
        self.assertIn("stableFrequency", INDEX)
        self.assertIn("worstFrequency", INDEX)
        self.assertIn("vtx-frequency-best", INDEX)
        self.assertIn("vtx-frequency-worst", INDEX)
        self.assertIn("AVG ${item.avgDbm.toFixed(1)} dBm", INDEX)

    def test_unused_frequency_keeps_missing_dbm_as_null_not_zero(self):
        self.assertIn("row?.avgDbm===null||row?.avgDbm===undefined", INDEX)
        self.assertIn("item.avgDbm=hasAvg&&Number.isFinite(avg)?avg:null", INDEX)
        self.assertIn("item.dbmSamples>0&&item.avgDbm!==null", INDEX)

    def test_minus_85_is_reference_only(self):
        self.assertIn("≥ -85 dBm — норма", INDEX)
        self.assertNotIn("item.avgDbm>=VTX_STABLE_DBM_LIMIT", INDEX)


if __name__ == "__main__":
    unittest.main()
