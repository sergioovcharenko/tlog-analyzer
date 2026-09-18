from __future__ import annotations

from typing import Any

try:
    from backend.ai_expert_sessions import segment_arm_sessions
    from backend.ai_expert_modules import (
        analyze_control_modes,
        analyze_navigation,
        analyze_power,
        analyze_propulsion,
        analyze_radio,
        analyze_termination,
    )
except ImportError:
    from ai_expert_sessions import segment_arm_sessions
    from ai_expert_modules import (
        analyze_control_modes,
        analyze_navigation,
        analyze_power,
        analyze_propulsion,
        analyze_radio,
        analyze_termination,
    )

SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}
AFFECTED_STATUSES = {"confirmed_problem", "probable_problem", "unknown"}

SUBSYSTEM_LABELS = {
    "radio": "Зв'язок / MAVLink",
    "navigation": "Навігація / GPS / EKF",
    "power": "Живлення / батарея",
    "propulsion": "ESC / RPM / тяга",
    "control": "Керування / режими",
    "termination": "Завершення польоту",
}

CHECKS_BY_SUBSYSTEM = {
    "radio": "Перевірити антени, RF-роз'єми та модулі, тракт передавач-приймач і можливі джерела радіоперешкод.",
    "navigation": "Перевірити GPS, компас/IMU, джерела EKF та налаштування зовнішньої навігації.",
    "power": "Перевірити акумулятор, силові роз'єми та просідання напруги під навантаженням.",
    "propulsion": "Перевірити ESC-телеметрію, мотори, пропелери та симетрію RPM під однаковим навантаженням.",
    "control": "Перевірити конфігурацію режимів/failsafe і точну послідовність RC-команд та аварійних подій.",
    "termination": "Зіставити останні секунди TLOG з іншими джерелами та перевірити причину завершення запису/стану ARMED.",
}


def _event_time(event: dict[str, Any]) -> float | None:
    try:
        value = event.get("time_s")
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _events_for_session(events, session: dict[str, Any]) -> list[dict[str, Any]]:
    start = float(session.get("start_s") or 0.0)
    end = float(session.get("end_s") or start)
    out = []
    for event in events or []:
        if not isinstance(event, dict):
            continue
        t = _event_time(event)
        if t is not None and start <= t <= end:
            out.append(event)
    return out


def _overall_severity(subsystems: dict[str, dict[str, Any]]) -> str:
    return max(
        (str(module.get("severity") or "info") for module in subsystems.values()),
        key=lambda value: SEVERITY_RANK.get(value, 0),
        default="info",
    )


def _affected_names(subsystems: dict[str, dict[str, Any]]) -> list[str]:
    names = []
    for name, module in subsystems.items():
        status = str(module.get("status") or "")
        severity = str(module.get("severity") or "info")
        if status in {"confirmed_problem", "probable_problem"} or (status == "unknown" and severity != "info"):
            names.append(name)
    return names


def _unique_source_count(subsystems: dict[str, dict[str, Any]]) -> int:
    classes = set()
    for name, module in subsystems.items():
        for source in module.get("source_classes") or []:
            classes.add((name, str(source)))
    return len(classes)


