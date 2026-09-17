from pathlib import Path

modules_path = Path("backend/ai_expert_modules.py")
text = modules_path.read_text(encoding="utf-8")
start = text.index("def analyze_control_modes(session: dict[str, Any]) -> dict[str, Any]:")
end = text.index("\ndef analyze_termination(session: dict[str, Any]) -> dict[str, Any]:", start)

replacement = r'''def analyze_control_modes(session: dict[str, Any]) -> dict[str, Any]:
    rows = [r for r in (session.get("rows") or []) if isinstance(r, dict)]
    evidence: list[str] = []
    sources: list[str] = []
    related: list[dict[str, Any]] = []
    previous_mode = None
    previous_time = None

    def first_measure(row, keys, *, distance=False):
        for key in keys:
            raw = row.get(key)
            value = _num(raw)
            if value is None and raw is not None:
                cleaned = "".join(ch if ch.isdigit() or ch in ".,-" else " " for ch in str(raw)).replace(",", ".")
                for token in cleaned.split():
                    try:
                        value = float(token)
                        break
                    except ValueError:
                        pass
            if value is not None:
                if distance:
                    unit_text = str(raw or "").lower()
                    if "km" in unit_text or "км" in unit_text:
                        value *= 1000.0
                return value
        return None

    loiter_samples = []
    for row in rows:
        t = _row_time(row)
        mode = str(row.get("mode") or "").strip().upper()
        if mode == "LOITER":
            alt = first_measure(row, ("alt", "altitude", "relAlt", "relative_alt", "relativeAltitude", "alt_m"))
            distance = first_measure(
                row,
                ("dist", "distance", "homeDistance", "home_distance", "distanceM", "distance_m"),
                distance=True,
            )
            if alt is not None and distance is not None:
                loiter_samples.append({"time_s": t, "alt": alt, "distance": distance})

        if mode and mode != previous_mode:
            if previous_mode is not None:
                sources.append("mode_transition")
                text = f"Режим змінено {previous_mode} -> {mode}."
                evidence.append(text)
                if t is not None:
                    related.append({"time_s": t, "type": "control", "text": text})
            previous_mode = mode
            previous_time = t

        text = str(row.get("systemText") or row.get("system_text") or "").strip()
        lower = text.lower()
        if not text:
            continue
        if "emergency stop" in lower:
            sources.append("emergency_stop")
            evidence.append(text)
        elif "failsafe" in lower:
            sources.append("failsafe_transition")
            evidence.append(text)
        elif "drop" in lower or "скид" in lower:
            sources.append("payload_event")
            evidence.append(text)
        if t is not None and any(k in lower for k in ("emergency stop", "failsafe", "drop", "скид")):
            related.append({"time_s": t, "type": "control", "text": text})

    # Project-specific LOITER operating rule:
    # vertical takeoff 0->50 m, normal horizontal operation at 50-300 m,
    # vertical descent 50->0 m. Up to 10 m horizontal drift is ignored.
    if len(loiter_samples) >= 2:
        horizontal_tolerance_m = 10.0
        max_alt = max(sample["alt"] for sample in loiter_samples)
        peak_index = max(range(len(loiter_samples)), key=lambda i: loiter_samples[i]["alt"])

        takeoff = loiter_samples[: peak_index + 1]
        if takeoff:
            base_distance = takeoff[0]["distance"]
            violation = next(
                (
                    sample
                    for sample in takeoff
                    if sample["alt"] < 50.0
                    and abs(sample["distance"] - base_distance) >= horizontal_tolerance_m
                ),
                None,
            )
            if violation is not None:
                horizontal = abs(violation["distance"] - base_distance)
                sources.extend(("loiter_vertical_takeoff", "loiter_altitude_profile", "loiter_horizontal_displacement"))
                text = (
                    "Неправильне використання польотного режиму LOITER: під час набору висоти "
                    f"горизонтальне переміщення {horizontal:.1f} м зафіксоване вже на висоті {violation['alt']:.1f} м. "
                    "Спочатку потрібно виконати вертикальний набір до 50 м, а горизонтальне переміщення "
                    "виконувати після досягнення 50 м; робочий діапазон LOITER — 50–300 м."
                )
                evidence.append(text)
                if violation["time_s"] is not None:
                    related.append({"time_s": violation["time_s"], "type": "control", "text": text})

        if max_alt >= 50.0 and peak_index < len(loiter_samples) - 1:
            descent = loiter_samples[peak_index:]
            crossing_index = next((i for i, sample in enumerate(descent) if sample["alt"] <= 50.0), None)
            if crossing_index is not None:
                landing = descent[crossing_index:]
                if landing:
                    base_distance = landing[0]["distance"]
                    violation = next(
                        (
                            sample
                            for sample in landing[1:]
                            if sample["alt"] < 50.0
                            and abs(sample["distance"] - base_distance) >= horizontal_tolerance_m
                        ),
                        None,
                    )
                    if violation is not None:
                        horizontal = abs(violation["distance"] - base_distance)
                        sources.extend(("loiter_vertical_landing", "loiter_altitude_profile", "loiter_horizontal_displacement"))
                        text = (
                            "Неправильне використання польотного режиму LOITER під час зниження: "
                            f"нижче 50 м зафіксоване горизонтальне переміщення {horizontal:.1f} м на висоті {violation['alt']:.1f} м. "
                            "Після зниження до 50 м посадковий профіль потрібно продовжувати вертикально вниз без значного горизонтального переміщення."
                        )
                        evidence.append(text)
                        if violation["time_s"] is not None:
                            related.append({"time_s": violation["time_s"], "type": "control", "text": text})

        high_sample = next((sample for sample in loiter_samples if sample["alt"] > 300.0), None)
        if high_sample is not None:
            sources.append("loiter_altitude_range")
            text = (
                f"LOITER використано поза заданим робочим діапазоном: зафіксована висота {high_sample['alt']:.1f} м; "
                "для цього профілю допустима робоча висота становить 50–300 м."
            )
            evidence.append(text)
            if high_sample["time_s"] is not None:
                related.append({"time_s": high_sample["time_s"], "type": "control", "text": text})

    sources = list(dict.fromkeys(sources))
    if not sources:
        return _result(evidence=["Критичних керуючих або режимних подій у цій сесії не виявлено."])
    critical_sources = {"emergency_stop", "failsafe_transition"}
    loiter_rule_sources = {"loiter_vertical_takeoff", "loiter_vertical_landing", "loiter_altitude_range"}
    severity = "critical" if critical_sources.intersection(sources) else "warning"
    status = "confirmed_problem" if critical_sources.intersection(sources) or loiter_rule_sources.intersection(sources) else "probable_problem"
    times = [e["time_s"] for e in related if e.get("time_s") is not None]
    return _result(
        status=status,
        severity=severity,
        source_classes=sources,
        start_time_s=min(times) if times else previous_time,
        end_time_s=max(times) if times else previous_time,
        evidence=evidence,
        related_events=related,
    )
'''

