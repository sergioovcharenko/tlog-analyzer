from __future__ import annotations

from typing import Any

try:
    from backend.ai_expert_sessions import parse_timeline_time_s
except ImportError:
    from ai_expert_sessions import parse_timeline_time_s


def confidence_from_sources(source_classes) -> float:
    count = len(set(source_classes or []))
    if count <= 0:
        return 0.0
    if count == 1:
        return 0.55
    if count == 2:
        return 0.75
    if count == 3:
        return 0.88
    return 0.94


def _result(
    *,
    status: str = "no_significant_issue",
    severity: str = "info",
    source_classes=None,
    start_time_s=None,
    end_time_s=None,
    evidence=None,
    counter_evidence=None,
    related_events=None,
) -> dict[str, Any]:
    sources = list(dict.fromkeys(source_classes or []))
    return {
        "status": status,
        "severity": severity,
        "confidence": confidence_from_sources(sources),
        "start_time_s": start_time_s,
        "end_time_s": end_time_s,
        "evidence": list(evidence or []),
        "counter_evidence": list(counter_evidence or []),
        "related_events": list(related_events or []),
        "source_classes": sources,
    }


def _event_time(event: dict[str, Any]) -> float | None:
    value = event.get("time_s")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _row_time(row: dict[str, Any]) -> float | None:
    return parse_timeline_time_s(row.get("time"))


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def analyze_radio(session: dict[str, Any], radio_events) -> dict[str, Any]:
    events = [e for e in (radio_events or []) if isinstance(e, dict)]
    if not events:
        return _result(
            evidence=["У межах цієї ARM-сесії критичних подій MAVLink/радіотелеметрії не зафіксовано."],
            counter_evidence=[],
        )

    sources: list[str] = []
    evidence: list[str] = []
    related: list[dict[str, Any]] = []
    times = [t for t in (_event_time(e) for e in events) if t is not None]

    gap_events = [e for e in events if e.get("type") != "failsafe" and ("recovered" in e or e.get("dbm") is not None)]
    if gap_events:
        sources.append("mavlink_gap")
        evidence.append(f"Зафіксовано {len(gap_events)} епізод(ів) втрати/паузи MAVLink у межах цієї сесії.")

    dbm_values = [_num(e.get("dbm")) for e in events]
    dbm_values = [v for v in dbm_values if v is not None]
    critical_dbm = [v for v in dbm_values if v <= -128.0]
    if critical_dbm:
        sources.append("critical_dbm")
        evidence.append(f"Критичний рівень сигналу до {min(critical_dbm):.0f} dBm зафіксовано у {len(critical_dbm)} епізод(ах).")
    elif dbm_values:
        evidence.append(f"Найгірший зафіксований рівень у сесії: {min(dbm_values):.0f} dBm.")

    unrecovered = [e for e in events if e.get("recovered") is False]
    if unrecovered:
        sources.append("unrecovered_link")
        evidence.append("Щонайменше один епізод не має підтвердженого відновлення зв'язку в межах TLOG-сесії.")

    failsafe = [e for e in events if e.get("type") == "failsafe" or "failsafe" in str(e.get("text") or "").lower()]
    if failsafe:
        sources.append("failsafe_text")
        evidence.append("У цій сесії присутнє повідомлення failsafe, пов'язане з радіо/зв'язком.")

    for event in events:
        t = _event_time(event)
        if t is not None:
            related.append({"time_s": t, "type": "radio", "text": str(event.get("text") or "MAVLink/радіоподія")})

    unique_count = len(set(sources))
    if unique_count >= 2:
        status = "confirmed_problem"
    elif unique_count == 1:
        status = "probable_problem"
    else:
        status = "unknown"
    severity = "critical" if "unrecovered_link" in sources or "critical_dbm" in sources else "warning"
    return _result(
        status=status,
        severity=severity,
        source_classes=sources,
        start_time_s=min(times) if times else None,
        end_time_s=max(times) if times else None,
        evidence=evidence,
        related_events=related,
    )


