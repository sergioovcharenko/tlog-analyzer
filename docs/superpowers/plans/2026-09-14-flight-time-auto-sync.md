# Flight Time Auto-Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically synchronize an uploaded MP4/MOV with the correct TLOG flight session by OCR-reading the OSD `Flight Time` from several cropped frames, validating that clock against media time, selecting a physically plausible ARM session, and populating the existing video↔TLOG anchors.

**Architecture:** Preserve the current `/analyze-video` endpoint and manual anchor variables. Add OCR/synchronization helpers to `backend/video_analysis.py`, reuse `flight.flightSessions` produced by the stable analyzer, make manual anchors optional only for `auto_sync=true`, and return `videoAnalysis.autoSync`. The frontend adds one special ROI (`Flight Time`), an auto-sync action, confidence/result UI, and an ambiguity chooser; successful auto-sync writes the same `videoAnchorSec` and `tlogAnchorSec` used by manual sync.

**Tech Stack:** Python 3.11, FastAPI, pymavlink, imageio-ffmpeg, `rapidocr_onnxruntime` (RapidOCR + ONNX Runtime), vanilla HTML/CSS/JavaScript, pytest, GitHub Actions, Render.

**Spec:** `docs/superpowers/specs/2026-09-14-flight-time-auto-sync-design.md`

## Global Constraints

- OCR reads only the user-drawn `Flight Time` ROI. Automatic ROI-position detection is out of scope for v1.
- Sample 7 internal frames for normal clips; use at least 3 when possible for short clips.
- Parse `HH:MM:SS` and `MM:SS`; accept only unambiguous substitutions `O→0`, `I/l/|→1`, and punctuation-as-separator.
- OSD time progression may differ from media-time progression by at most ±2.0 s between adjacent samples.
- High confidence requires at least 4 valid samples, one uniquely plausible TLOG session, and offset spread ≤ 1.0 s.
- Medium confidence requires at least 3 valid samples and offset spread ≤ 2.0 s. If multiple sessions pass physical bounds but one is clearly dominant, it may be selected only at Medium confidence.
- “Clearly dominant” means duration ≥ 1.5× the second-longest physically plausible session. Otherwise return `ambiguous` and require user confirmation.
- Low confidence never changes anchors automatically.
- Existing TLOG-only `/analyze`, manual video sync, MP4/MOV validation, FFmpeg timeout/cleanup, and ROI bounds validation must remain intact.
- Auto-sync failure must return the normal TLOG result and an inspectable failed/ambiguous `videoAnalysis.autoSync`; it must not turn a successful TLOG parse into an HTTP failure.
- The supplied `.tlog` and `.mp4` are validation inputs only. Their filename, flight number, and ROI coordinates must never appear in production code.

---

### Task 1: Add Flight Time parser, crop extraction, and OCR adapter

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/video_analysis.py`
- Create: `tests/test_flight_time_auto_sync.py`

**Interfaces:**
- Consumes: existing `_ffmpeg_executable()` and validated ROI dicts.
- Produces: `parse_flight_time_text(text) -> int | None`, `extract_frame_crop(path, time_sec, roi, output_path) -> None`, `read_flight_time_text(image_path) -> dict`.

- [ ] **Step 1: Write failing parser/OCR-adapter tests**

Create `tests/test_flight_time_auto_sync.py`:

```python
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
```

- [ ] **Step 2: Run parser/OCR test RED**

```bash
pytest tests/test_flight_time_auto_sync.py -v
```

Expected: FAIL because the parser/OCR helpers do not exist.

- [ ] **Step 3: Add the OCR dependency and implementation**

Append to `backend/requirements.txt`:

```text
rapidocr-onnxruntime
```

Add module imports to `backend/video_analysis.py`:

```python
from functools import lru_cache
import re
import subprocess
```

Add after `_ffmpeg_executable()`:

```python
_TIME_HMS_RE = re.compile(r"(?<!\d)(\d{1,2})\s*:\s*(\d{2})\s*:\s*(\d{2})(?!\d)")
_TIME_MS_RE = re.compile(r"(?<!\d)(\d{1,3})\s*:\s*(\d{2})(?!\d)")


