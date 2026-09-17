from pathlib import Path
import re

BACKEND = Path("backend/ai_expert.py")
INDEX = Path("index.html")
PATCHER = Path("tools/apply_ai_expert.py")

NEW_SHORT_CONCLUSION = r'''def _short_conclusion(session: dict[str, Any], subsystems: dict[str, dict[str, Any]]) -> str:
    affected = _affected_names(subsystems)
    if not affected:
        if session.get("classification") == "arm_check":
            return "Коротка ARM-перевірка; критичних відхилень у доступних даних не виявлено."
        return "У цій ARM-сесії підтверджених критичних відхилень за доступними даними не виявлено."

    control = subsystems.get("control") or {}
    control_sources = set(control.get("source_classes") or [])
    loiter_sources = {"loiter_vertical_takeoff", "loiter_vertical_landing", "loiter_altitude_range"}
    has_loiter_issue = bool(control_sources.intersection(loiter_sources))
    propulsion = subsystems.get("propulsion") or {}
    has_propulsion_issue = propulsion.get("status") in {"confirmed_problem", "probable_problem"}

    sections: list[str] = []
    if has_propulsion_issue:
        propulsion_evidence = [str(text).strip() for text in (propulsion.get("evidence") or []) if str(text).strip()]
        selected: list[str] = []
        motor_evidence = next((text for text in propulsion_evidence if "motor " in text.lower()), "")
        if motor_evidence:
            selected.append(motor_evidence.rstrip("."))
        for text in propulsion_evidence:
            lower = text.lower()
            if text == motor_evidence:
                continue
            if "асиметр" in lower and any("асиметр" in item.lower() for item in selected):
                continue
            if "падіння rpm" in lower and any("падіння rpm" in item.lower() for item in selected):
                continue
            if len(selected) < 3:
                selected.append(text.rstrip("."))
        if selected:
            sections.append("ESC / RPM / тяга:\n" + "; ".join(selected) + ".")
        else:
            sections.append("ESC / RPM / тяга:\nЗафіксовано ознаки проблеми силової установки.")

    if has_loiter_issue:
        loiter_evidence = [
            str(text).strip()
            for text in (control.get("evidence") or [])
            if "loiter" in str(text).lower() and str(text).strip()
        ]
        if loiter_evidence:
            loiter_text = loiter_evidence[0]
        else:
            loiter_text = (
                "Неправильне використання польотного режиму LOITER. Для цього профілю вертикальний зліт виконується до 50 м, "
                "робочий діапазон становить 50–300 м, а нижче 50 м зниження виконується вертикально."
            )
        sections.append("Керування / режими:\n" + loiter_text)

    covered = {"propulsion" if has_propulsion_issue else None, "control" if has_loiter_issue else None}
    covered.discard(None)
    remaining = [name for name in affected if name not in covered]
    if remaining:
        labels = [SUBSYSTEM_LABELS.get(name, name) for name in remaining]
        sections.append("Додатково потребують уваги:\n" + ", ".join(labels) + ".")

    if sections:
        if len(affected) > 1:
            sections.insert(0, "Виявлено декілька незалежних відхилень.")
            sections.append("Причинний зв'язок між цими відхиленнями за самим TLOG не встановлено.")
        return "\n\n".join(sections)

    labels = [SUBSYSTEM_LABELS.get(name, name) for name in affected]
    return "Уваги потребують: " + ", ".join(labels) + ". Деталі нижче наведені окремо без автоматичного встановлення причинності."
'''


def patch_backend() -> None:
    source = BACKEND.read_text(encoding="utf-8")
    pattern = re.compile(r"def _short_conclusion\(session: dict\[str, Any\], subsystems: dict\[str, dict\[str, Any\]\]\) -> str:\n.*?\n\ndef _analyze_session", re.S)
    replacement = NEW_SHORT_CONCLUSION + "\n\ndef _analyze_session"
    updated, count = pattern.subn(replacement, source, count=1)
    if count != 1:
        raise SystemExit(f"short conclusion function replacement count={count}")
    BACKEND.write_text(updated, encoding="utf-8")


def patch_frontend() -> None:
    source = INDEX.read_text(encoding="utf-8")
    old = ".ai-expert-conclusion{margin:12px 0;font-weight:700;line-height:1.5}"
    new = ".ai-expert-conclusion{margin:12px 0;font-weight:700;line-height:1.5;white-space:pre-wrap}"
    if new not in source:
        if old not in source:
            raise SystemExit("ai expert conclusion CSS anchor not found in index.html")
        source = source.replace(old, new, 1)
    INDEX.write_text(source, encoding="utf-8")


def patch_generator() -> None:
    source = PATCHER.read_text(encoding="utf-8")
    old = ".ai-expert-conclusion{margin:12px 0;font-weight:700;line-height:1.5}"
    new = ".ai-expert-conclusion{margin:12px 0;font-weight:700;line-height:1.5;white-space:pre-wrap}"
    if new not in source:
        if old not in source:
            raise SystemExit("ai expert conclusion CSS anchor not found in tools/apply_ai_expert.py")
        source = source.replace(old, new, 1)
    PATCHER.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    patch_backend()
    patch_frontend()
    patch_generator()
    print("expert conclusion sections applied")