def analyze_navigation(session: dict[str, Any]) -> dict[str, Any]:
    sources: list[str] = []
    evidence: list[str] = []
    related: list[dict[str, Any]] = []
    times: list[float] = []

    for row in session.get("rows") or []:
        if not isinstance(row, dict):
            continue
        text = str(row.get("systemText") or row.get("system_text") or "").strip()
        lower = text.lower()
        if not text:
            continue
        source = None
        if "stopped aiding" in lower or "ekf" in lower and any(k in lower for k in ("variance", "failsafe", "error", "unhealthy")):
            source = "ekf_state"
        elif "need position estimate" in lower or "position estimate" in lower and any(k in lower for k in ("need", "bad", "failed")):
            source = "position_estimate"
        elif "smartrtl" in lower and "bad position" in lower:
            source = "smartrtl_bad_position"
        elif "gps" in lower and any(k in lower for k in ("bad", "unhealthy", "lost", "no fix", "failsafe")):
            source = "gps_quality"
        if source:
            sources.append(source)
            evidence.append(text)
            t = _row_time(row)
            if t is not None:
                times.append(t)
                related.append({"time_s": t, "type": "navigation", "text": text})

    sources = list(dict.fromkeys(sources))
    if not sources:
        return _result(evidence=["Критичних навігаційних/EKF повідомлень у цій сесії не виявлено."])
    status = "confirmed_problem" if len(sources) >= 2 else "probable_problem"
    severity = "critical" if any(s in sources for s in ("ekf_state", "smartrtl_bad_position")) else "warning"
    return _result(
        status=status,
        severity=severity,
        source_classes=sources,
        start_time_s=min(times) if times else None,
        end_time_s=max(times) if times else None,
        evidence=evidence,
        related_events=related,
    )


def analyze_power(session: dict[str, Any]) -> dict[str, Any]:
    voltages: list[tuple[float | None, float]] = []
    currents: list[tuple[float | None, float]] = []
    warning_rows: list[tuple[float | None, str]] = []
    for row in session.get("rows") or []:
        if not isinstance(row, dict):
            continue
        t = _row_time(row)
        v = _num(row.get("volt"))
        c = _num(row.get("curr"))
        if v is not None and v > 0:
            voltages.append((t, v))
        if c is not None and c >= 0:
            currents.append((t, c))
        text = str(row.get("systemText") or row.get("system_text") or "").strip()
        lower = text.lower()
        if text and any(k in lower for k in ("battery failsafe", "low battery", "power fail", "voltage fail")):
            warning_rows.append((t, text))

    sources: list[str] = []
    evidence: list[str] = []
    related: list[dict[str, Any]] = []
    if warning_rows:
        sources.append("power_warning")
        evidence.extend(text for _, text in warning_rows)
        related.extend({"time_s": t, "type": "power", "text": text} for t, text in warning_rows if t is not None)

    if voltages:
        vmax = max(v for _, v in voltages)
        vmin = min(v for _, v in voltages)
        sag = vmax - vmin
        if vmax > 0 and sag >= max(1.0, vmax * 0.15):
            sources.append("voltage_sag")
            evidence.append(f"Просідання напруги в межах сесії: {vmax:.2f} -> {vmin:.2f} V ({sag:.2f} V).")

    if currents:
        max_current = max(c for _, c in currents)
        if max_current >= 80.0:
            sources.append("high_load")
            evidence.append(f"Піковий струм у сесії: {max_current:.1f} A.")

    sources = list(dict.fromkeys(sources))
    explicit = "power_warning" in sources
    enough = len(sources) >= 2 or explicit
    if not enough:
        counter = []
        if sources:
            counter.append("Окремий показник навантаження або напруги без незалежного підтвердження не вважається достатнім доказом проблеми живлення.")
        return _result(
            status="no_significant_issue" if not explicit else "probable_problem",
            severity="info" if not explicit else "warning",
            source_classes=sources,
            evidence=evidence or ["Незалежних ознак проблеми живлення в цій сесії не виявлено."],
            counter_evidence=counter,
            related_events=related,
        )

    times = [t for t, _ in voltages + currents if t is not None] + [t for t, _ in warning_rows if t is not None]
    return _result(
        status="confirmed_problem" if len(sources) >= 2 else "probable_problem",
        severity="critical" if "power_warning" in sources and "voltage_sag" in sources else "warning",
        source_classes=sources,
        start_time_s=min(times) if times else None,
        end_time_s=max(times) if times else None,
        evidence=evidence,
        related_events=related,
    )


