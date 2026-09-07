import unittest

from backend.main import build_ai_reconstruction_facts


class AIReconstructionIntegrationTest(unittest.TestCase):
    def test_extracts_stable_altitude_and_short_rtl_land(self):
        facts = build_ai_reconstruction_facts(
            radio_loss_episodes=[{"time_s": 180.0, "dbm": -128, "recovered": False}],
            mode_transitions=[{"from": "RTL", "to": "LAND", "time_s": 201.1, "delta_s": 0.7}],
            altitude_samples=[
                {"time_s": 176.0, "altitude_m": 69.2},
                {"time_s": 180.0, "altitude_m": 69.8},
                {"time_s": 184.0, "altitude_m": 71.0},
            ],
            vtx_events=[],
            home_distance_samples=[{"time_s": 201.1, "distance_m": 1360.0}],
            ended_armed=True,
            power_metrics={},
        )
        ep = facts["critical_radio_episode"]
        self.assertAlmostEqual(ep["altitude_m"], 69.8, places=1)
        self.assertLessEqual(ep["altitude_window_max_m"] - ep["altitude_window_min_m"], 5.0)
        self.assertFalse(ep["vtx_changed"])
        self.assertEqual(facts["land_distance_home_m"], 1360.0)
        self.assertTrue(facts["ended_armed"])

    def test_vtx_event_inside_reaction_window_is_detected(self):
        facts = build_ai_reconstruction_facts(
            radio_loss_episodes=[{"time_s": 90.0, "dbm": -128, "recovered": True}],
            mode_transitions=[],
            altitude_samples=[{"time_s": 90.0, "altitude_m": 80.0}],
            vtx_events=[{"time_s": 94.0, "frequency": 5580}],
            home_distance_samples=[],
            ended_armed=False,
            power_metrics={},
        )
        self.assertTrue(facts["critical_radio_episode"]["vtx_changed"])

    def test_structured_vtx_change_across_blind_zone_is_preserved(self):
        facts = build_ai_reconstruction_facts(
            radio_loss_episodes=[{
                "time_s": 90.0,
                "dbm": -128,
                "recovered": True,
                "vtx_changed": True,
            }],
            mode_transitions=[],
            altitude_samples=[{"time_s": 90.0, "altitude_m": 80.0}],
            vtx_events=[],
            home_distance_samples=[],
            ended_armed=False,
            power_metrics={},
        )
        self.assertTrue(facts["critical_radio_episode"]["vtx_changed"])


if __name__ == "__main__":
    unittest.main()
