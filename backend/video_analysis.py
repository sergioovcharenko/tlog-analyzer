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
