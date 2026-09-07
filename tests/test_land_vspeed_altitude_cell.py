from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class LandVerticalSpeedAltitudeCellTest(unittest.TestCase):
    def test_land_vertical_speed_is_rendered_next_to_altitude(self):
        self.assertIn("LAND_VSPEED_ALTITUDE_CELL_V1", INDEX)
        self.assertIn("class=\"land-vspeed-inline\"", INDEX)
        self.assertIn("${item.alt||'—'}${landVerticalSpeed}", INDEX)

    def test_land_vertical_speed_is_not_rendered_in_system_message_cell(self):
        self.assertNotIn("<div class=\"esc-no-data\">Vz↓:", INDEX)


if __name__ == "__main__":
    unittest.main()
