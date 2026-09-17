import unittest
from pathlib import Path

from backend.ai_expert import _short_conclusion


class ExpertSummarySpacingTest(unittest.TestCase):
    def test_combined_summary_uses_separate_paragraphs(self):
        session = {"classification": "flight"}
        subsystems = {
            "radio": {"status": "confirmed_problem", "severity": "warning", "evidence": []},
            "navigation": {"status": "normal", "severity": "info", "evidence": []},
            "power": {"status": "normal", "severity": "info", "evidence": []},
            "propulsion": {
                "status": "confirmed_problem",
                "severity": "critical",
                "evidence": ["Motor 4: зафіксовано нижчі RPM; максимальна асиметрія RPM 100.0%."],
            },
            "control": {
                "status": "confirmed_problem",
                "severity": "warning",
                "source_classes": ["loiter_vertical_takeoff"],
                "evidence": [
                    "Неправильне використання польотного режиму LOITER: горизонтальне переміщення 17.1 м зафіксоване вже на висоті 9.4 м."
                ],
            },
            "termination": {"status": "normal", "severity": "info", "evidence": []},
        }

        text = _short_conclusion(session, subsystems)

        self.assertIn("Виявлено декілька незалежних відхилень.\n\nESC / RPM / тяга:", text)
        self.assertIn("\n\nНеправильне використання польотного режиму LOITER:", text)
        self.assertIn("\n\nДодатково уваги потребують: Зв'язок / MAVLink.", text)
        self.assertIn("\n\nПричинний зв'язок між цими відхиленнями", text)

    def test_frontend_preserves_summary_paragraph_breaks(self):
        html = Path("index.html").read_text(encoding="utf-8")
        self.assertIn("EXPERT_SUMMARY_SECTIONS_V1", html)
        self.assertIn(".ai-expert-conclusion{", html)
        self.assertIn("white-space:pre-line;", html)


if __name__ == "__main__":
    unittest.main()
