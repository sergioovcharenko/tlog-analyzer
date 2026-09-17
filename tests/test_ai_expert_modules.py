import unittest

from backend.ai_expert_modules import analyze_radio, analyze_navigation, analyze_termination, analyze_control_modes


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

    def test_loiter_takeoff_horizontal_motion_below_50m_is_reported(self):
        self.session["rows"] = [
            {"time": "00:01.000", "mode": "LOITER", "alt": 1.0, "distance": 0.0},
            {"time": "00:05.000", "mode": "LOITER", "alt": 10.2, "distance": 20.0},
            {"time": "00:10.000", "mode": "LOITER", "alt": 25.0, "distance": 89.0},
            {"time": "00:12.000", "mode": "LOITER", "alt": 28.0, "distance": 109.0},
        ]
        result = analyze_control_modes(self.session)
        joined = " ".join(result["evidence"])
        self.assertIn("loiter_vertical_takeoff", result["source_classes"])
        self.assertIn("неправильне використання", joined.lower())
        self.assertIn("10.2 м", joined)
        self.assertIn("20.0 м", joined)
        self.assertIn("50 м", joined)

    def test_loiter_descent_below_50m_with_horizontal_motion_is_reported(self):
        self.session["rows"] = [
            {"time": "01:00.000", "mode": "LOITER", "alt": 70.0, "distance": 120.0},
            {"time": "01:10.000", "mode": "LOITER", "alt": 50.0, "distance": 120.0},
            {"time": "01:15.000", "mode": "LOITER", "alt": 35.0, "distance": 136.0},
            {"time": "01:20.000", "mode": "LOITER", "alt": 10.0, "distance": 145.0},
        ]
        result = analyze_control_modes(self.session)
        joined = " ".join(result["evidence"])
        self.assertIn("loiter_vertical_landing", result["source_classes"])
        self.assertIn("35.0 м", joined)
        self.assertIn("16.0 м", joined)
        self.assertIn("вертикально", joined.lower())


if __name__ == "__main__":
    unittest.main()
