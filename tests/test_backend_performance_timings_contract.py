from pathlib import Path
import unittest

MAIN = Path("backend/main.py").read_text(encoding="utf-8")


class BackendPerformanceTimingsContractTest(unittest.TestCase):
    def test_analyze_exposes_stage_timings(self):
        for marker in (
            '"upload_ms"',
            '"parse_rules_ms"',
            '"timeline_ms"',
            '"ai_ms"',
            '"graphs_ms"',
            '"server_total_ms"',
            '"file_size_mb"',
            '"performance": _perf',
        ):
            self.assertIn(marker, MAIN)

    def test_timing_is_visible_in_existing_ai_alerts(self):
        self.assertIn('⏱ <b>Швидкість аналізу backend:</b>', MAIN)
        self.assertIn('MAVLink/правила', MAIN)
        self.assertIn('Timeline', MAIN)
        self.assertIn('AI', MAIN)


if __name__ == "__main__":
    unittest.main()
