import unittest

from backend.ai_expert import build_ai_expert_analysis


class AIExpertTest(unittest.TestCase):
    def test_problem_is_attributed_to_fourth_session_only(self):
        timeline = [
            {"time": "00:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "00:08.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "01:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "01:08.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "02:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "02:08.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "05:05.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "05:15.000", "eventType": "SNAPSHOT", "alt": 10.0, "dist": "40 m", "groundSpeed": 5.0},
            {"time": "07:46.000", "systemText": "EKF3 IMU0 stopped aiding"},
            {"time": "07:47.000", "systemText": "SmartRTL deactivated: bad position"},
            {"time": "08:00.000", "eventType": "SNAPSHOT", "alt": 80.0, "dist": "900 m", "groundSpeed": 10.0},
        ]
        result = build_ai_expert_analysis(
            timeline=timeline,
            radio_events=[{"time_s": 450.0, "dbm": -128, "recovered": False}],
            thrust_events=[],
            rpm_events=[],
        )
        self.assertEqual(result["primary_session_id"], 4)
        self.assertEqual(len(result["sessions"]), 4)
        self.assertTrue(all(s["overall_severity"] == "info" for s in result["sessions"][:3]))
        self.assertIn("4", result["summary"])

    def test_radio_then_ekf_is_described_as_sequence_not_cause(self):
        timeline = [
            {"time": "05:05.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "05:15.000", "eventType": "SNAPSHOT", "alt": 12.0, "dist": "30 m", "groundSpeed": 4.0},
            {"time": "07:46.000", "systemText": "EKF3 IMU0 stopped aiding"},
        ]
        result = build_ai_expert_analysis(
            timeline=timeline,
            radio_events=[{"time_s": 430.0, "dbm": -128, "recovered": False}],
            thrust_events=[],
            rpm_events=[],
        )
        session = result["sessions"][0]
        joined = " ".join(session["interpretation"]).lower()
        self.assertIn("раніше", joined)
        self.assertIn("причин", joined)
        self.assertNotIn("спричини", joined)


if __name__ == "__main__":
    unittest.main()
