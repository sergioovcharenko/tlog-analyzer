from pathlib import Path
import re
import unittest


class TimelineAltitudeWidthContract(unittest.TestCase):
    def test_land_altitude_cell_has_enough_space_for_vertical_speed(self):
        html = Path('index.html').read_text(encoding='utf-8')

        default = re.search(
            r"\.tl-header,\.tl-item\{.*?grid-template-columns:\s*80px\s+90px\s+(\d+)px\s+(\d+)px",
            html,
            flags=re.S,
        )
        self.assertIsNotNone(default, 'default timeline grid not found')
        self.assertGreaterEqual(int(default.group(1)), 140)
        self.assertGreaterEqual(int(default.group(2)), 88)

        responsive = re.search(
            r"@media \(max-width:1550px\).*?grid-template-columns:\s*76px\s+84px\s+(\d+)px\s+(\d+)px",
            html,
            flags=re.S,
        )
        self.assertIsNotNone(responsive, 'responsive timeline grid not found')
        self.assertGreaterEqual(int(responsive.group(1)), 136)
        self.assertGreaterEqual(int(responsive.group(2)), 84)

        self.assertIn(
            '.tl-altitude-cell,.tl-distance-cell{white-space:nowrap;min-width:0}',
            html,
        )
        self.assertIn('.tl-altitude-cell{padding-right:8px}', html)


if __name__ == '__main__':
    unittest.main()
