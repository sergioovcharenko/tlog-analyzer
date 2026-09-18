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


def _iter_iso_boxes(stream, start, end):
    import struct

    pos = int(start)
    stream.seek(pos)
    while pos + 8 <= end:
        stream.seek(pos)
        header = stream.read(8)
        if len(header) < 8:
            break
        size, box_type = struct.unpack(">I4s", header)
        header_size = 8
        if size == 1:
            ext = stream.read(8)
            if len(ext) < 8:
                break
            size = struct.unpack(">Q", ext)[0]
            header_size = 16
        elif size == 0:
            size = end - pos

        if size < header_size or pos + size > end:
            break

        yield box_type, pos + header_size, pos + size
        pos += size


def _find_child(stream, start, end, wanted):
    for box_type, payload_start, box_end in _iter_iso_boxes(stream, start, end):
        if box_type == wanted:
            return payload_start, box_end
    return None


def _read_mvhd_duration(stream, start, end):
    import struct

    stream.seek(start)
    head = stream.read(min(40, end - start))
    if len(head) < 20:
        return None
    version = head[0]
    if version == 1:
        if len(head) < 32:
            return None
        timescale = struct.unpack(">I", head[20:24])[0]
        duration = struct.unpack(">Q", head[24:32])[0]
    else:
        timescale = struct.unpack(">I", head[12:16])[0]
        duration = struct.unpack(">I", head[16:20])[0]
    if not timescale:
        return None
    return float(duration) / float(timescale)


def _read_tkhd_size(stream, start, end):
    import struct

    # Width and height are the final two 16.16 fixed-point values in tkhd.
    if end - start < 8:
        return None
    stream.seek(end - 8)
    raw = stream.read(8)
    if len(raw) != 8:
        return None
    width_fixed, height_fixed = struct.unpack(">II", raw)
    width = int(round(width_fixed / 65536.0))
    height = int(round(height_fixed / 65536.0))
    if width <= 0 or height <= 0:
        return None
    return width, height


def _read_mdhd_timescale(stream, start, end):
    import struct

    stream.seek(start)
    head = stream.read(min(32, end - start))
    if len(head) < 16:
        return None
    version = head[0]
    if version == 1:
        if len(head) < 24:
            return None
        return struct.unpack(">I", head[20:24])[0]
    return struct.unpack(">I", head[12:16])[0]


def _read_stts_fps(stream, start, end, timescale):
    import struct

    if not timescale:
        return 0.0
    stream.seek(start)
    head = stream.read(8)
    if len(head) < 8:
        return 0.0
    entry_count = struct.unpack(">I", head[4:8])[0]
    total_samples = 0
    total_ticks = 0
    for _ in range(min(entry_count, 100000)):
        raw = stream.read(8)
        if len(raw) < 8:
            break
        count, delta = struct.unpack(">II", raw)
        total_samples += count
        total_ticks += count * delta
    if total_samples <= 0 or total_ticks <= 0:
        return 0.0
    return float(total_samples) * float(timescale) / float(total_ticks)


def probe_video(path):
    """Read MP4/MOV metadata without FFmpeg or network access."""
    import os

    file_size = os.path.getsize(path)
    duration = None
    video_width = 0
    video_height = 0
    video_fps = 0.0

    with open(path, "rb") as stream:
        moov = _find_child(stream, 0, file_size, b"moov")
        if not moov:
            raise ValueError("MP4/MOV metadata (moov) not found")
        moov_start, moov_end = moov

        mvhd = _find_child(stream, moov_start, moov_end, b"mvhd")
        if mvhd:
            duration = _read_mvhd_duration(stream, *mvhd)

        for box_type, trak_start, trak_end in _iter_iso_boxes(stream, moov_start, moov_end):
            if box_type != b"trak":
                continue

            tkhd = _find_child(stream, trak_start, trak_end, b"tkhd")
            size = _read_tkhd_size(stream, *tkhd) if tkhd else None
            if not size:
                continue

            mdia = _find_child(stream, trak_start, trak_end, b"mdia")
            if not mdia:
                continue

            hdlr = _find_child(stream, mdia[0], mdia[1], b"hdlr")
            if hdlr:
                stream.seek(hdlr[0])
                data = stream.read(min(24, hdlr[1] - hdlr[0]))
                if len(data) >= 12 and data[8:12] != b"vide":
                    continue

            video_width, video_height = size

            mdhd = _find_child(stream, mdia[0], mdia[1], b"mdhd")
            timescale = _read_mdhd_timescale(stream, *mdhd) if mdhd else None

            minf = _find_child(stream, mdia[0], mdia[1], b"minf")
            if minf:
                stbl = _find_child(stream, minf[0], minf[1], b"stbl")
                if stbl:
                    stts = _find_child(stream, stbl[0], stbl[1], b"stts")
                    if stts:
                        video_fps = _read_stts_fps(stream, *stts, timescale)
            break

    if not duration or duration <= 0 or video_width <= 0 or video_height <= 0:
        raise ValueError("Video metadata is incomplete")

    return {
        "durationSec": float(duration),
        "width": int(video_width),
        "height": int(video_height),
        "fps": float(video_fps or 0.0),
    }


def extract_frame(path, time_sec, output_path):
    raise RuntimeError(
        "Frame extraction is not used by the current /analyze-video endpoint on Android"
    )


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
            _ffmpeg_executable(),
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
