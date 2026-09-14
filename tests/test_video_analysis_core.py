from backend.video_analysis import map_video_to_tlog_time, validate_roi, normalize_rois


def test_partial_clip_anchor_mapping():
    assert map_video_to_tlog_time(37.0, 37.0, 822.0) == 822.0
    assert map_video_to_tlog_time(0.0, 37.0, 822.0) == 785.0
    assert map_video_to_tlog_time(120.0, 37.0, 822.0) == 905.0


def test_validate_roi_accepts_rect_inside_frame():
    roi = {"id": "r1", "label": "dBm", "x": 100, "y": 50, "width": 200, "height": 80}
    assert validate_roi(roi, 1920, 1080)["label"] == "dBm"


def test_normalize_rois_rejects_zero_or_outside_rect_without_failing_all():
    rois = [
        {"id": "ok", "label": "Напруга", "x": 10, "y": 10, "width": 100, "height": 40},
        {"id": "bad", "label": "dBm", "x": 1900, "y": 10, "width": 100, "height": 40},
    ]
    valid, warnings = normalize_rois(rois, 1920, 1080)
    assert [r["id"] for r in valid] == ["ok"]
    assert warnings
