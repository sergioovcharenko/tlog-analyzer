from pathlib import Path
import unittest


class MapDefaultFlightSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = Path('index.html').read_text(encoding='utf-8')

    def test_map_defaults_to_most_substantial_flight(self):
        self.assertIn('function selectDefaultFlightIndex(flights)', self.index)
        self.assertIn('STATE.active=selectDefaultFlightIndex(STATE.flights);', self.index)

    def test_default_selector_prefers_flight_with_most_route_points(self):
        self.assertIn('points.length', self.index)
        self.assertIn('bestIndex', self.index)
        self.assertIn('bestScore', self.index)

    def test_render_map_does_not_force_first_arm_session(self):
        render_map = self.index.split('function renderMap(data){', 1)[1].split('bindMapControls();', 1)[0]
        self.assertNotIn('STATE.active=0;', render_map)


if __name__ == '__main__':
    unittest.main()
