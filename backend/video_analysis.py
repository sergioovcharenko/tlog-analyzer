from __future__ import annotations


def map_video_to_tlog_time(video_time_sec, video_anchor_sec, tlog_anchor_sec):
    return float(tlog_anchor_sec) + (float(video_time_sec) - float(video_anchor_sec))


def validate_roi(roi, frame_width, frame_height):
    if not isinstance(roi, dict):
        raise ValueError("ROI must be an object")

    frame_width = int(frame_width)
    frame_height = int(frame_height)
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Frame dimensions must be positive")

    normalized = dict(roi)
    try:
        x = float(normalized.get("x", 0))
        y = float(normalized.get("y", 0))
        width = float(normalized.get("width", 0))
        height = float(normalized.get("height", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("ROI coordinates must be numeric") from exc

    if width <= 0 or height <= 0:
        raise ValueError("ROI width and height must be positive")
    if x < 0 or y < 0 or x + width > frame_width or y + height > frame_height:
        raise ValueError("ROI must stay inside the video frame")

    normalized.update({"x": x, "y": y, "width": width, "height": height})
    normalized.setdefault("id", "roi")
    normalized.setdefault("label", "Інше")
    return normalized


def normalize_rois(rois, frame_width, frame_height):
    valid = []
    warnings = []
    for index, roi in enumerate(rois or []):
        try:
            valid.append(validate_roi(roi, frame_width, frame_height))
        except ValueError as exc:
            roi_id = roi.get("id") if isinstance(roi, dict) else None
            warnings.append(f"ROI {roi_id or index + 1}: {exc}")
    return valid, warnings


def _parse_rate(value):
    text = str(value or "0").strip()
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        try:
            denominator_value = float(denominator)
            return float(numerator) / denominator_value if denominator_value else 0.0
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def probe_video(path):
    import json
    import subprocess

    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate,r_frame_rate:format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    payload = json.loads(completed.stdout or "{}")
    streams = payload.get("streams") or []
    if not streams:
        raise ValueError("Video stream not found")
    stream = streams[0]
    duration = float((payload.get("format") or {}).get("duration") or 0.0)
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    fps = _parse_rate(stream.get("avg_frame_rate")) or _parse_rate(stream.get("r_frame_rate"))
    if duration <= 0 or width <= 0 or height <= 0:
        raise ValueError("Video metadata is incomplete")
    return {"durationSec": duration, "width": width, "height": height, "fps": fps}


def build_sample_times(duration_sec, normal_fps=1.0, dense_windows=None):
    duration = max(0.0, float(duration_sec))
    normal_fps = float(normal_fps)
    if normal_fps <= 0:
        raise ValueError("normal_fps must be positive")

    times = set()
    normal_step = 1.0 / normal_fps
    t = 0.0
    while t < duration:
        times.add(round(t, 6))
        t += normal_step
    times.add(round(duration, 6))

    dense_step = 0.25
    for window in dense_windows or []:
        if not isinstance(window, (tuple, list)) or len(window) != 2:
            continue
        start = max(0.0, min(duration, float(window[0])))
        end = max(0.0, min(duration, float(window[1])))
        if end < start:
            start, end = end, start
        t = start
        while t < end:
            times.add(round(t, 6))
            t += dense_step
        times.add(round(end, 6))

    return sorted(times)


def extract_frame(path, time_sec, output_path):
    import subprocess

    timestamp = max(0.0, float(time_sec))
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{timestamp:.6f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-y",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )


def build_observation(
    video_time_sec,
    mapped_tlog_sec,
    roi,
    kind,
    description,
    confidence,
    extracted_text=None,
):
    roi = roi or {}
    observation = {
        "videoTimeSec": round(float(video_time_sec), 3),
        "tlogTimeSec": round(float(mapped_tlog_sec), 3),
        "roiId": str(roi.get("id") or "roi"),
        "roiLabel": str(roi.get("label") or "Інше"),
        "type": str(kind or "observation"),
        "description": str(description or ""),
        "confidence": max(0.0, min(1.0, float(confidence))),
    }
    if extracted_text is not None and str(extracted_text).strip():
        observation["extractedText"] = str(extracted_text).strip()
    return observation


def correlate_observations(observations, tlog_events, max_delta_sec=2.0):
    max_delta = max(0.0, float(max_delta_sec))
    correlations = []

    normalized_events = []
    for event in tlog_events or []:
        if not isinstance(event, dict):
            continue
        try:
            event_time = float(event.get("timeSec"))
        except (TypeError, ValueError):
            continue
        normalized_events.append((event_time, event))

    for observation in observations or []:
        if not isinstance(observation, dict):
            continue
        try:
            observation_time = float(observation.get("tlogTimeSec"))
        except (TypeError, ValueError):
            continue

        candidates = []
        for event_time, event in normalized_events:
            signed_delta = event_time - observation_time
            absolute_delta = abs(signed_delta)
            if absolute_delta <= max_delta:
                candidates.append((absolute_delta, signed_delta, event))
        if not candidates:
            continue

        absolute_delta, signed_delta, event = min(candidates, key=lambda item: item[0])
        rounded_delta = round(absolute_delta, 3)
        if rounded_delta == 0:
            relation = "часово збігається"
        elif signed_delta > 0:
            relation = f"передувало TLOG-події на {rounded_delta:g} с; події часово близькі"
        else:
            relation = f"відбулося після TLOG-події на {rounded_delta:g} с; події часово близькі"

        event_type = str(event.get("type") or "TLOG")
        event_text = str(event.get("text") or "").strip()
        video_description = str(observation.get("description") or "").strip()
        summary = f"На відео: {video_description}. Це {relation} з {event_type}"
        if event_text:
            summary += f" ({event_text})"
        summary += "."

        correlations.append(
            {
                "tlogEvent": event,
                "videoObservation": observation,
                "deltaSec": rounded_delta,
                "summary": summary,
            }
        )

    return correlations
