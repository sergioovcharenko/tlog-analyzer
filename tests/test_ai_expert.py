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

    def test_loiter_misuse_is_named_in_short_conclusion(self):
        timeline = [
            {"time": "00:00.000", "eventType": "FLIGHT_SESSION_START", "mode": "LOITER", "alt": 1.0, "dist": 0.0},
            {"time": "00:05.000", "eventType": "SNAPSHOT", "mode": "LOITER", "alt": 10.2, "dist": 20.0, "groundSpeed": 4.0},
            {"time": "00:10.000", "eventType": "SNAPSHOT", "mode": "LOITER", "alt": 28.0, "dist": 109.0, "groundSpeed": 7.0},
            {"time": "00:20.000", "eventType": "FLIGHT_SESSION_END", "mode": "LOITER", "alt": 0.0, "dist": 109.0},
        ]
        result = build_ai_expert_analysis(timeline=timeline, radio_events=[], thrust_events=[], rpm_events=[])
        session = result["sessions"][0]
        self.assertIn("неправильне використання", session["short_conclusion"].lower())
        self.assertIn("loiter", session["short_conclusion"].lower())
        self.assertIn("50 м", session["short_conclusion"])

    def test_short_conclusion_keeps_propulsion_problem_when_loiter_is_also_wrong(self):
        timeline = [
            {"time": "00:00.000", "eventType": "FLIGHT_SESSION_START", "mode": "LOITER", "alt": 1.0, "dist": 0.0},
            {"time": "00:05.000", "eventType": "SNAPSHOT", "mode": "LOITER", "alt": 10.2, "dist": 20.0, "groundSpeed": 4.0},
            {"time": "00:10.000", "eventType": "SNAPSHOT", "mode": "LOITER", "alt": 28.0, "dist": 109.0, "groundSpeed": 7.0},
            {"time": "00:20.000", "eventType": "FLIGHT_SESSION_END", "mode": "LOITER", "alt": 0.0, "dist": 109.0},
        ]
        rpm_events = [
            {"time_s": 8.0, "differencePct": 48.5, "drop": True, "type": "rpm_drop", "text": "RPM drop motor 4"},
        ]
        result = build_ai_expert_analysis(
            timeline=timeline,
            radio_events=[],
            thrust_events=[],
            rpm_events=rpm_events,
        )
        session = result["sessions"][0]
        conclusion = session["short_conclusion"].lower()
        self.assertIn("loiter", conclusion)
        self.assertIn("rpm", conclusion)
        self.assertIn("48.5%", session["short_conclusion"])
        self.assertIn("падіння rpm", conclusion)
        self.assertIn("причин", conclusion)


if __name__ == "__main__":
    unittest.main()
