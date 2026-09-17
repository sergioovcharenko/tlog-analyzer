from pathlib import Path

path = Path("backend/ai_expert_modules.py")
text = path.read_text(encoding="utf-8")
start = text.index("def analyze_control_modes(session: dict[str, Any]) -> dict[str, Any]:")
end = text.index("\ndef analyze_termination(session: dict[str, Any]) -> dict[str, Any]:", start)

replacement = r'''def analyze_control_modes(session: dict[str, Any]) -> dict[str, Any]:
    rows = [r for r in (session.get("rows") or []) if isinstance(r, dict)]
    evidence: list[str] = []
    sources: list[str] = []
    related: list[dict[str, Any]] = []
    previous_mode = None
    previous_time = None

    def first_num(row, keys):
        for key in keys:
            value = _num(row.get(key))
            if value is not None:
                return value
        return None

    loiter_samples = []
    for row in rows:
        t = _row_time(row)
        mode = str(row.get("mode") or "").strip().upper()
        if mode == "LOITER":
            alt = first_num(row, ("alt", "altitude", "relAlt", "relative_alt", "relativeAltitude", "alt_m"))
            distance = first_num(row, ("distance", "dist", "homeDistance", "home_distance", "distanceM", "distance_m"))
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
    # take off vertically 0->50 m, normal horizontal flight at 50-300 m,
    # and descend vertically 50->0 m. Ignore up to 10 m horizontal drift.
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
                    "Для цього профілю спочатку потрібно виконати вертикальний набір до 50 м, "
                    "а горизонтальне переміщення виконувати після досягнення 50 м; робочий діапазон LOITER — 50–300 м."
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
path.write_text(new_text, encoding="utf-8")
print("LOITER vertical profile rule applied")
