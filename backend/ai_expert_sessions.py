from __future__ import annotations

import re
from typing import Any

FLIGHT_ALTITUDE_SPAN_M = 2.0
FLIGHT_HOME_DISTANCE_M = 15.0
FLIGHT_GROUND_SPEED_MS = 2.5
ARM_CHECK_MAX_DURATION_S = 30.0


def parse_timeline_time_s(value: Any) -> float | None:
    text = str(value or "").strip()
    match = re.match(r"^(-)?(\d+):(\d+(?:\.\d+)?)$", text)
    if not match:
        return None
    total = int(match.group(2)) * 60.0 + float(match.group(3))
    return -total if match.group(1) else total


def _numeric(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:[\.,]\d+)?", str(value or ""))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def _distance_m(value: Any) -> float | None:
    number = _numeric(value)
    if number is None:
        return None
    text = str(value or "").lower()
    if "km" in text or "км" in text:
        number *= 1000.0
    return number


def _build_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    altitudes: list[float] = []
    distances: list[float] = []
    speeds: list[float] = []
    for row in rows:
        alt = _numeric(row.get("alt"))
        if alt is not None:
            altitudes.append(alt)
        dist = _distance_m(row.get("dist"))
        if dist is not None:
            distances.append(max(0.0, dist))
        speed = _numeric(row.get("groundSpeed"))
        if speed is not None:
            speeds.append(max(0.0, speed))
    altitude_span = (max(altitudes) - min(altitudes)) if altitudes else 0.0
    return {
        "altitude_span_m": altitude_span,
        "max_distance_m": max(distances) if distances else 0.0,
        "max_ground_speed_ms": max(speeds) if speeds else 0.0,
    }


def classify_arm_session(session: dict[str, Any]) -> str:
    metrics = session.get("metrics") or {}
    duration_s = float(session.get("duration_s") or 0.0)
    altitude_span_m = float(metrics.get("altitude_span_m") or 0.0)
    max_distance_m = float(metrics.get("max_distance_m") or 0.0)
    max_ground_speed_ms = float(metrics.get("max_ground_speed_ms") or 0.0)

    is_flight = duration_s >= 5.0 and (
        altitude_span_m >= FLIGHT_ALTITUDE_SPAN_M
        or max_distance_m >= FLIGHT_HOME_DISTANCE_M
        or max_ground_speed_ms >= FLIGHT_GROUND_SPEED_MS
    )
    if is_flight:
        return "flight"
    if (
        duration_s <= ARM_CHECK_MAX_DURATION_S
        and altitude_span_m < FLIGHT_ALTITUDE_SPAN_M
        and max_distance_m < FLIGHT_HOME_DISTANCE_M
        and max_ground_speed_ms < FLIGHT_GROUND_SPEED_MS
    ):
        return "arm_check"
    return "uncertain"


def _finalize_session(
    *,
    session_id: int,
    start_s: float,
    end_s: float,
    rows: list[dict[str, Any]],
    ended_with_disarm: bool,
    ended_by_log: bool,
) -> dict[str, Any]:
    metrics = _build_metrics(rows)
    session: dict[str, Any] = {
        "session_id": session_id,
        "start_s": float(start_s),
        "end_s": float(max(start_s, end_s)),
        "duration_s": float(max(0.0, end_s - start_s)),
        "ended_with_disarm": bool(ended_with_disarm),
        "ended_by_log": bool(ended_by_log),
        "rows": list(rows),
        "classification": "uncertain",
        "classification_evidence": [],
        "metrics": metrics,
    }
    session["classification"] = classify_arm_session(session)
    session["classification_evidence"] = [
        f"duration={session['duration_s']:.1f}s",
        f"altitude_span={metrics['altitude_span_m']:.1f}m",
        f"max_distance={metrics['max_distance_m']:.1f}m",
        f"max_ground_speed={metrics['max_ground_speed_ms']:.1f}m/s",
    ]
    return session


def segment_arm_sessions(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows_with_time: list[tuple[float, dict[str, Any]]] = []
    for row in timeline or []:
        if not isinstance(row, dict):
            continue
        time_s = parse_timeline_time_s(row.get("time"))
        if time_s is not None:
            rows_with_time.append((time_s, row))

    sessions: list[dict[str, Any]] = []
    active_start: float | None = None
    active_rows: list[dict[str, Any]] = []
    last_time: float | None = None

    for time_s, row in rows_with_time:
        last_time = time_s
        event_type = str(row.get("eventType") or "")

        if event_type == "FLIGHT_SESSION_START":
            if active_start is not None:
                sessions.append(
                    _finalize_session(
                        session_id=len(sessions) + 1,
                        start_s=active_start,
                        end_s=time_s,
                        rows=active_rows,
                        ended_with_disarm=False,
                        ended_by_log=False,
                    )
                )
            active_start = time_s
            active_rows = [row]
            continue

        if active_start is None:
            continue

        active_rows.append(row)
        if event_type == "FLIGHT_SESSION_END":
            sessions.append(
                _finalize_session(
                    session_id=len(sessions) + 1,
                    start_s=active_start,
                    end_s=time_s,
                    rows=active_rows,
                    ended_with_disarm=True,
                    ended_by_log=False,
                )
            )
            active_start = None
            active_rows = []

    if active_start is not None:
        end_s = last_time if last_time is not None else active_start
        sessions.append(
            _finalize_session(
                session_id=len(sessions) + 1,
                start_s=active_start,
                end_s=end_s,
                rows=active_rows,
                ended_with_disarm=False,
                ended_by_log=True,
            )
        )

    return sessions
