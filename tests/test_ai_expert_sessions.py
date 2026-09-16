import unittest

from backend.ai_expert_sessions import segment_arm_sessions


class AIExpertSessionTest(unittest.TestCase):
    def test_three_short_checks_and_one_real_flight_are_separated(self):
        timeline = [
            {"time": "00:01.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "00:05.000", "eventType": "SNAPSHOT", "alt": 0.2, "dist": "1 m", "groundSpeed": 0.1},
            {"time": "00:08.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "01:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "01:05.000", "eventType": "SNAPSHOT", "alt": 0.3, "dist": "2 m", "groundSpeed": 0.2},
            {"time": "01:09.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "02:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "02:06.000", "eventType": "SNAPSHOT", "alt": 0.4, "dist": "1 m", "groundSpeed": 0.2},
            {"time": "02:10.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "05:05.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "05:12.000", "eventType": "SNAPSHOT", "alt": 4.0, "dist": "25 m", "groundSpeed": 4.2},
            {"time": "07:00.000", "eventType": "SNAPSHOT", "alt": 100.0, "dist": "900 m", "groundSpeed": 11.0},
        ]
        sessions = segment_arm_sessions(timeline)
        self.assertEqual([s["classification"] for s in sessions], ["arm_check", "arm_check", "arm_check", "flight"])
        self.assertTrue(sessions[-1]["ended_by_log"])
        self.assertFalse(sessions[-1]["ended_with_disarm"])

    def test_no_takeoff_evidence_is_not_called_flight(self):
        timeline = [
            {"time": "00:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "00:45.000", "eventType": "SNAPSHOT", "alt": 0.5, "dist": "4 m", "groundSpeed": 0.4},
            {"time": "00:50.000", "eventType": "FLIGHT_SESSION_END"},
        ]
        self.assertEqual(segment_arm_sessions(timeline)[0]["classification"], "uncertain")


if __name__ == "__main__":
    unittest.main()
