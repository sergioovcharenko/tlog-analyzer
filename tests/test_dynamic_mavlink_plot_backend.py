import math
import unittest
from pathlib import Path

from backend.mavlink_plot import MavlinkPlotCollector, build_board_messages


class DynamicMavlinkPlotBackendTest(unittest.TestCase):
    def test_collects_numeric_scalars_and_skips_non_numeric_payloads(self):
        c = MavlinkPlotCollector(max_points_per_series=10)
        c.add("ATTITUDE", {"roll": 0.25, "pitch": -0.1, "name": "x", "payload": [1, 2]}, 101.0)
        out = c.build(100.0)
        self.assertIn("ATTITUDE", out["groups"])
        self.assertIn("roll", out["groups"]["ATTITUDE"])
        self.assertNotIn("name", out["groups"]["ATTITUDE"])
        self.assertNotIn("payload", out["groups"]["ATTITUDE"])
        self.assertEqual(out["groups"]["ATTITUDE"]["roll"]["time_ms"], [1000])

    def test_rejects_nan_and_inf(self):
        c = MavlinkPlotCollector()
        c.add("TEST", {"a": math.nan, "b": math.inf, "c": 4.0}, 1.0)
        out = c.build(0.0)
        self.assertEqual(set(out["groups"]["TEST"]), {"c"})

    def test_downsampling_caps_points_and_preserves_endpoints(self):
        c = MavlinkPlotCollector(max_points_per_series=5)
        for i in range(20):
            c.add("VFR_HUD", {"alt": float(i)}, float(i))
        s = c.build(0.0)["groups"]["VFR_HUD"]["alt"]
        self.assertLessEqual(len(s["values"]), 5)
        self.assertEqual(s["values"][0], 0.0)
        self.assertEqual(s["values"][-1], 19.0)

    def test_streaming_collector_bounds_memory_before_build(self):
        limit = 64
        c = MavlinkPlotCollector(max_points_per_series=limit)
        for i in range(20000):
            c.add("HIGH_RATE", {"value": float(i)}, float(i) / 100.0)
        bucket = c._series[("HIGH_RATE", "value")]
        self.assertLessEqual(len(bucket["values"]), limit * 2)
        self.assertLessEqual(len(bucket["timestamps"]), limit * 2)
        out = c.build(0.0)["groups"]["HIGH_RATE"]["value"]
        self.assertLessEqual(len(out["values"]), limit)
        self.assertEqual(out["values"][0], 0.0)
        self.assertEqual(out["values"][-1], 19999.0)

    def test_board_messages_use_elapsed_time_and_severity(self):
        rows = [
            {"timestamp": 102.0, "eventType": "SYSTEM", "system_text": "EKF variance", "severity": 3},
            {"timestamp": 108.0, "eventType": "SYSTEM", "system_text": "GPS OK", "severity": 6},
        ]
        msgs = build_board_messages(rows, 100.0)
        self.assertEqual(msgs[0]["time_ms"], 2000)
        self.assertEqual(msgs[0]["level"], "error")
        self.assertEqual(msgs[1]["level"], "info")

    def test_board_messages_only_include_raw_board_statustext(self):
        rows = [
            {"timestamp": 101.0, "eventType": "SYSTEM", "system_text": "EKF variance", "analysis_text": "synthetic duplicate", "severity": 3},
            {"timestamp": 102.0, "eventType": "ANALYSIS", "analysis_text": "Calculated antenna warning", "isError": True},
            {"timestamp": 103.0, "eventType": "SYSTEM", "system_text": "Battery failsafe", "severity": 2},
        ]
        msgs = build_board_messages(rows, 100.0)
        self.assertEqual([m["text"] for m in msgs], ["EKF variance", "Battery failsafe"])
        self.assertTrue(all(m.get("source") == "board" for m in msgs))

    def test_main_will_emit_dynamic_plot_structures(self):
        main_text = Path("backend/main.py").read_text(encoding="utf-8")
        self.assertIn("MavlinkPlotCollector", main_text)
        self.assertIn('"mavlink_plot"', main_text)
        self.assertIn('"board_messages"', main_text)


if __name__ == "__main__":
    unittest.main()
