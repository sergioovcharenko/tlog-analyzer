from pathlib import Path
import unittest


class TimelineSpacingContractTest(unittest.TestCase):
    def test_altitude_and_distance_cells_have_readable_spacing(self):
        html = Path("index.html").read_text(encoding="utf-8")
        self.assertIn('class="tl-badge tl-altitude-cell"', html)
        self.assertIn('class="tl-badge tl-distance-cell"', html)
        self.assertIn('.tl-altitude-cell,.tl-distance-cell{white-space:nowrap}', html)
        self.assertIn('column-gap:12px', html)


if __name__ == "__main__":
    unittest.main()
