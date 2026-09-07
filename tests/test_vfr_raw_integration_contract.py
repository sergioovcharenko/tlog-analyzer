from pathlib import Path
import unittest


class VfrRawIntegrationContractTest(unittest.TestCase):
    def test_main_uses_raw_vfr_with_full_fallback(self):
        text = Path('backend/main.py').read_text(encoding='utf-8')
        self.assertIn('VFR_RAW_FAST_PATH_V1', text)
        self.assertIn('build_raw_vfr_hud_series_from_reader', text)
        self.assertIn('if not vfr_raw_enabled:', text)
        self.assertIn('needed_messages.append("VFR_HUD")', text)
        self.assertIn('elif msg_type == "VFR_HUD":', text)
        self.assertIn('vfr_raw_input_count', text)
        self.assertIn('VFR_HUD raw', text)


if __name__ == '__main__':
    unittest.main()
