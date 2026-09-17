from pathlib import Path
import unittest

SOURCE = Path("backend/main.py").read_text(encoding="utf-8")


class AIExpertIntegrationContractTest(unittest.TestCase):
    def test_legacy_ai_reconstruction_is_preserved(self):
        self.assertIn('"ai_reconstruction": ai_reconstruction', SOURCE)

    def test_new_expert_result_and_warning_are_returned(self):
        self.assertIn("build_ai_expert_analysis", SOURCE)
        self.assertIn('"ai_expert": ai_expert', SOURCE)
        self.assertIn('"ai_expert_warning": ai_expert_warning', SOURCE)

    def test_expert_layer_is_fail_closed(self):
        self.assertIn("ai_expert_warning = None", SOURCE)
        self.assertIn("except Exception as", SOURCE)
        self.assertIn("Поглиблений аналіз недоступний", SOURCE)

    def test_existing_analyzer_events_are_normalized_for_expert(self):
        for marker in (
            "communication_loss_episodes",
            "potential_thrust_loss_events",
            "rpm_drop_events",
            "_expert_radio_events",
            "_expert_thrust_events",
            "_expert_rpm_events",
        ):
            self.assertIn(marker, SOURCE)


if __name__ == "__main__":
    unittest.main()
