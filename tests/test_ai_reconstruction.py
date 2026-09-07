import unittest

from backend.ai_reconstruction import build_ai_reconstruction


class AIReconstructionTest(unittest.TestCase):
    def test_radio_scenario_uses_actual_altitude_and_cautious_language(self):
        facts = {
            "radio_loss_episodes": [
                {"time_s": 120.0, "dbm": -128, "recovered": True},
                {"time_s": 180.0, "dbm": -128, "recovered": False},
            ],
            "critical_radio_episode": {
                "time_s": 180.0,
                "altitude_m": 69.8,
                "altitude_window_min_m": 68.9,
                "altitude_window_max_m": 71.2,
                "vtx_changed": False,
            },
            "mode_transitions": [
                {"from": "RTL", "to": "LAND", "time_s": 201.1, "delta_s": 0.7}
            ],
            "land_distance_home_m": 1360.0,
            "ended_armed": True,
            "power": {},
        }
        result = build_ai_reconstruction(facts)
        self.assertEqual(result["dominant_scenario"], "radio")
        joined = " ".join(
            result["what_happened"]
            + result["likely_sequence"]
            + result["pilot_actions"]
            + result["possible_alternatives"]
        )
        self.assertIn("69.8", joined)
        self.assertIn("RTL", joined)
        self.assertIn("LAND", joined)
        self.assertIn("не зафіксовано", joined)
        self.assertNotIn("помилка пілота", joined.lower())
        self.assertNotIn("потрібно було", joined.lower())

    def test_confirmed_vtx_change_is_not_reported_as_missing(self):
        facts = {
            "radio_loss_episodes": [{"time_s": 90.0, "dbm": -128, "recovered": True}],
            "critical_radio_episode": {
                "time_s": 90.0,
                "altitude_m": 80.0,
                "altitude_window_min_m": 79.0,
                "altitude_window_max_m": 83.0,
                "vtx_changed": True,
            },
            "mode_transitions": [],
            "land_distance_home_m": None,
            "ended_armed": False,
            "power": {},
        }
        result = build_ai_reconstruction(facts)
        joined = " ".join(result["pilot_actions"])
        self.assertNotIn("зміна відеоканалу не зафіксована", joined.lower())

    def test_power_scenario_wins_when_power_evidence_is_stronger(self):
        facts = {
            "radio_loss_episodes": [{"time_s": 50.0, "dbm": -128, "recovered": True}],
            "critical_radio_episode": None,
            "mode_transitions": [],
            "land_distance_home_m": None,
            "ended_armed": True,
            "power": {
                "potential_thrust_loss_count": 3,
                "rpm_asymmetry_pct": 47.0,
                "min_voltage_v": 10.09,
                "max_current_a": 83.9,
            },
        }
        result = build_ai_reconstruction(facts)
        self.assertEqual(result["dominant_scenario"], "power")

    def test_short_rtl_land_is_reported_even_without_radio_scenario(self):
        facts = {
            "radio_loss_episodes": [],
            "critical_radio_episode": None,
            "mode_transitions": [
                {"from": "RTL", "to": "LAND", "time_s": 201.1, "delta_s": 0.6}
            ],
            "land_distance_home_m": 900.0,
            "ended_armed": False,
            "power": {},
        }
        result = build_ai_reconstruction(facts)
        joined = " ".join(result["likely_sequence"])
        self.assertIn("RTL", joined)
        self.assertIn("LAND", joined)
        self.assertIn("0.6", joined)
        self.assertIn("900", joined)

    def test_normal_log_does_not_invent_a_failure(self):
        facts = {
            "radio_loss_episodes": [],
            "critical_radio_episode": None,
            "mode_transitions": [],
            "land_distance_home_m": None,
            "ended_armed": False,
            "power": {},
        }
        result = build_ai_reconstruction(facts)
        self.assertEqual(result["dominant_scenario"], "none")
        self.assertTrue(any("не виявлено" in x.lower() for x in result["what_happened"]))


if __name__ == "__main__":
    unittest.main()
