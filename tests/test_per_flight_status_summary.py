from pathlib import Path
import unittest

BACKEND = Path("backend/main.py").read_text(encoding="utf-8")
FRONTEND = Path("index.html").read_text(encoding="utf-8")


class PerFlightStatusSummaryContractTest(unittest.TestCase):
    def test_log_ended_armed_takes_priority_over_any_earlier_disarm(self):
        armed_pos = BACKEND.index("elif log_ended_armed:")
        disarm_pos = BACKEND.index("elif disarm_detected:")
        self.assertLess(
            armed_pos,
            disarm_pos,
            "A final ARMED log must not be reported as 'board completed flight' just because an earlier session had DISARM",
        )

    def test_each_session_has_user_facing_status_labels(self):
        for text in (
            "Завершено штатно",
            "ARM-сесія / зліт не підтверджено",
            "Втрата зв'язку",
            "Потребує уваги",
        ):
            self.assertIn(text, BACKEND)

    def test_each_session_status_has_a_color_class(self):
        for css_class in (
            "flight-session-status-ok",
            "flight-session-status-info",
            "flight-session-status-warning",
            "flight-session-status-critical",
        ):
            self.assertIn(css_class, BACKEND)
            self.assertIn(f".{css_class}", FRONTEND)

    def test_session_summary_spans_the_row(self):
        self.assertIn(".flight-session-status{", FRONTEND)
        self.assertIn("display:block", FRONTEND)
        self.assertIn("width:100%", FRONTEND)


if __name__ == "__main__":
    unittest.main()
