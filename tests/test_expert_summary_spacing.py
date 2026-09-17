from pathlib import Path

from backend.ai_expert import _short_conclusion


def test_combined_summary_uses_separate_paragraphs():
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

    assert "Виявлено декілька незалежних відхилень.\n\nESC / RPM / тяга:" in text
    assert "\n\nНеправильне використання польотного режиму LOITER:" in text
    assert "\n\nДодатково уваги потребують: Зв'язок / MAVLink." in text
    assert "\n\nПричинний зв'язок між цими відхиленнями" in text


def test_frontend_preserves_summary_paragraph_breaks():
    html = Path("index.html").read_text(encoding="utf-8")
    assert "EXPERT_SUMMARY_SECTIONS_V1" in html
    assert ".ai-expert-conclusion{white-space:pre-line" in html