def analyze_propulsion(session: dict[str, Any], thrust_events, rpm_events) -> dict[str, Any]:
    sources: list[str] = []
    evidence: list[str] = []
    related: list[dict[str, Any]] = []
    times: list[float] = []

    thrust = [e for e in (thrust_events or []) if isinstance(e, dict)]
    rpm = [e for e in (rpm_events or []) if isinstance(e, dict)]
    if thrust:
        sources.append("thrust_loss")
        evidence.append(f"Potential Thrust Loss: {len(thrust)} подій у цій сесії.")
    for event in thrust:
        t = _event_time(event)
        if t is not None:
            times.append(t)
            related.append({"time_s": t, "type": "propulsion", "text": str(event.get("text") or "Potential Thrust Loss")})

    asymmetry = []
    drops = []
    for event in rpm:
        pct = _num(event.get("differencePct") if event.get("differencePct") is not None else event.get("asymmetry_pct"))
        if pct is not None and pct >= 20.0:
            asymmetry.append(pct)
        if event.get("drop") or str(event.get("type") or "").lower() in ("rpm_drop", "drop"):
            drops.append(event)
        t = _event_time(event)
        if t is not None:
            times.append(t)
            related.append({"time_s": t, "type": "propulsion", "text": str(event.get("text") or "RPM подія")})
    if asymmetry:
        sources.append("rpm_asymmetry")
        evidence.append(f"Максимальна асиметрія RPM: {max(asymmetry):.1f}%.")
    if drops:
        sources.append("rpm_drop")
        evidence.append(f"Зафіксовано {len(drops)} подій падіння RPM.")

    for row in session.get("rows") or []:
        text = str(row.get("systemText") or row.get("system_text") or "").strip()
        if text and "esc" in text.lower() and any(k in text.lower() for k in ("fail", "error", "warning", "fault")):
            sources.append("esc_warning")
            evidence.append(text)
            t = _row_time(row)
            if t is not None:
                times.append(t)
                related.append({"time_s": t, "type": "propulsion", "text": text})

    sources = list(dict.fromkeys(sources))
    if not sources:
        return _result(evidence=["Підтверджених ознак відмови ESC/RPM/тяги в цій сесії не виявлено."])
    status = "confirmed_problem" if len(sources) >= 2 else "probable_problem"
    severity = "critical" if "thrust_loss" in sources and len(sources) >= 2 else "warning"
    return _result(
        status=status,
        severity=severity,
        source_classes=sources,
        start_time_s=min(times) if times else None,
        end_time_s=max(times) if times else None,
        evidence=evidence,
        related_events=related,
    )


def analyze_control_modes(session: dict[str, Any]) -> dict[str, Any]:
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

def analyze_termination(session: dict[str, Any]) -> dict[str, Any]:
    if session.get("ended_with_disarm"):
        return _result(
            status="no_significant_issue",
            severity="info",
            source_classes=["disarm_recorded"],
            start_time_s=session.get("end_s"),
            end_time_s=session.get("end_s"),
            evidence=["DISARM зафіксовано в межах цієї ARM-сесії."],
        )
    if session.get("ended_by_log"):
        return _result(
            status="unknown",
            severity="warning",
            source_classes=["ended_armed"],
            start_time_s=session.get("end_s"),
            end_time_s=session.get("end_s"),
            evidence=["Запис TLOG завершився, коли стан ARMED ще був активний."],
            counter_evidence=["Подальший DISARM або фактичний стан апарата в цьому файлі не зафіксовані."],
        )
    return _result(
        status="unknown",
        severity="info",
        evidence=["Спосіб завершення ARM-сесії за доступними даними не визначено."],
    )