def _normalize_ocr_time_text(text):
    value = str(text or "").upper()
    value = value.replace("O", "0")
    value = value.replace("I", "1").replace("L", "1").replace("|", "1")
    value = re.sub(r"[.;,]", ":", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_flight_time_text(text):
    value = _normalize_ocr_time_text(text)
    match = _TIME_HMS_RE.search(value)
    if match:
        hours, minutes, seconds = (int(part) for part in match.groups())
        if minutes >= 60 or seconds >= 60:
            return None
        return hours * 3600 + minutes * 60 + seconds
    match = _TIME_MS_RE.search(value)
    if match:
        minutes, seconds = (int(part) for part in match.groups())
        if seconds >= 60:
            return None
        return minutes * 60 + seconds
    return None


@lru_cache(maxsize=1)
def _get_ocr_engine():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


def read_flight_time_text(image_path):
    rows, _elapsed = _get_ocr_engine()(str(image_path))
    rows = rows or []
    tokens = []
    scores = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 3:
            continue
        text = str(row[1] or "").strip()
        if not text:
            continue
        tokens.append(text)
        try:
            scores.append(float(row[2]))
        except (TypeError, ValueError):
            scores.append(0.0)

    joined = " ".join(tokens)
    parsed = parse_flight_time_text(joined)
    confidence = min(scores) if parsed is not None and scores else 0.0
    if parsed is None:
        for text, score in zip(tokens, scores):
            parsed = parse_flight_time_text(text)
            if parsed is not None:
                joined = text
                confidence = score
                break
    return {
        "text": joined,
        "flightTimeSec": parsed,
        "confidence": max(0.0, min(1.0, float(confidence))),
    }


def extract_frame_crop(path, time_sec, roi, output_path):
    timestamp = max(0.0, float(time_sec))
    x = int(round(float(roi["x"])))
    y = int(round(float(roi["y"])))
    width = max(1, int(round(float(roi["width"]))))
    height = max(1, int(round(float(roi["height"]))))
    subprocess.run(
        [
            _ffmpeg_executable(), "-hide_banner", "-loglevel", "error",
            "-ss", f"{timestamp:.6f}", "-i", str(path), "-frames:v", "1",
            "-vf", f"crop={width}:{height}:{x}:{y},scale=iw*3:ih*3:flags=lanczos,format=gray",
            "-y", str(output_path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
```

- [ ] **Step 4: Run Task 1 tests GREEN**

```bash
pytest tests/test_flight_time_auto_sync.py tests/test_video_analysis_core.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/video_analysis.py tests/test_flight_time_auto_sync.py
git commit -m "feat: add Flight Time OCR primitives"
```

---

### Task 2: Validate the OSD clock and select a physically plausible ARM session

**Files:**
- Modify: `backend/video_analysis.py`
- Modify: `tests/test_flight_time_auto_sync.py`

**Interfaces:**
- Consumes: samples `{videoSec, flightTimeSec, ocrText, ocrConfidence}` and stable analyzer sessions `{number, armTimestamp, duration, endedArmed}`.
- Produces: `build_auto_sync_sample_times()`, `validate_flight_time_samples()`, `build_session_candidates()`, `select_session_for_samples()`.

- [ ] **Step 1: Add failing synchronization-core tests**

Append:

```python
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
```

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_flight_time_auto_sync.py -k "stable_clock or clock_reset or short_sessions or similar_long" -v
```

Expected: FAIL because the synchronization helpers do not exist.

- [ ] **Step 3: Implement sampling, validation, and session selection**

Add to `backend/video_analysis.py`:

```python
import statistics


def build_auto_sync_sample_times(duration_sec):
    duration = max(0.0, float(duration_sec))
    if duration <= 0:
        return []
    count = 7 if duration >= 6.0 else 3
    start = min(1.0, duration * 0.10)
    end = max(start, duration - min(1.0, duration * 0.10))
    return [round(start + (end - start) * i / (count - 1), 3) for i in range(count)]


def validate_flight_time_samples(samples, tolerance_sec=2.0):
    items = [dict(item) for item in samples if item.get("flightTimeSec") is not None]
    items.sort(key=lambda item: float(item["videoSec"]))
    if len(items) < 3:
        return {"valid": False, "confidence": "low", "samples": items,
                "flightMinusVideoSec": None, "offsetSpreadSec": None,
                "reason": "not_enough_samples"}
    for previous, current in zip(items, items[1:]):
        video_delta = float(current["videoSec"]) - float(previous["videoSec"])
        flight_delta = float(current["flightTimeSec"]) - float(previous["flightTimeSec"])
        if flight_delta < 0:
            return {"valid": False, "confidence": "low", "samples": items,
                    "flightMinusVideoSec": None, "offsetSpreadSec": None,
                    "reason": "flight_time_reset"}
        if abs(flight_delta - video_delta) > float(tolerance_sec):
            return {"valid": False, "confidence": "low", "samples": items,
                    "flightMinusVideoSec": None, "offsetSpreadSec": None,
                    "reason": "clock_drift"}
    offsets = [float(item["flightTimeSec"]) - float(item["videoSec"]) for item in items]
    median_offset = float(statistics.median(offsets))
    spread = max(abs(value - median_offset) for value in offsets)
    if spread > 2.0:
        confidence, valid, reason = "low", False, "offset_spread"
    elif len(items) >= 4 and spread <= 1.0:
        confidence, valid, reason = "high", True, None
    else:
        confidence, valid, reason = "medium", True, None
    return {"valid": valid, "confidence": confidence, "samples": items,
            "flightMinusVideoSec": round(median_offset, 3),
            "offsetSpreadSec": round(spread, 3), "reason": reason}


def build_session_candidates(flight_sessions):
    sessions = [item for item in (flight_sessions or []) if isinstance(item, dict)]
    if not sessions:
        return []
    base_arm = float(sessions[0]["armTimestamp"])
    return [
        {
            "number": int(session.get("number") or index + 1),
            "armTlogSec": round(float(session["armTimestamp"]) - base_arm, 3),
            "durationSec": round(max(0.0, float(session.get("duration") or 0.0)), 3),
            "endedArmed": bool(session.get("endedArmed")),
        }
        for index, session in enumerate(sessions)
    ]


def select_session_for_samples(samples, candidates, tolerance_sec=2.0, dominance_ratio=1.5):
    observed = [float(item["flightTimeSec"]) for item in samples if item.get("flightTimeSec") is not None]
    if not observed:
        return {"status": "failed", "selected": None, "candidates": [], "dominanceSelected": False}
    required_duration = max(observed)
    plausible = [dict(candidate) for candidate in candidates
                 if float(candidate.get("durationSec") or 0.0) + tolerance_sec >= required_duration]
    plausible.sort(key=lambda item: float(item["durationSec"]), reverse=True)
    if not plausible:
        return {"status": "failed", "selected": None, "candidates": [], "dominanceSelected": False}
    if len(plausible) == 1:
        return {"status": "selected", "selected": plausible[0], "candidates": plausible, "dominanceSelected": False}
    longest = float(plausible[0]["durationSec"])
    second = float(plausible[1]["durationSec"])
    if second <= 0 or longest >= second * dominance_ratio:
        return {"status": "selected", "selected": plausible[0], "candidates": plausible, "dominanceSelected": True}
    return {"status": "ambiguous", "selected": None, "candidates": plausible, "dominanceSelected": False}
```

- [ ] **Step 4: Run GREEN**

```bash
pytest tests/test_flight_time_auto_sync.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/video_analysis.py tests/test_flight_time_auto_sync.py
git commit -m "feat: validate Flight Time synchronization"
```

---

### Task 3: Build the auto-sync orchestrator

**Files:**
- Modify: `backend/video_analysis.py`
- Modify: `tests/test_flight_time_auto_sync.py`

**Interfaces:**
- Consumes: video path, probed metadata, one Flight Time ROI, stable `flightSessions`, injectable OCR function.
- Produces: `run_flight_time_auto_sync(...) -> dict` with `status`, `confidence`, candidate evidence, selected flight, anchors, samples, spread, warnings.

- [ ] **Step 1: Add failing orchestrator tests**

Append:

```python
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
```

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_flight_time_auto_sync.py -k "run_auto_sync" -v
```

Expected: FAIL because `run_flight_time_auto_sync` does not exist.

- [ ] **Step 3: Implement the orchestrator**

Add imports:

```python
from pathlib import Path
import tempfile
```

Add:

```python
def run_flight_time_auto_sync(video_path, metadata, roi, flight_sessions, ocr_reader=read_flight_time_text):
    normalized_roi = validate_roi(roi, int(metadata["width"]), int(metadata["height"]))
    samples = []
    warnings = []
    with tempfile.TemporaryDirectory(prefix="flight-time-ocr-") as temp_dir:
        for index, video_sec in enumerate(build_auto_sync_sample_times(metadata["durationSec"])):
            crop_path = Path(temp_dir) / f"flight_time_{index}.png"
            try:
                extract_frame_crop(video_path, video_sec, normalized_roi, crop_path)
                reading = ocr_reader(crop_path)
            except Exception as exc:
                warnings.append(f"OCR {video_sec:.1f} с: {exc}")
                continue
            if reading.get("flightTimeSec") is None:
                continue
            samples.append({
                "videoSec": round(float(video_sec), 3),
                "flightTimeSec": float(reading["flightTimeSec"]),
                "ocrText": str(reading.get("text") or ""),
                "ocrConfidence": round(float(reading.get("confidence") or 0.0), 3),
            })

    validation = validate_flight_time_samples(samples)
    if not validation["valid"]:
        return {"status": "failed", "confidence": "low", "selectedFlight": None,
                "armTlogSec": None, "offsetSec": None, "videoAnchorSec": None,
                "tlogAnchorSec": None, "samples": validation["samples"],
                "offsetSpreadSec": validation["offsetSpreadSec"], "candidates": [],
                "warnings": warnings + ["Не вдалося стабільно прочитати Flight Time"]}

    selection = select_session_for_samples(
        validation["samples"], build_session_candidates(flight_sessions)
    )
    flight_minus_video = float(validation["flightMinusVideoSec"])
    candidate_payloads = []
    for candidate in selection["candidates"]:
        item = dict(candidate)
        item["offsetSec"] = round(float(item["armTlogSec"]) + flight_minus_video, 3)
        candidate_payloads.append(item)

    if selection["status"] == "failed":
        return {"status": "failed", "confidence": "low", "selectedFlight": None,
                "armTlogSec": None, "offsetSec": None, "videoAnchorSec": None,
                "tlogAnchorSec": None, "samples": validation["samples"],
                "offsetSpreadSec": validation["offsetSpreadSec"], "candidates": [],
                "warnings": warnings + ["Flight Time не поміщається в жодну ARM-сесію TLOG"]}
    if selection["status"] == "ambiguous":
        return {"status": "ambiguous", "confidence": "low", "selectedFlight": None,
                "armTlogSec": None, "offsetSec": None, "videoAnchorSec": None,
                "tlogAnchorSec": None, "samples": validation["samples"],
                "offsetSpreadSec": validation["offsetSpreadSec"],
                "candidates": candidate_payloads,
                "warnings": warnings + ["Кілька ARM-сесій правдоподібні — потрібен вибір користувача"]}

    selected = selection["selected"]
    offset_sec = round(float(selected["armTlogSec"]) + flight_minus_video, 3)
    confidence = validation["confidence"]
    if selection["dominanceSelected"] and confidence == "high":
        confidence = "medium"
    mapped_samples = []
    for sample in validation["samples"]:
        item = dict(sample)
        item["mappedTlogSec"] = round(float(selected["armTlogSec"]) + float(sample["flightTimeSec"]), 3)
        mapped_samples.append(item)
    return {"status": "success", "confidence": confidence,
            "selectedFlight": int(selected["number"]),
            "armTlogSec": round(float(selected["armTlogSec"]), 3),
            "offsetSec": offset_sec, "videoAnchorSec": 0.0,
            "tlogAnchorSec": offset_sec, "samples": mapped_samples,
            "offsetSpreadSec": validation["offsetSpreadSec"],
            "candidates": candidate_payloads, "warnings": warnings}
```

- [ ] **Step 4: Run GREEN and commit**

```bash
pytest tests/test_flight_time_auto_sync.py tests/test_video_analysis_core.py -v
git add backend/video_analysis.py tests/test_flight_time_auto_sync.py
git commit -m "feat: calculate Flight Time auto-sync anchors"
```

---

### Task 4: Extend `/analyze-video` while preserving manual behavior

**Files:**
- Modify: `backend/main.py:5380-5465` (`# VIDEO_TLOG_ANALYSIS_ENDPOINT_V1`)
- Modify: `tests/test_video_analysis_api.py`

**Interfaces:**
- Request: current multipart fields plus optional `auto_sync` and `flight_time_roi_json`.
- Response: current `videoAnalysis` plus `autoSync`; successful High/Medium auto-sync populates current anchor fields.

- [ ] **Step 1: Add failing API tests**

Add a test that posts `auto_sync=true` without manual anchors and monkeypatches `run_flight_time_auto_sync()` to return:

```python
{
    "status": "success", "confidence": "high", "selectedFlight": 4,
    "armTlogSec": 185.397, "offsetSec": 470.397,
    "videoAnchorSec": 0.0, "tlogAnchorSec": 470.397,
    "samples": [], "offsetSpreadSec": 0.2, "candidates": [], "warnings": [],
}
```

Assert HTTP 200, `videoAnalysis.autoSync.status == "success"`, and both `videoAnalysis.anchor*Sec` fields equal the returned anchors. Add a second test where the helper returns `status="failed"`; assert `success is True` for the TLOG result and the failed structure remains in `videoAnalysis.autoSync`.

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_video_analysis_api.py -v
```

Expected: new request fails because anchors are currently required.

- [ ] **Step 3: Replace the endpoint signature/import block**

Use:

```python
@app.post("/analyze-video")
async def analyze_video(
    file: UploadFile = File(...),
    video: UploadFile = File(...),
    video_anchor_sec: float | None = Form(None),
    tlog_anchor_sec: float | None = Form(None),
    rois_json: str = Form("[]"),
    auto_sync: bool = Form(False),
    flight_time_roi_json: str = Form(""),
):
```

Import `run_flight_time_auto_sync` in both the `backend.video_analysis` and Render-root fallback paths.

Initialize:

```python
video_result = {
    "enabled": True,
    "videoDurationSec": None,
    "anchorVideoSec": float(video_anchor_sec) if video_anchor_sec is not None else None,
    "anchorTlogSec": float(tlog_anchor_sec) if tlog_anchor_sec is not None else None,
    "rois": [], "observations": [], "correlations": [], "warnings": [],
    "autoSync": None,
}
```

- [ ] **Step 4: Guard manual validation and add isolated auto-sync failure handling**

After `metadata = probe_video(temp_video_path)` and `duration = ...`, replace unconditional anchor checks with:

```python
if video_anchor_sec is not None:
    if not 0.0 <= float(video_anchor_sec) <= duration:
        raise ValueError("Точка синхронізації відео виходить за межі ролика")

timeline_times = []
for row in tlog_result.get("timeline") or []:
    if isinstance(row, dict):
        t_ms = _timeline_graph_time_ms(row.get("time"))
        if t_ms is not None:
            timeline_times.append(t_ms / 1000.0)
if tlog_anchor_sec is not None and timeline_times:
    if not min(timeline_times) <= float(tlog_anchor_sec) <= max(timeline_times):
        raise ValueError("Точка синхронізації TLOG виходить за межі журналу")
```

After normal ROI parsing, add:

```python
if auto_sync:
    try:
        if not flight_time_roi_json:
            raise ValueError("Для автосинхронізації намалюй зону Flight Time")
        flight_time_roi = json.loads(flight_time_roi_json)
        if not isinstance(flight_time_roi, dict):
            raise ValueError("Flight Time ROI must be a JSON object")
        auto_result = run_flight_time_auto_sync(
            temp_video_path,
            metadata,
            flight_time_roi,
            (tlog_result.get("flight") or {}).get("flightSessions") or [],
        )
    except Exception as exc:
        auto_result = {
            "status": "failed", "confidence": "low", "selectedFlight": None,
            "armTlogSec": None, "offsetSec": None, "videoAnchorSec": None,
            "tlogAnchorSec": None, "samples": [], "offsetSpreadSec": None,
            "candidates": [], "warnings": [f"Автосинхронізація недоступна: {exc}"],
        }
    video_result["autoSync"] = auto_result
    if auto_result.get("status") == "success" and auto_result.get("confidence") in {"high", "medium"}:
        video_result["anchorVideoSec"] = auto_result.get("videoAnchorSec")
        video_result["anchorTlogSec"] = auto_result.get("tlogAnchorSec")
elif video_anchor_sec is None or tlog_anchor_sec is None:
    video_result["warnings"].append("Для ручного відеоаналізу спочатку синхронізуй відео з TLOG")
```

Keep the outer video exception handler and temp-file cleanup exactly as existing safety boundaries.

- [ ] **Step 5: Run API/Render-root tests GREEN and commit**

```bash
pytest tests/test_video_analysis_api.py tests/test_flight_time_auto_sync.py tests/test_video_analysis_core.py -v
python -m py_compile backend/main.py backend/video_analysis.py
git add backend/main.py tests/test_video_analysis_api.py
git commit -m "feat: expose Flight Time auto-sync in video API"
```

---

### Task 5: Add frontend controls and reuse the existing anchor state

**Files:**
- Modify: `index.html` in `VIDEO_TLOG_ROI_CONTROLS_V1`, `VIDEO_TLOG_SYNC_V1`, and existing video JS.
- Modify: `tests/test_video_analysis_frontend.py`

**Interfaces:**
- Consumes: `selectedFile`, `videoFile`, `videoRois`, `API_BASE_URL`, existing `videoAnchorSec`, `tlogAnchorSec`, `updateVideoSyncPair()`.
- Produces: auto-sync request, confidence/status rendering, ambiguity selection, and writes only the existing anchor variables.

- [ ] **Step 1: Add failing frontend contract**

Change the ROI option expectation to:

```python
assert options == [
    "Flight Time", "Напруга АКБ", "Ампераж", "dBm", "RSSI", "VISP",
    "Режим", "Попередження", "Інше",
]
```

Add assertions for IDs `videoAutoSync`, `videoAutoSyncStatus`, `videoAutoSyncConfidence`, `videoAutoSyncCandidate`, `videoAutoSyncApplyCandidate`, the text `Автосинхронізація по Flight Time`, request field `flight_time_roi_json`, and assignments from `autoSync.videoAnchorSec` / `autoSync.tlogAnchorSec` into existing state.

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_video_analysis_frontend.py -v
```

Expected: FAIL because the controls and `Flight Time` option do not exist.

- [ ] **Step 3: Add HTML controls**

Make `Flight Time` the first ROI option. Extend the sync panel with:

```html
<button id="videoAutoSync" type="button">⚡ Автосинхронізація по Flight Time</button>
<div id="videoAutoSyncStatus">Автосинхронізація ще не запускалась.</div>
<div id="videoAutoSyncConfidence" hidden></div>
<div class="video-auto-sync-candidate-row" hidden>
  <select id="videoAutoSyncCandidate" aria-label="Політ для автосинхронізації"></select>
  <button id="videoAutoSyncApplyCandidate" type="button">Застосувати вибраний політ</button>
</div>
```

Keep the two manual buttons and `videoSyncPair` visible.

- [ ] **Step 4: Add frontend request/application logic**

Extend `VideoSyncUI` with the five new elements, then add:

```javascript
function flightTimeRoi(){
  return videoRois.find(roi=>String(roi?.label||'')==='Flight Time')||null;
}

function applyAutoSyncResult(autoSync){
  if(!autoSync||autoSync.status!=='success'||autoSync.confidence==='low')return false;
  const va=Number(autoSync.videoAnchorSec),ta=Number(autoSync.tlogAnchorSec);
  if(!Number.isFinite(va)||!Number.isFinite(ta))return false;
  videoAnchorSec=va;
  tlogAnchorSec=ta;
  updateVideoSyncPair();
  return true;
}

async function runFlightTimeAutoSync(){
  if(!selectedFile||!videoFile)throw new Error('Спочатку обери TLOG і відео');
  const roi=flightTimeRoi();
  if(!roi)throw new Error('Намалюй зону Flight Time на відео');
  VideoSyncUI.autoStatus.textContent='Читаю Flight Time на кількох кадрах…';
  const formData=new FormData();
  formData.append('file',selectedFile,selectedFile.name);
  formData.append('video',videoFile,videoFile.name);
  formData.append('auto_sync','true');
  formData.append('flight_time_roi_json',JSON.stringify(roi));
  formData.append('rois_json',JSON.stringify(videoRois));
  const response=await fetch(`${API_BASE_URL}/analyze-video`,{method:'POST',body:formData});
  if(!response.ok)throw new Error(`HTTP ${response.status}`);
  const data=await response.json();
  window.__lastAnalysisResult=data;
  renderVideoAnalysisSection(data);
  renderAutoSyncResult(data?.videoAnalysis?.autoSync||null);
}
```

`renderAutoSyncResult()` must implement exactly these branches:

```javascript
if(autoSync?.status==='success'){
  applyAutoSyncResult(autoSync);
}else if(autoSync?.status==='ambiguous'){
  // Populate candidate select from autoSync.candidates; do not touch anchors.
}else{
  // Show first warning; do not touch anchors.
}
```

Candidate application must read `data-offset` from the selected candidate and only then set:

```javascript
videoAnchorSec=0;
tlogAnchorSec=offset;
updateVideoSyncPair();
```

- [ ] **Step 5: Run frontend contract + JS syntax GREEN and commit**

```bash
pytest tests/test_video_analysis_frontend.py -v
python - <<'PY'
from pathlib import Path
import re, subprocess, tempfile
html=Path('index.html').read_text(encoding='utf-8')
script='\n'.join(re.findall(r'<script[^>]*>(.*?)</script>',html,re.S))
with tempfile.NamedTemporaryFile('w',suffix='.js',delete=False,encoding='utf-8') as f:
    f.write(script)
    name=f.name
subprocess.run(['node','--check',name],check=True)
PY
git add index.html tests/test_video_analysis_frontend.py
git commit -m "feat: add Flight Time auto-sync controls"
```

---

### Task 6: Add deterministic real-sample validation and CI coverage

**Files:**
- Create: `tools/validate_flight_time_auto_sync.py`
- Modify: `.github/workflows/video-tlog-analysis.yml`

**Interfaces:**
- Validation tool consumes an arbitrary TLOG, arbitrary video, and explicit ROI JSON; it obtains `flightSessions` by calling the production `/analyze` path, then calls the same `run_flight_time_auto_sync()` used in production.
- CI installs `backend/requirements.txt` and runs the new test file; real uploaded media stays outside git.

- [ ] **Step 1: Create a production-path validation utility**

Create `tools/validate_flight_time_auto_sync.py`:

```python
import argparse
import json
from pathlib import Path
from fastapi.testclient import TestClient
import backend.main as backend_main
from backend.video_analysis import probe_video, run_flight_time_auto_sync


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('tlog',type=Path)
    parser.add_argument('video',type=Path)
    parser.add_argument('--roi',required=True)
    args=parser.parse_args()

    client=TestClient(backend_main.app)
    with args.tlog.open('rb') as handle:
        response=client.post('/analyze',files={
            'file':(args.tlog.name,handle,'application/octet-stream')
        })
    response.raise_for_status()
    tlog_result=response.json()
    sessions=(tlog_result.get('flight') or {}).get('flightSessions') or []
    metadata=probe_video(args.video)
    result=run_flight_time_auto_sync(
        args.video, metadata, json.loads(args.roi), sessions
    )
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
```

- [ ] **Step 2: Update CI exactly**

In `.github/workflows/video-tlog-analysis.yml`:

1. Change push branches to:

```yaml
branches: [feature/video-tlog-analysis, feature/flight-time-auto-sync]
```

2. Add these paths to both `push.paths` and `pull_request.paths`:

```yaml
- 'tests/test_flight_time_auto_sync.py'
- 'tools/validate_flight_time_auto_sync.py'
```

3. Add `tests/test_flight_time_auto_sync.py` to `Run video TLOG tests`:

```yaml
python -m pytest \
  tests/test_video_analysis_core.py \
  tests/test_video_analysis_api.py \
  tests/test_video_analysis_frontend.py \
  tests/test_flight_time_auto_sync.py \
  -v
```

4. Extend syntax check to:

```yaml
run: python -m py_compile backend/main.py backend/video_analysis.py tools/validate_flight_time_auto_sync.py
```

- [ ] **Step 3: Run target tests and real sample**

The supplied video is 848×530. The visible Flight Time block in the supplied frame is covered by validation ROI `x=390, y=438, width=110, height=37`. Use that only for this local validation command:

```bash
pytest tests/test_flight_time_auto_sync.py tests/test_video_analysis_core.py tests/test_video_analysis_api.py tests/test_video_analysis_frontend.py -v
python tools/validate_flight_time_auto_sync.py \
  "/mnt/data/47 2026-09-14 11-49-46(1).tlog" \
  "/mnt/data/WhatsApp Video 2026-09-14 at 12.00.00.mp4" \
  --roi '{"id":"sample-flight-time","label":"Flight Time","x":390,"y":438,"width":110,"height":37}'
```

Expected real-sample evidence:

- OCR readings progress approximately from `00:04:45` toward `00:05:59`;
- flights 1–3 are rejected because their ~10 s durations cannot contain a 4–6 minute Flight Time;
- flight 4 is selected;
- `offsetSpreadSec <= 2.0` is required for automatic anchor application;
- if OCR spread is larger, result must be Low/failed rather than a guessed anchor.

- [ ] **Step 4: Run the workflow's existing high-value regressions**

```bash
python -m pytest \
  tests/test_report_export.py \
  tests/test_report_export_full.py \
  tests/test_report_export_runtime_vtx.py \
  tests/test_ai_reconstruction.py \
  tests/test_ai_reconstruction_frontend_contract.py \
  tests/test_ai_reconstruction_integration.py \
  tests/test_vtx_frequency_matrix.py \
  tests/test_board_messages_complete_list.py \
  tests/test_graph_board_statustext_clickable.py \
  tests/test_statustext_severity_passthrough.py \
  tests/test_map_default_flight.py \
  tests/test_frontend_flow.py \
  -v
```

Expected: PASS.

- [ ] **Step 5: Commit CI/validation changes**

```bash
git add tools/validate_flight_time_auto_sync.py .github/workflows/video-tlog-analysis.yml
git commit -m "test: validate Flight Time auto-sync pipeline"
```

- [ ] **Step 6: Final verification before PR**

```bash
pytest tests/test_flight_time_auto_sync.py tests/test_video_analysis_core.py tests/test_video_analysis_api.py tests/test_video_analysis_frontend.py -v
python -m py_compile backend/main.py backend/video_analysis.py tools/validate_flight_time_auto_sync.py
git status --short
git log --oneline --max-count=8
```

Expected: targeted tests and syntax checks PASS, working tree is clean, and `main` has not moved because implementation remains in `feature/flight-time-auto-sync` until explicit merge approval.
