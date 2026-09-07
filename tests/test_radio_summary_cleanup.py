from pathlib import Path
import unittest

HTML = Path('index.html').read_text(encoding='utf-8')
BACKEND = Path('backend/main.py').read_text(encoding='utf-8')


class RadioSummaryCleanupTests(unittest.TestCase):
    def test_backend_exposes_average_dbm_including_minus_128(self):
        self.assertIn('dbm_sum = 0.0', BACKEND)
        self.assertIn('dbm_sample_count = 0', BACKEND)
        self.assertIn('dbm_sum += float(dbm_val)', BACKEND)
        self.assertIn('"avgDbm":', BACKEND)
        self.assertIn('"worstDbm":', BACKEND)
        self.assertIn('"dbmSampleCount":', BACKEND)

    def test_health_cards_show_min_rssi_and_worst_plus_average_dbm(self):
        self.assertIn("createCard('MIN RSSI'", HTML)
        self.assertIn('MAX ${data.radio.worstDbm} dBm', HTML)
        self.assertIn('Середнє: ${data.radio.avgDbm.toFixed(1)} dBm', HTML)
        self.assertIn('включно з -128', HTML)

    def test_redundant_vtx_cards_are_removed(self):
        for old in (
            "createCard('Діапазон CH7'",
            "createCard('Канал CH8'",
            "createCard('CH7 PWM'",
            "createCard('CH8 PWM'",
        ):
            self.assertNotIn(old, HTML)
        self.assertIn("'VTX / Відеочастота'", HTML)
        self.assertIn("createCard('Змін VTX'", HTML)


if __name__ == '__main__':
    unittest.main()
