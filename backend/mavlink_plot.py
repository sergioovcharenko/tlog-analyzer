import math

TRANSPORT_FIELDS = {"mavpackettype", "_timestamp"}
ANGLE_FIELDS = {("ATTITUDE", "roll"), ("ATTITUDE", "pitch"), ("ATTITUDE", "yaw")}


def _finite_scalar(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _downsample(times, values, limit):
    if len(values) <= limit:
        return list(times), list(values)
    limit = max(2, int(limit))
    if limit == 2:
        return [times[0], times[-1]], [values[0], values[-1]]
    step = (len(values) - 1) / (limit - 1)
    idx = sorted({0, len(values) - 1, *[round(i * step) for i in range(1, limit - 1)]})
    return [times[i] for i in idx], [values[i] for i in idx]


def _normalize_value(message_type, field, value):
    msg = str(message_type or "").upper()
    f = str(field or "").lower()
    v = float(value)
    if (msg, field) in ANGLE_FIELDS:
        return math.degrees(v), "deg"
    if msg == "SYS_STATUS" and f == "voltage_battery":
        return v / 1000.0, "V"
    if msg == "SYS_STATUS" and f == "current_battery":
        return v / 100.0, "A"
    if msg == "SYS_STATUS" and f == "load":
        return v / 10.0, "%"
    if msg == "BATTERY_STATUS" and f == "current_battery":
        return v / 100.0, "A"
    if msg == "BATTERY_STATUS" and f == "temperature":
        return v / 100.0, "°C"
    if msg in {"GLOBAL_POSITION_INT", "GPS_RAW_INT"} and f in {"alt", "relative_alt"}:
        return v / 1000.0, "m"
    if msg == "GLOBAL_POSITION_INT" and f in {"vx", "vy", "vz"}:
        return v / 100.0, "m/s"
    if msg == "GPS_RAW_INT" and f == "vel":
        return v / 100.0, "m/s"
    if msg == "VFR_HUD" and f in {"airspeed", "groundspeed", "climb"}:
        return v, "m/s"
    if msg == "VFR_HUD" and f == "alt":
        return v, "m"
    if msg == "VFR_HUD" and f == "heading":
        return v, "deg"
    if msg == "VFR_HUD" and f == "throttle":
        return v, "%"
    if "rpm" in f:
        return v, "rpm"
    if f.endswith("_pct") or f in {"battery_remaining", "engine_load"}:
        return v, "%"
    if f in {"temperature", "temperature_core", "mcu_temperature"} or f.endswith("_temperature"):
        return v, "native"
    return v, ""


class MavlinkPlotCollector:
    """Collect graphable MAVLink scalars with bounded per-series memory.

    High-rate TLOGs can contain hundreds of thousands of samples. Keeping every
    sample until build() used to make graph collection consume memory and spend
    extra time downsampling huge arrays at the end. Each series is now compacted
    incrementally whenever its temporary buffer reaches 2x the requested output
    limit. The first and most recent sample remain preserved.
    """

    def __init__(self, max_points_per_series=1200):
        self.max_points_per_series = max(2, int(max_points_per_series))
        self._series = {}
        self._compact_at = self.max_points_per_series * 2

    def _compact_bucket(self, bucket):
        times, values = _downsample(
            bucket["timestamps"],
            bucket["values"],
            self.max_points_per_series,
        )
        bucket["timestamps"] = times
        bucket["values"] = values

    def add(self, message_type, fields, timestamp):
        if not isinstance(fields, dict) or not _finite_scalar(timestamp):
            return
        msg = str(message_type or "UNKNOWN").upper()
        for field, raw in fields.items():
            field = str(field)
            if field in TRANSPORT_FIELDS or not _finite_scalar(raw):
                continue
            value, unit = _normalize_value(msg, field, raw)
            if not math.isfinite(value):
                continue
            bucket = self._series.setdefault((msg, field), {"timestamps": [], "values": [], "unit": unit})
            bucket["timestamps"].append(float(timestamp))
            bucket["values"].append(float(value))
            if unit and not bucket.get("unit"):
                bucket["unit"] = unit
            if len(bucket["values"]) >= self._compact_at:
                self._compact_bucket(bucket)

    def build(self, base_timestamp):
        base = float(base_timestamp or 0.0)
        groups = {}
        for (msg, field), bucket in sorted(self._series.items()):
            times = [int(round((ts - base) * 1000.0)) for ts in bucket["timestamps"]]
            times, values = _downsample(times, bucket["values"], self.max_points_per_series)
            groups.setdefault(msg, {})[field] = {
                "id": f"{msg}.{field}",
                "label": f"{msg}.{field}",
                "unit": bucket.get("unit") or "",
                "time_ms": times,
                "values": values,
            }
        return {"groups": groups}


def _severity_level(severity, is_error=False, event_type=""):
    if is_error:
        return "error"
    try:
        s = int(severity)
    except (TypeError, ValueError):
        s = None
    if s is not None:
        if s <= 3:
            return "error"
        if s <= 4:
            return "warning"
        if s <= 6:
            return "info"
        return "recovery"
    et = str(event_type or "").upper()
    if any(token in et for token in ("CRITICAL", "FAIL", "LOSS", "THRUST", "ERROR")):
        return "error"
    if any(token in et for token in ("WARNING", "DEGRADED")):
        return "warning"
    if any(token in et for token in ("RESTORE", "RECOVERY", "OK")):
        return "recovery"
    return "info"


def build_board_messages(timeline_rows, base_timestamp):
    """Return only raw ArduPilot/MAVLink STATUSTEXT received from the board."""
    base = float(base_timestamp or 0.0)
    out = []
    seen = set()
    for row in timeline_rows or []:
        if not isinstance(row, dict):
            continue
        text = str(row.get("system_text") or "").strip()
        ts = row.get("timestamp")
        if not text or not _finite_scalar(ts):
            continue
        item = {
            "time_ms": int(round((float(ts) - base) * 1000.0)),
            "level": _severity_level(row.get("severity"), row.get("isError"), row.get("eventType")),
            "text": text,
            "event_type": str(row.get("eventType") or "SYSTEM"),
            "source": "board",
        }
        key = (item["time_ms"], item["text"])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return sorted(out, key=lambda item: item["time_ms"])
