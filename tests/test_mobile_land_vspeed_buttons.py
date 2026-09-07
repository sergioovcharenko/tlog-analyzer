from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class MobileLandVspeedButtonsTest(unittest.TestCase):
    def test_mobile_land_speed_stacks_under_altitude(self):
        self.assertIn("MOBILE_LAND_VSPEED_BUTTONS_V1", INDEX)
        self.assertIn(".tl-altitude-cell{flex-direction:column!important", INDEX)
        self.assertIn("flex-direction:column!important;align-items:flex-start!important", INDEX)

    def test_mobile_floating_buttons_do_not_overlap(self):
        self.assertIn("#graphViewerBtn{right:12px!important;bottom:12px!important", INDEX)
        self.assertIn("#scrollTopBtn{right:12px!important;bottom:72px!important", INDEX)


if __name__ == "__main__":
    unittest.main()
