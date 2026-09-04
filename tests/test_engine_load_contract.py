from pathlib import Path
import unittest

BACKEND = Path("backend/main.py").read_text(encoding="utf-8")
HTML = Path("index.html").read_text(encoding="utf-8")


class EngineLoadContractTests(unittest.TestCase):
    def test_engine_load_comes_from_efi_status(self):
        self.assertIn('"EFI_STATUS"', BACKEND)
        self.assertIn('elif msg_type == "EFI_STATUS":', BACKEND)
        self.assertIn('engine_load_val = getattr(msg, "engine_load", None)', BACKEND)
        self.assertIn('curr_engine_load = max(0.0, min(100.0, float(engine_load_val)))', BACKEND)

    def test_vfr_hud_throttle_is_not_used_as_engine_load(self):
        self.assertNotIn('curr_engine_load = throttle_val', BACKEND)
        self.assertIn('max_throttle = max(max_throttle, throttle_val)', BACKEND)

    def test_timeline_keeps_one_decimal_and_existing_keypoint_curve(self):
        self.assertIn("${load.toFixed(1)}%", HTML)
        for anchor in ('[95,100]', '[96,141]', '[97,200]', '[98,252]', '[99,317]', '[100,400]'):
            self.assertIn(anchor, HTML)
        self.assertIn('Math.exp', HTML)


if __name__ == "__main__":
    unittest.main()