def _build_chronology(subsystems: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    raw = []
    seen = set()
    for subsystem_name, module in subsystems.items():
        for event in module.get("related_events") or []:
            if not isinstance(event, dict):
                continue
            t = _event_time(event)
            if t is None:
                continue
            text = str(event.get("text") or "").strip()
            event_type = str(event.get("type") or subsystem_name)
            signature = (round(t, 3), event_type, text)
            if signature in seen:
                continue
            seen.add(signature)
            raw.append(
                {
                    "time_s": round(t, 3),
                    "subsystem": subsystem_name,
                    "type": event_type,
                    "text": text or SUBSYSTEM_LABELS.get(subsystem_name, subsystem_name),
                }
            )
    raw.sort(key=lambda item: item["time_s"])
    return raw


def _build_interpretation(subsystems: dict[str, dict[str, Any]]) -> list[str]:
    out: list[str] = []
    radio = subsystems.get("radio") or {}
    navigation = subsystems.get("navigation") or {}
    radio_problem = radio.get("status") in {"confirmed_problem", "probable_problem"}
    nav_problem = navigation.get("status") in {"confirmed_problem", "probable_problem"}
    radio_t = radio.get("start_time_s")
    nav_t = navigation.get("start_time_s")

    if radio_problem and nav_problem and radio_t is not None and nav_t is not None:
        if float(radio_t) < float(nav_t):
            out.append(
                "Ознаки проблем зі зв'язком зафіксовано раніше за навігаційні/EKF події; причинний зв'язок за TLOG не встановлено."
            )
        elif float(nav_t) < float(radio_t):
            out.append(
                "Навігаційні/EKF події зафіксовано раніше за ознаки проблем зі зв'язком; причинний зв'язок за TLOG не встановлено."
            )
        else:
            out.append(
                "Ознаки проблем зі зв'язком і навігаційні/EKF події часово близькі; причинний зв'язок за TLOG не встановлено."
            )

    for name, module in subsystems.items():
        if module.get("status") not in {"confirmed_problem", "probable_problem"}:
            continue
        confidence = float(module.get("confidence") or 0.0)
        if confidence <= 0:
            continue
        out.append(
            f"{SUBSYSTEM_LABELS.get(name, name)}: висновок спирається на {len(set(module.get('source_classes') or []))} незалежний(і) клас(и) ознак; підтримка даними {confidence * 100:.0f}%."
        )
    return out


def _build_confirmed(subsystems: dict[str, dict[str, Any]]) -> list[str]:
    confirmed = []
    for name, module in subsystems.items():
        label = SUBSYSTEM_LABELS.get(name, name)
        for text in module.get("evidence") or []:
            cleaned = str(text).strip()
            if cleaned:
                confirmed.append(f"{label}: {cleaned}")
    return confirmed


def _build_unknowns(session: dict[str, Any], subsystems: dict[str, dict[str, Any]]) -> list[str]:
    unknowns = []
    if session.get("ended_by_log") and not session.get("ended_with_disarm"):
        unknowns.append(
            "Запис TLOG завершився, коли стан ARMED ще був активний. Подальший DISARM або фактичний стан апарата в цьому файлі не зафіксовані."
        )
    if (
        (subsystems.get("radio") or {}).get("status") in {"confirmed_problem", "probable_problem"}
        and (subsystems.get("navigation") or {}).get("status") in {"confirmed_problem", "probable_problem"}
    ):
        unknowns.append(
            "За самим TLOG неможливо довести причинний зв'язок між подіями радіолінії та навігаційними/EKF подіями лише за їх часовою послідовністю."
        )
    return unknowns


def _build_checks(subsystems: dict[str, dict[str, Any]]) -> list[str]:
    checks = []
    for name, module in subsystems.items():
        status = str(module.get("status") or "")
        severity = str(module.get("severity") or "info")
        if status in {"confirmed_problem", "probable_problem"} or (status == "unknown" and severity != "info"):
            check = CHECKS_BY_SUBSYSTEM.get(name)
            if check and check not in checks:
                checks.append(check)
    return checks


def _enrich_propulsion_motor_identity(module: dict[str, Any], rpm_events) -> None:
    candidates = []
    for event in rpm_events or []:
        if not isinstance(event, dict):
            continue
        motor = event.get("lowerMotor")
        if motor is None:
            continue
        try:
            pct = float(event.get("differencePct") or event.get("asymmetry_pct") or 0.0)
        except (TypeError, ValueError):
            pct = 0.0
        candidates.append((pct, motor))
    if not candidates:
        return

    pct, motor = max(candidates, key=lambda item: item[0])
    try:
        motor_label = str(int(float(motor)))
    except (TypeError, ValueError):
        motor_label = str(motor)
    drop_count = sum(
        1
        for event in rpm_events or []
        if isinstance(event, dict)
        and (event.get("drop") or str(event.get("type") or "").lower() in {"rpm_drop", "drop"})
    )
    details = f"Motor {motor_label}: зафіксовано нижчі RPM відносно парного мотора"
    if pct > 0:
        details += f"; максимальна асиметрія RPM {pct:.1f}%"
    if drop_count:
        details += f"; зафіксовано {drop_count} подій падіння RPM"
    details += "."

    evidence = list(module.get("evidence") or [])
    if details not in evidence:
        evidence.insert(0, details)
    module["evidence"] = evidence
    module["focus_motor"] = motor_label


def _short_conclusion(session: dict[str, Any], subsystems: dict[str, dict[str, Any]]) -> str:
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

    special_parts: list[str] = []
    if has_propulsion_issue:
        propulsion_evidence = [str(text).strip() for text in (propulsion.get("evidence") or []) if str(text).strip()]
        if propulsion_evidence:
            special_parts.append("ESC / RPM / тяга: " + " ".join(propulsion_evidence[:3]))
        else:
            special_parts.append("ESC / RPM / тяга: зафіксовано ознаки проблеми силової установки.")

    if has_loiter_issue:
        loiter_evidence = [
            str(text).strip()
            for text in (control.get("evidence") or [])
            if "loiter" in str(text).lower() and str(text).strip()
        ]
        if loiter_evidence:
            special_parts.append(loiter_evidence[0])
        else:
            special_parts.append(
                "Неправильне використання польотного режиму LOITER. Для цього профілю вертикальний зліт виконується до 50 м, робочий діапазон становить 10–500 м, а нижче 50 м зниження виконується вертикально."
            )

    covered = {"propulsion" if has_propulsion_issue else None, "control" if has_loiter_issue else None}
    covered.discard(None)
    remaining = [name for name in affected if name not in covered]
    if remaining:
        labels = [SUBSYSTEM_LABELS.get(name, name) for name in remaining]
        special_parts.append("Додатково уваги потребують: " + ", ".join(labels) + ".")

    if special_parts:
        if len(affected) > 1:
            return (
                "Виявлено декілька незалежних відхилень.\n\n"
                + "\n\n".join(special_parts)
                + "\n\nПричинний зв'язок між цими відхиленнями за самим TLOG не встановлено."
            )
        return "\n\n".join(special_parts)

    labels = [SUBSYSTEM_LABELS.get(name, name) for name in affected]
    return "Уваги потребують: " + ", ".join(labels) + ". Деталі нижче наведені окремо без автоматичного встановлення причинності."


def _analyze_session(session, radio_events, thrust_events, rpm_events, *, loiter_rule_enabled: bool = False) -> dict[str, Any]:
    scoped_radio = _events_for_session(radio_events, session)
    scoped_thrust = _events_for_session(thrust_events, session)
    scoped_rpm = _events_for_session(rpm_events, session)

    propulsion = analyze_propulsion(session, scoped_thrust, scoped_rpm)
    _enrich_propulsion_motor_identity(propulsion, scoped_rpm)
    subsystems = {
        "radio": analyze_radio(session, scoped_radio),
        "navigation": analyze_navigation(session),
        "power": analyze_power(session),
        "propulsion": propulsion,
        "control": analyze_control_modes(session, loiter_rule_enabled=loiter_rule_enabled),
        "termination": analyze_termination(session),
    }
    severity = _overall_severity(subsystems)

    aircraft_pairs = []
    for row in session.get("rows") or []:
        aircraft_name = row.get("aircraftType")
        board_type = row.get("aircraftBoardType")
        flight_number = row.get("flightNumber")
        if aircraft_name:
            pair = {
                "flightNumber": flight_number,
                "aircraftType": aircraft_name,
                "aircraftBoardType": board_type,
            }
            if pair not in aircraft_pairs:
                aircraft_pairs.append(pair)

    aircraft_types = list(dict.fromkeys(
        item["aircraftType"] for item in aircraft_pairs if item.get("aircraftType")
    ))

    return {
        "session_id": int(session["session_id"]),
        "classification": str(session.get("classification") or "uncertain"),
        "start_s": float(session.get("start_s") or 0.0),
        "end_s": float(session.get("end_s") or session.get("start_s") or 0.0),
        "duration_s": float(session.get("duration_s") or 0.0),
        "ended_with_disarm": bool(session.get("ended_with_disarm")),
        "ended_by_log": bool(session.get("ended_by_log")),
        "aircraft_type": aircraft_types[0] if len(aircraft_types) == 1 else None,
        "aircraft_types": aircraft_types,
        "flight_aircraft": aircraft_pairs,
        "overall_severity": severity,
        "short_conclusion": _short_conclusion(session, subsystems),
        "chronology": _build_chronology(subsystems),
        "subsystems": subsystems,
        "confirmed": _build_confirmed(subsystems),
        "interpretation": _build_interpretation(subsystems),
        "unknowns": _build_unknowns(session, subsystems),
        "checks": _build_checks(subsystems),
        "affected_subsystem_count": len(_affected_names(subsystems)),
        "unique_evidence_class_count": _unique_source_count(subsystems),
    }


def _priority_key(session: dict[str, Any]):
    return (
        SEVERITY_RANK.get(str(session.get("overall_severity") or "info"), 0),
        int(session.get("affected_subsystem_count") or 0),
        int(session.get("unique_evidence_class_count") or 0),
        int(session.get("session_id") or 0),
    )


def _build_summary(sessions: list[dict[str, Any]], primary: dict[str, Any] | None) -> str:
    count = len(sessions)
    if not count:
        return "ARM-сесії у TLOG не виявлено."
    problem_sessions = [s for s in sessions if s.get("overall_severity") in {"warning", "critical"}]
    if not problem_sessions:
        return f"Виявлено {count} ARM-сесії. Підтверджених критичних відхилень у них не виявлено."
    if primary is None:
        return f"Виявлено {count} ARM-сесії; частина з них потребує додаткової перевірки."
    other_count = len(problem_sessions) - 1
    if other_count > 0:
        return (
            f"Виявлено {count} ARM-сесії. Основну увагу потребує сесія №{primary['session_id']}; "
            f"ще {other_count} сесія(ї) містить(ять) відхилення."
        )
    return f"Виявлено {count} ARM-сесії. Основні відхилення зосереджені у сесії №{primary['session_id']}."


def build_ai_expert_analysis(*, timeline, radio_events, thrust_events, rpm_events, loiter_rule_enabled: bool = False) -> dict[str, Any]:
    raw_sessions = segment_arm_sessions(list(timeline or []))
    sessions = [
        _analyze_session(session, radio_events or [], thrust_events or [], rpm_events or [], loiter_rule_enabled=loiter_rule_enabled)
        for session in raw_sessions
    ]

    problematic = [s for s in sessions if s.get("overall_severity") in {"warning", "critical"}]
    primary = max(problematic, key=_priority_key) if problematic else None

    return {
        "version": 1,
        "summary": _build_summary(sessions, primary),
        "primary_session_id": primary.get("session_id") if primary else None,
        "sessions": sessions,
        "warnings": [],
    }