new_text = text[:start] + replacement + text[end:]
modules_path.write_text(new_text, encoding="utf-8")

expert_path = Path("backend/ai_expert.py")
expert_text = expert_path.read_text(encoding="utf-8")
short_start = expert_text.index("def _short_conclusion(session: dict[str, Any], subsystems: dict[str, dict[str, Any]]) -> str:")
short_end = expert_text.index("\ndef _analyze_session(", short_start)
short_replacement = r'''def _short_conclusion(session: dict[str, Any], subsystems: dict[str, dict[str, Any]]) -> str:
    control = subsystems.get("control") or {}
    control_sources = set(control.get("source_classes") or [])
    loiter_sources = {"loiter_vertical_takeoff", "loiter_vertical_landing", "loiter_altitude_range"}
    if control_sources.intersection(loiter_sources):
        loiter_evidence = [
            str(text).strip()
            for text in (control.get("evidence") or [])
            if "loiter" in str(text).lower() and str(text).strip()
        ]
        if loiter_evidence:
            return " ".join(loiter_evidence[:2])
        return "Неправильне використання польотного режиму LOITER. Для цього профілю вертикальний зліт виконується до 50 м, робочий діапазон становить 50–300 м, а нижче 50 м зниження виконується вертикально."

    affected = _affected_names(subsystems)
    if not affected:
        if session.get("classification") == "arm_check":
            return "Коротка ARM-перевірка; критичних відхилень у доступних даних не виявлено."
        return "У цій ARM-сесії підтверджених критичних відхилень за доступними даними не виявлено."
    labels = [SUBSYSTEM_LABELS.get(name, name) for name in affected]
    return "Уваги потребують: " + ", ".join(labels) + ". Деталі нижче наведені окремо без автоматичного встановлення причинності."
'''
expert_path.write_text(expert_text[:short_start] + short_replacement + expert_text[short_end:], encoding="utf-8")

print("LOITER vertical profile rule applied")
