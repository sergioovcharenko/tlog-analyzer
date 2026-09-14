from fastapi.testclient import TestClient
import backend.main as main


def _base_tlog_result():
    return {
        "success": True,
        "timeline": [
            {"time": "00:00.000", "eventType": "SNAPSHOT"},
            {"time": "15:00.000", "eventType": "SNAPSHOT"},
        ],
        "flight": {"durationText": "15 хв 0 с"},
    }


def test_video_endpoint_returns_anchor_metadata(monkeypatch):
    async def fake_analyze(file):
        return _base_tlog_result()

    monkeypatch.setattr(main, "analyze", fake_analyze)

    import backend.video_analysis as va
    monkeypatch.setattr(
        va,
        "probe_video",
        lambda path: {"durationSec": 120.0, "width": 1920, "height": 1080, "fps": 30.0},
    )

    client = TestClient(main.app)
    response = client.post(
        "/analyze-video",
        files={
            "file": ("flight.tlog", b"tlog", "application/octet-stream"),
            "video": ("clip.mp4", b"video", "video/mp4"),
        },
        data={
            "video_anchor_sec": "37.0",
            "tlog_anchor_sec": "822.0",
            "rois_json": "[]",
        },
    )
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["success"] is True
    assert response_json["videoAnalysis"]["enabled"] is True
    assert response_json["videoAnalysis"]["anchorVideoSec"] == 37.0
    assert response_json["videoAnalysis"]["anchorTlogSec"] == 822.0


def test_video_decode_failure_keeps_tlog_result(monkeypatch):
    async def fake_analyze(file):
        return _base_tlog_result()

    monkeypatch.setattr(main, "analyze", fake_analyze)

    import backend.video_analysis as va

    def fail_probe(path):
        raise RuntimeError("decode failed")

    monkeypatch.setattr(va, "probe_video", fail_probe)

    client = TestClient(main.app)
    response = client.post(
        "/analyze-video",
        files={
            "file": ("flight.tlog", b"tlog", "application/octet-stream"),
            "video": ("clip.mp4", b"video", "video/mp4"),
        },
        data={
            "video_anchor_sec": "37.0",
            "tlog_anchor_sec": "822.0",
            "rois_json": "[]",
        },
    )
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["success"] is True
    assert response_json["videoAnalysis"]["enabled"] is True
    assert response_json["videoAnalysis"]["warnings"]
