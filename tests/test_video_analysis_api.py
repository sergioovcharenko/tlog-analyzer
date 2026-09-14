import json

from fastapi.testclient import TestClient
import backend.main as main


def _base_tlog_result():
    return {
        "success": True,
        "timeline": [
            {"time": "00:00.000", "eventType": "SNAPSHOT"},
            {"time": "15:00.000", "eventType": "SNAPSHOT"},
        ],
        "flight": {
            "durationText": "15 хв 0 с",
            "flightSessions": [
                {"number": 1, "armTimestamp": 1000.0, "duration": 10.0, "endedArmed": False},
                {"number": 4, "armTimestamp": 1185.397, "duration": 647.4, "endedArmed": True},
            ],
        },
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


def test_video_endpoint_auto_sync_works_without_manual_anchors(monkeypatch):
    async def fake_analyze(file):
        return _base_tlog_result()

    monkeypatch.setattr(main, "analyze", fake_analyze)

    import backend.video_analysis as va
    monkeypatch.setattr(
        va,
        "probe_video",
        lambda path: {"durationSec": 74.0, "width": 848, "height": 530, "fps": 30.0},
    )
    monkeypatch.setattr(
        va,
        "run_flight_time_auto_sync",
        lambda *args, **kwargs: {
            "status": "success",
            "confidence": "high",
            "selectedFlight": 4,
            "armTlogSec": 185.397,
            "offsetSec": 470.397,
            "videoAnchorSec": 0.0,
            "tlogAnchorSec": 470.397,
            "samples": [],
            "offsetSpreadSec": 0.2,
            "candidates": [],
            "warnings": [],
        },
    )

    client = TestClient(main.app)
    response = client.post(
        "/analyze-video",
        files={
            "file": ("flight.tlog", b"tlog", "application/octet-stream"),
            "video": ("clip.mp4", b"video", "video/mp4"),
        },
        data={
            "rois_json": "[]",
            "auto_sync": "true",
            "flight_time_roi_json": json.dumps(
                {"id": "ft", "label": "Flight Time", "x": 390, "y": 438, "width": 110, "height": 37}
            ),
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["videoAnalysis"]["autoSync"]["status"] == "success"
    assert payload["videoAnalysis"]["anchorVideoSec"] == 0.0
    assert payload["videoAnalysis"]["anchorTlogSec"] == 470.397


def test_video_endpoint_auto_sync_failure_preserves_tlog(monkeypatch):
    async def fake_analyze(file):
        return _base_tlog_result()

    monkeypatch.setattr(main, "analyze", fake_analyze)

    import backend.video_analysis as va
    monkeypatch.setattr(
        va,
        "probe_video",
        lambda path: {"durationSec": 74.0, "width": 848, "height": 530, "fps": 30.0},
    )
    monkeypatch.setattr(
        va,
        "run_flight_time_auto_sync",
        lambda *args, **kwargs: {
            "status": "failed",
            "confidence": "low",
            "selectedFlight": None,
            "armTlogSec": None,
            "offsetSec": None,
            "videoAnchorSec": None,
            "tlogAnchorSec": None,
            "samples": [],
            "offsetSpreadSec": None,
            "candidates": [],
            "warnings": ["Не вдалося стабільно прочитати Flight Time"],
        },
    )

    client = TestClient(main.app)
    response = client.post(
        "/analyze-video",
        files={
            "file": ("flight.tlog", b"tlog", "application/octet-stream"),
            "video": ("clip.mp4", b"video", "video/mp4"),
        },
        data={
            "rois_json": "[]",
            "auto_sync": "true",
            "flight_time_roi_json": json.dumps(
                {"id": "ft", "label": "Flight Time", "x": 390, "y": 438, "width": 110, "height": 37}
            ),
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["videoAnalysis"]["autoSync"]["status"] == "failed"
    assert payload["videoAnalysis"]["anchorVideoSec"] is None
    assert payload["videoAnalysis"]["anchorTlogSec"] is None


def test_video_endpoint_works_from_render_backend_root():
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    script = r'''
from fastapi.testclient import TestClient
import main
import video_analysis

async def fake_analyze(file):
    return {
        "success": True,
        "timeline": [
            {"time": "00:00.000", "eventType": "SNAPSHOT"},
            {"time": "15:00.000", "eventType": "SNAPSHOT"},
        ],
    }

main.analyze = fake_analyze
video_analysis.probe_video = lambda path: {
    "durationSec": 120.0,
    "width": 1920,
    "height": 1080,
    "fps": 30.0,
}

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
assert response.status_code == 200, response.text
assert response.json()["videoAnalysis"]["enabled"] is True
'''

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root / "backend",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
