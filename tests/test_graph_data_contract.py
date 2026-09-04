import math
import unittest

from backend.main import _build_graph_data


class GraphDataContractTest(unittest.TestCase):
    def test_build_graph_data_from_timeline_and_attitude(self):
        timeline = [
            {
                "time": "00:01.000",
                "eventType": "SNAPSHOT",
                "alt": "12.3 м",
                "volt": 24.2,
                "curr": 18.5,
                "engineLoad": 42.0,
                "dbm": -77,
                "verticalSpeedDown": -0.4,
                "rcChannels": {"ch1": 1510},
                "esc": [{"id": 1, "rpm": 4200, "current": 12.4}],
            }
        ]
        attitude = [
            {"timestamp": 101.0, "roll": math.pi / 2, "pitch": -math.pi / 4, "yaw": math.pi}
        ]
        graph = _build_graph_data(timeline, attitude, 100.0)

        self.assertEqual(graph["altitude_time_ms"], [1000])
        self.assertEqual(graph["altitude_m"], [12.3])
        self.assertEqual(graph["voltage_v"], [24.2])
        self.assertEqual(graph["current_a"], [18.5])
        self.assertEqual(graph["engine_load_pct"], [42.0])
        self.assertEqual(graph["radio_dbm"], [-77.0])
        self.assertEqual(graph["rc_ch1_pwm"], [1510.0])
        self.assertEqual(graph["esc1_rpm"], [4200.0])
        self.assertEqual(graph["attitude_time_ms"], [1000])
        self.assertAlmostEqual(graph["roll_deg"][0], 90.0, places=5)
        self.assertAlmostEqual(graph["pitch_deg"][0], -45.0, places=5)
        self.assertAlmostEqual(graph["yaw_deg"][0], 180.0, places=5)

    def test_missing_or_invalid_values_are_omitted(self):
        graph = _build_graph_data(
            [{"time": "00:00.000", "eventType": "SNAPSHOT", "volt": None, "curr": float("nan")}],
            [],
            0.0,
        )
        self.assertNotIn("voltage_v", graph)
        self.assertNotIn("current_a", graph)
        self.assertNotIn("attitude_time_ms", graph)


if __name__ == "__main__":
    unittest.main()
