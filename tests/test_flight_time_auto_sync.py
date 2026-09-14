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
