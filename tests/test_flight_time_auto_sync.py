import pytest
from backend import video_analysis as va


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("00:05:05", 305),
        ("05:05", 305),
        ("Flight Time 00:04:45", 285),
        ("O0:O5:O5", 305),
        ("00.O5.O5", 305),
        ("00;05;05", 305),
        ("00:73:05", None),
        ("noise", None),
    ],
)
def test_parse_flight_time_text(text, expected):
    assert va.parse_flight_time_text(text) == expected


def test_read_flight_time_text_wraps_rapidocr(monkeypatch, tmp_path):
    class FakeEngine:
        def __call__(self, image_path):
            assert str(image_path).endswith("crop.png")
            return [
                [[[0, 0], [1, 0], [1, 1], [0, 1]], "Flight Time", 0.97],
                [[[2, 0], [3, 0], [3, 1], [2, 1]], "00:05:05", 0.96],
            ], 0.01

    monkeypatch.setattr(va, "_get_ocr_engine", lambda: FakeEngine())
    crop = tmp_path / "crop.png"
    crop.write_bytes(b"fake")
    result = va.read_flight_time_text(crop)
    assert result["flightTimeSec"] == 305
    assert "00:05:05" in result["text"]
    assert result["confidence"] == pytest.approx(0.96)


def _sample(video_sec, flight_time_sec):
    return {
        "videoSec": float(video_sec),
        "flightTimeSec": float(flight_time_sec),
        "ocrText": "00:00:00",
        "ocrConfidence": 0.95,
    }


def test_stable_clock_is_high_confidence():
    result = va.validate_flight_time_samples([
        _sample(5, 290), _sample(15, 300), _sample(25, 310), _sample(35, 320)
    ])
    assert result["valid"] is True
    assert result["confidence"] == "high"
    assert result["flightMinusVideoSec"] == pytest.approx(285.0)
    assert result["offsetSpreadSec"] == pytest.approx(0.0)


def test_clock_reset_is_low_confidence():
    result = va.validate_flight_time_samples([
        _sample(5, 290), _sample(15, 300), _sample(25, 4)
    ])
    assert result["valid"] is False
    assert result["confidence"] == "low"
    assert result["reason"] == "flight_time_reset"


def test_short_sessions_are_rejected():
    sessions = [
        {"number": 1, "armTimestamp": 1000.0, "duration": 10.0, "endedArmed": False},
        {"number": 2, "armTimestamp": 1090.193, "duration": 10.0, "endedArmed": False},
        {"number": 3, "armTimestamp": 1124.278, "duration": 10.0, "endedArmed": False},
        {"number": 4, "armTimestamp": 1185.397, "duration": 647.4, "endedArmed": True},
    ]
    result = va.select_session_for_samples(
        [_sample(5, 290), _sample(15, 300), _sample(25, 310), _sample(35, 320)],
        va.build_session_candidates(sessions),
    )
    assert result["status"] == "selected"
    assert result["selected"]["number"] == 4
    assert result["selected"]["armTlogSec"] == pytest.approx(185.397)


def test_similar_long_sessions_are_ambiguous():
    sessions = [
        {"number": 1, "armTimestamp": 1000.0, "duration": 400.0, "endedArmed": False},
        {"number": 2, "armTimestamp": 1500.0, "duration": 380.0, "endedArmed": False},
    ]
    result = va.select_session_for_samples(
        [_sample(5, 100), _sample(15, 110), _sample(25, 120)],
        va.build_session_candidates(sessions),
    )
    assert result["status"] == "ambiguous"
    assert [item["number"] for item in result["candidates"]] == [1, 2]


def test_run_auto_sync_returns_anchor_pair(monkeypatch):
    monkeypatch.setattr(va, "extract_frame_crop", lambda *args, **kwargs: None)
    values = iter([285, 297, 309, 321, 333, 345, 357])

    def fake_ocr(_path):
        value = next(values)
        return {"text": str(value), "flightTimeSec": value, "confidence": 0.96}

    sessions = [
        {"number": 1, "armTimestamp": 1000.0, "duration": 10.0, "endedArmed": False},
        {"number": 4, "armTimestamp": 1185.397, "duration": 647.4, "endedArmed": True},
    ]
    result = va.run_flight_time_auto_sync(
        "flight.mp4",
        {"durationSec": 74.0, "width": 848, "height": 530, "fps": 30.0},
        {"id": "ft", "label": "Flight Time", "x": 390, "y": 438, "width": 110, "height": 37},
        sessions,
        ocr_reader=fake_ocr,
    )
    assert result["status"] == "success"
    assert result["selectedFlight"] == 4
    assert result["videoAnchorSec"] == 0.0
    assert result["tlogAnchorSec"] == result["offsetSec"]


def test_run_auto_sync_ambiguous_never_sets_anchors(monkeypatch):
    monkeypatch.setattr(va, "extract_frame_crop", lambda *args, **kwargs: None)
    values = iter([100, 112, 124, 136, 148, 160, 172])

    def fake_ocr(_path):
        value = next(values)
        return {"text": str(value), "flightTimeSec": value, "confidence": 0.9}

    sessions = [
        {"number": 1, "armTimestamp": 1000.0, "duration": 400.0, "endedArmed": False},
        {"number": 2, "armTimestamp": 1500.0, "duration": 380.0, "endedArmed": False},
    ]
    result = va.run_flight_time_auto_sync(
        "flight.mp4",
        {"durationSec": 74.0, "width": 848, "height": 530, "fps": 30.0},
        {"id": "ft", "label": "Flight Time", "x": 390, "y": 438, "width": 110, "height": 37},
        sessions,
        ocr_reader=fake_ocr,
    )
    assert result["status"] == "ambiguous"
    assert result["confidence"] == "low"
    assert result["videoAnchorSec"] is None
    assert result["tlogAnchorSec"] is None
