import unittest

from backend.ai_expert_modules import analyze_radio, analyze_navigation, analyze_termination


class AIExpertModuleTest(unittest.TestCase):
    def setUp(self):
        self.session = {
            "session_id": 4,
            "start_s": 300.0,
            "end_s": 600.0,
            "classification": "flight",
            "rows": [],
        }

    def test_twenty_repeated_radio_gaps_do_not_count_as_twenty_independent_sources(self):
        events = [{"time_s": 400.0 + i, "dbm": -128, "recovered": True} for i in range(20)]
        result = analyze_radio(self.session, events)
        self.assertIn("mavlink_gap", result["source_classes"])
        self.assertLessEqual(len(result["source_classes"]), 3)
        self.assertLess(result["confidence"], 0.90)

    def test_independent_radio_sources_raise_confidence(self):
        events = [
            {"time_s": 420.0, "dbm": -128, "recovered": False},
            {"time_s": 430.0, "type": "failsafe", "text": "Radio failsafe"},
        ]
        result = analyze_radio(self.session, events)
        self.assertGreaterEqual(len(result["source_classes"]), 3)
        self.assertGreaterEqual(result["confidence"], 0.85)

    def test_navigation_message_is_reported_without_radio_causality(self):
        self.session["rows"] = [
            {"time": "07:46.000", "systemText": "EKF3 IMU0 stopped aiding"},
            {"time": "07:47.000", "systemText": "SmartRTL deactivated: bad position"},
        ]
        result = analyze_navigation(self.session)
        joined = " ".join(result["evidence"]).lower()
        self.assertIn("stopped aiding", joined)
        self.assertIn("bad position", joined)
        self.assertNotIn("через раді", joined)

    def test_ended_armed_never_claims_crash(self):
        self.session["ended_by_log"] = True
        self.session["ended_with_disarm"] = False
        result = analyze_termination(self.session)
        joined = " ".join(result["evidence"] + result["counter_evidence"]).lower()
        self.assertIn("armed", joined)
        self.assertNotIn("авар", joined)
        self.assertNotIn("crash", joined)


if __name__ == "__main__":
    unittest.main()
