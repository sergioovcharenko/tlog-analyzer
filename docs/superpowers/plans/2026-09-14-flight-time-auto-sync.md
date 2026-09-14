# Flight Time Auto-Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically synchronize an uploaded MP4/MOV with the correct TLOG flight session by OCR-reading the OSD `Flight Time` value from multiple cropped frames, validating the clock progression, selecting a physically plausible ARM session, and populating the existing video↔TLOG anchors.

**Architecture:** Keep the existing `/analyze-video` flow and manual anchor state. Add isolated OCR/synchronization helpers to `backend/video_analysis.py`, reuse `flight.flightSessions` from the stable TLOG analyzer, make manual anchors optional only when `auto_sync=true`, and return an inspectable `videoAnalysis.autoSync` result. The frontend adds a `Flight Time` ROI, an auto-sync action, confidence/result UI, and an ambiguity chooser; successful auto-sync writes the same `videoAnchorSec`/`tlogAnchorSec` variables already used by manual synchronization.

**Tech Stack:** Python 3, FastAPI, pymavlink, imageio-ffmpeg, RapidOCR via `rapidocr_onnxruntime`, ONNX Runtime, vanilla HTML/CSS/JavaScript, pytest, GitHub Actions/Render.

**Spec:** `docs/superpowers/specs/2026-09-14-flight-time-auto-sync-design.md`

## Global Constraints

- OCR runs only on the user-supplied `Flight Time` ROI; automatic ROI-position detection is out of scope for v1.
- Sample exactly 7 useful frames for ordinary clips, reducing to at least 3 when possible for short clips.
- Accept `HH:MM:SS` and `MM:SS`; accept only unambiguous OCR substitutions (`O→0`, `I/l/|→1`, punctuation-as-separator).
- Adjacent OSD-time progression may differ from media-time progression by at most ±2.0 s.
- High confidence: at least 4 valid OCR samples, one unambiguous selected TLOG session, offset spread ≤ 1.0 s.
- Medium confidence: at least 3 valid OCR samples, one selected TLOG session, offset spread > 1.0 s and ≤ 2.0 s.
- Low confidence never changes anchors automatically.
- A clearly dominant session means its duration is at least 1.5× the next-longest physically plausible session; this resolves the spec's “clearly dominant” rule. A dominance-based selection is capped at Medium confidence because more than one session passed the physical-bounds filter.
- Manual sync and ordinary TLOG-only `/analyze` behavior remain unchanged.
- Auto-sync failure must return the normal TLOG result plus an explanatory `videoAnalysis.autoSync` failure/ambiguity structure.
- MP4/MOV limits, temporary-file cleanup, FFmpeg timeouts, and existing ROI validation remain in force.
- The provided real pair is validation data only; no filename, timestamp, ROI coordinate, or flight number may be hard-coded in production code.

---

### Task 1: Add Flight Time OCR primitives and dependency

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/video_analysis.py`
- Create: `tests/test_flight_time_auto_sync.py`

**Interfaces:**
- Consumes: existing `validate_roi()`, `_ffmpeg_executable()` and video frame dimensions.
- Produces: `parse_flight_time_text(text) -> int | None`, `extract_frame_crop(video_path, time_sec, roi, output_path) -> None`, `read_flight_time_text(image_path) -> dict`.

- [ ] **Step 1: Write failing parser and crop/OCR-isolation tests**

Add `tests/test_flight_time_auto_sync.py`:

```python
import pytest

from backend import video_analysis as va


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("00:05:05", 305),
        ("05:05", 305),
        ("Flight Time 00:04:45", 285),
        ("00.O5.O5", 305),
        ("O0:O5:O5", 305),
        ("00;05;05", 305),
        ("001I05", None),
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


def test_extract_frame_crop_uses_validated_roi(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)

    monkeypatch.setattr(va.subprocess, "run", fake_run)
    out = tmp_path / "crop.png"
    va.extract_frame_crop(
        "video.mp4",
        12.5,
        {"id": "ft", "label": "Flight Time", "x": 100, "y": 50, "width": 220, "height": 48},
        out,
    )
    command = calls[0]
    assert "-ss" in command
    assert "12.500000" in command
    vf = command[command.index("-vf") + 1]
    assert "crop=220:48:100:50" in vf
    assert "scale=iw*3:ih*3" in vf
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
pytest tests/test_flight_time_auto_sync.py -v
```

Expected: collection/test failures because `parse_flight_time_text`, `_get_ocr_engine`, `read_flight_time_text`, and `extract_frame_crop` do not exist yet.

- [ ] **Step 3: Add RapidOCR dependency and minimal OCR helpers**

Append to `backend/requirements.txt`:

```text
rapidocr-onnxruntime
```

At the top of `backend/video_analysis.py`, add imports used by the new helpers:

```python
from functools import lru_cache
from pathlib import Path
import re
import subprocess
```

Add these helpers after `_ffmpeg_executable()`:

```python
_TIME_HMS_RE = re.compile(r"(?<!\d)(\d{1,2})\s*:\s*(\d{2})\s*:\s*(\d{2})(?!\d)")
_TIME_MS_RE = re.compile(r"(?<!\d)(\d{1,3})\s*:\s*(\d{2})(?!\d)")


def _normalize_ocr_time_text(text):
    normalized = str(text or "").upper()
    normalized = normalized.replace("O", "0")
    normalized = normalized.replace("I", "1").replace("L", "1").replace("|", "1")
    normalized = re.sub(r"[.;,]", ":", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def parse_flight_time_text(text):
    normalized = _normalize_ocr_time_text(text)
    match = _TIME_HMS_RE.search(normalized)
    if match:
        hours, minutes, seconds = (int(value) for value in match.groups())
        if minutes >= 60 or seconds >= 60:
            return None
        return hours * 3600 + minutes * 60 + seconds

    match = _TIME_MS_RE.search(normalized)
    if match:
        minutes, seconds = (int(value) for value in match.groups())
        if seconds >= 60:
            return None
        return minutes * 60 + seconds
    return None


@lru_cache(maxsize=1)
def _get_ocr_engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def read_flight_time_text(image_path):
    engine = _get_ocr_engine()
    rows, _elapsed = engine(str(image_path))
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
    x = int(round(float(roi["x"])))
    y = int(round(float(roi["y"])))
    width = max(1, int(round(float(roi["width"]))))
    height = max(1, int(round(float(roi["height"]))))
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
            "-vf",
            f"crop={width}:{height}:{x}:{y},scale=iw*3:ih*3:flags=lanczos,format=gray",
            "-y",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
```

Keep the existing `extract_frame()` function intact for other video-analysis uses.

- [ ] **Step 4: Run OCR primitive tests GREEN and existing video core tests**

Run:

```bash
pytest tests/test_flight_time_auto_sync.py tests/test_video_analysis_core.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit OCR primitives**

```bash
git add backend/requirements.txt backend/video_analysis.py tests/test_flight_time_auto_sync.py
git commit -m "feat: add Flight Time OCR primitives"
```

---

### Task 2: Validate OSD clock progression and rank TLOG flight sessions

**Files:**
- Modify: `backend/video_analysis.py`
- Modify: `tests/test_flight_time_auto_sync.py`

**Interfaces:**
- Consumes: OCR samples shaped as `{videoSec, flightTimeSec, ocrText, ocrConfidence}` and existing `flight.flightSessions` objects containing `number`, `armTimestamp`, `endTimestamp`, `duration`, `endedArmed`.
- Produces: `build_auto_sync_sample_times(duration_sec) -> list[float]`, `validate_flight_time_samples(samples) -> dict`, `build_session_candidates(flight_sessions) -> list[dict]`, `select_session_for_samples(samples, candidates) -> dict`.

- [ ] **Step 1: Add failing clock-validation and session-selection tests**

Append to `tests/test_flight_time_auto_sync.py`:

```python
def _sample(video_sec, flight_time_sec):
    return {
        "videoSec": float(video_sec),
        "flightTimeSec": float(flight_time_sec),
        "ocrText": "00:00:00",
        "ocrConfidence": 0.95,
    }


def test_build_auto_sync_sample_times_returns_seven_internal_points():
    times = va.build_auto_sync_sample_times(74.0)
    assert len(times) == 7
    assert times == sorted(times)
    assert 0.0 < times[0] < times[-1] < 74.0


def test_validate_flight_time_samples_accepts_stable_clock():
    result = va.validate_flight_time_samples([
        _sample(5, 290),
        _sample(15, 300),
        _sample(25, 310),
        _sample(35, 320),
    ])
    assert result["valid"] is True
    assert result["confidence"] == "high"
    assert result["flightMinusVideoSec"] == pytest.approx(285.0)
    assert result["offsetSpreadSec"] == pytest.approx(0.0)


def test_validate_flight_time_samples_rejects_reset_or_large_drift():
    reset = va.validate_flight_time_samples([
        _sample(5, 290), _sample(15, 300), _sample(25, 4)
    ])
    drift = va.validate_flight_time_samples([
        _sample(5, 290), _sample(15, 306), _sample(25, 316)
    ])
    assert reset["valid"] is False
    assert reset["confidence"] == "low"
    assert drift["valid"] is False


def test_short_sessions_are_rejected_by_observed_flight_time():
    sessions = [
        {"number": 1, "armTimestamp": 1000.0, "endTimestamp": 1010.0, "duration": 10.0, "endedArmed": False},
        {"number": 2, "armTimestamp": 1100.0, "endTimestamp": 1111.0, "duration": 11.0, "endedArmed": False},
        {"number": 4, "armTimestamp": 1185.397, "endTimestamp": 1600.0, "duration": 414.603, "endedArmed": True},
    ]
    candidates = va.build_session_candidates(sessions)
    selected = va.select_session_for_samples(
        [_sample(5, 290), _sample(15, 300), _sample(25, 310), _sample(35, 320)],
        candidates,
    )
    assert selected["status"] == "selected"
    assert selected["selected"]["number"] == 4
    assert selected["selected"]["armTlogSec"] == pytest.approx(185.397)


def test_similarly_long_plausible_sessions_are_ambiguous():
    sessions = [
        {"number": 1, "armTimestamp": 1000.0, "endTimestamp": 1400.0, "duration": 400.0, "endedArmed": False},
        {"number": 2, "armTimestamp": 1500.0, "endTimestamp": 1880.0, "duration": 380.0, "endedArmed": False},
    ]
    result = va.select_session_for_samples(
        [_sample(5, 100), _sample(15, 110), _sample(25, 120)],
        va.build_session_candidates(sessions),
    )
    assert result["status"] == "ambiguous"
    assert [item["number"] for item in result["candidates"]] == [1, 2]
```

- [ ] **Step 2: Run targeted tests RED**

```bash
pytest tests/test_flight_time_auto_sync.py -k "sample_times or validate_flight or sessions or ambiguous" -v
```

Expected: FAIL because the four synchronization helpers do not exist.

- [ ] **Step 3: Implement deterministic sampling, validation, and session bounds**

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
    if count == 1 or end <= start:
        return [round(duration / 2.0, 3)]
    return [round(start + (end - start) * i / (count - 1), 3) for i in range(count)]


def validate_flight_time_samples(samples, tolerance_sec=2.0):
    valid_samples = [
        dict(item)
        for item in (samples or [])
        if isinstance(item, dict)
        and item.get("flightTimeSec") is not None
        and item.get("videoSec") is not None
    ]
    valid_samples.sort(key=lambda item: float(item["videoSec"]))
    if len(valid_samples) < 3:
        return {
            "valid": False,
            "confidence": "low",
            "samples": valid_samples,
            "flightMinusVideoSec": None,
            "offsetSpreadSec": None,
            "reason": "not_enough_samples",
        }

    for previous, current in zip(valid_samples, valid_samples[1:]):
        video_delta = float(current["videoSec"]) - float(previous["videoSec"])
        flight_delta = float(current["flightTimeSec"]) - float(previous["flightTimeSec"])
        if flight_delta < 0:
            return {
                "valid": False,
                "confidence": "low",
                "samples": valid_samples,
                "flightMinusVideoSec": None,
                "offsetSpreadSec": None,
                "reason": "flight_time_reset",
            }
        if abs(flight_delta - video_delta) > float(tolerance_sec):
            return {
                "valid": False,
                "confidence": "low",
                "samples": valid_samples,
                "flightMinusVideoSec": None,
                "offsetSpreadSec": None,
                "reason": "clock_drift",
            }

    relative_offsets = [
        float(item["flightTimeSec"]) - float(item["videoSec"])
        for item in valid_samples
    ]
    median_offset = float(statistics.median(relative_offsets))
    spread = max(abs(value - median_offset) for value in relative_offsets)
    if spread > 2.0:
        confidence = "low"
        is_valid = False
    elif len(valid_samples) >= 4 and spread <= 1.0:
        confidence = "high"
        is_valid = True
    else:
        confidence = "medium"
        is_valid = True
    return {
        "valid": is_valid,
        "confidence": confidence,
        "samples": valid_samples,
        "flightMinusVideoSec": round(median_offset, 3),
        "offsetSpreadSec": round(spread, 3),
        "reason": None if is_valid else "offset_spread",
    }


def build_session_candidates(flight_sessions):
    sessions = [item for item in (flight_sessions or []) if isinstance(item, dict)]
    if not sessions:
        return []
    base_arm = float(sessions[0]["armTimestamp"])
    candidates = []
    for session in sessions:
        arm_abs = float(session["armTimestamp"])
        duration = max(0.0, float(session.get("duration") or 0.0))
        candidates.append({
            "number": int(session.get("number") or len(candidates) + 1),
            "armTlogSec": round(arm_abs - base_arm, 3),
            "durationSec": round(duration, 3),
            "endedArmed": bool(session.get("endedArmed")),
        })
    return candidates


def select_session_for_samples(samples, candidates, tolerance_sec=2.0, dominance_ratio=1.5):
    observed = [float(item["flightTimeSec"]) for item in samples if item.get("flightTimeSec") is not None]
    if not observed:
        return {"status": "failed", "selected": None, "candidates": []}
    required_duration = max(observed)
    plausible = [
        dict(candidate)
        for candidate in candidates
        if float(candidate.get("durationSec") or 0.0) + float(tolerance_sec) >= required_duration
    ]
    plausible.sort(key=lambda item: float(item["durationSec"]), reverse=True)
    if not plausible:
        return {"status": "failed", "selected": None, "candidates": []}
    if len(plausible) == 1:
        return {"status": "selected", "selected": plausible[0], "candidates": plausible, "dominanceSelected": False}

    longest = float(plausible[0]["durationSec"])
    second = float(plausible[1]["durationSec"])
    if second <= 0.0 or longest >= second * float(dominance_ratio):
        return {"status": "selected", "selected": plausible[0], "candidates": plausible, "dominanceSelected": True}
    return {"status": "ambiguous", "selected": None, "candidates": plausible, "dominanceSelected": False}
```

- [ ] **Step 4: Run synchronization-core tests GREEN**

```bash
pytest tests/test_flight_time_auto_sync.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit synchronization core**

```bash
git add backend/video_analysis.py tests/test_flight_time_auto_sync.py
git commit -m "feat: validate Flight Time synchronization"
```

---

### Task 3: Build the bounded OCR auto-sync orchestrator

**Files:**
- Modify: `backend/video_analysis.py`
- Modify: `tests/test_flight_time_auto_sync.py`

**Interfaces:**
- Consumes: video path, probed metadata, validated `Flight Time` ROI, `flightSessions`, and injectable OCR reader.
- Produces: `run_flight_time_auto_sync(video_path, metadata, roi, flight_sessions, ocr_reader=read_flight_time_text) -> dict` with `status`, `confidence`, `selectedFlight`, anchors, samples, candidate list, spread, and warnings.

- [ ] **Step 1: Add failing orchestration tests with OCR injected**

Append:

```python
def test_run_auto_sync_returns_existing_anchor_shape(monkeypatch, tmp_path):
    monkeypatch.setattr(va, "extract_frame_crop", lambda *args, **kwargs: None)

    values = iter([285, 297, 309, 321, 333, 345, 357])
    def fake_ocr(_path):
        value = next(values)
        minutes, seconds = divmod(value, 60)
        return {
            "text": f"00:{minutes:02d}:{seconds:02d}",
            "flightTimeSec": value,
            "confidence": 0.96,
        }

    sessions = [
        {"number": 1, "armTimestamp": 1000.0, "duration": 10.0, "endedArmed": False},
        {"number": 4, "armTimestamp": 1185.397, "duration": 500.0, "endedArmed": True},
    ]
    result = va.run_flight_time_auto_sync(
        "flight.mp4",
        {"durationSec": 74.0, "width": 1920, "height": 1080, "fps": 30.0},
        {"id": "ft", "label": "Flight Time", "x": 100, "y": 50, "width": 220, "height": 48},
        sessions,
        ocr_reader=fake_ocr,
    )
    assert result["status"] == "success"
    assert result["selectedFlight"] == 4
    assert result["videoAnchorSec"] == 0.0
    assert result["tlogAnchorSec"] == result["offsetSec"]
    assert result["confidence"] in {"high", "medium"}
    assert len(result["samples"]) == 7


def test_run_auto_sync_ambiguous_does_not_return_anchors(monkeypatch):
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
        {"durationSec": 74.0, "width": 1920, "height": 1080, "fps": 30.0},
        {"id": "ft", "label": "Flight Time", "x": 1, "y": 1, "width": 100, "height": 30},
        sessions,
        ocr_reader=fake_ocr,
    )
    assert result["status"] == "ambiguous"
    assert result["confidence"] == "low"
    assert result["videoAnchorSec"] is None
    assert result["tlogAnchorSec"] is None
    assert len(result["candidates"]) == 2
```

- [ ] **Step 2: Run orchestration tests RED**

```bash
pytest tests/test_flight_time_auto_sync.py -k "run_auto_sync" -v
```

Expected: FAIL because `run_flight_time_auto_sync` is undefined.

- [ ] **Step 3: Implement the orchestration function with temp-crop cleanup**

Add to `backend/video_analysis.py`:

```python
import tempfile


def run_flight_time_auto_sync(video_path, metadata, roi, flight_sessions, ocr_reader=read_flight_time_text):
    normalized_roi = validate_roi(roi, int(metadata["width"]), int(metadata["height"]))
    sample_times = build_auto_sync_sample_times(float(metadata["durationSec"]))
    samples = []
    warnings = []

    with tempfile.TemporaryDirectory(prefix="flight-time-ocr-") as temp_dir:
        for index, video_sec in enumerate(sample_times):
            crop_path = Path(temp_dir) / f"flight_time_{index}.png"
            try:
                extract_frame_crop(video_path, video_sec, normalized_roi, crop_path)
                reading = ocr_reader(crop_path)
            except Exception as exc:
                warnings.append(f"OCR {video_sec:.1f} с: {exc}")
                continue
            flight_time_sec = reading.get("flightTimeSec")
            if flight_time_sec is None:
                continue
            samples.append({
                "videoSec": round(float(video_sec), 3),
                "flightTimeSec": float(flight_time_sec),
                "ocrText": str(reading.get("text") or ""),
                "ocrConfidence": round(float(reading.get("confidence") or 0.0), 3),
            })

    validation = validate_flight_time_samples(samples)
    if not validation["valid"]:
        return {
            "status": "failed",
            "confidence": "low",
            "selectedFlight": None,
            "armTlogSec": None,
            "offsetSec": None,
            "videoAnchorSec": None,
            "tlogAnchorSec": None,
            "samples": validation["samples"],
            "offsetSpreadSec": validation["offsetSpreadSec"],
            "candidates": [],
            "warnings": warnings + ["Не вдалося стабільно прочитати Flight Time"],
        }

    candidates = build_session_candidates(flight_sessions)
    selection = select_session_for_samples(validation["samples"], candidates)
    if selection["status"] == "failed":
        return {
            "status": "failed",
            "confidence": "low",
            "selectedFlight": None,
            "armTlogSec": None,
            "offsetSec": None,
            "videoAnchorSec": None,
            "tlogAnchorSec": None,
            "samples": validation["samples"],
            "offsetSpreadSec": validation["offsetSpreadSec"],
            "candidates": [],
            "warnings": warnings + ["Flight Time не поміщається в жодну ARM-сесію TLOG"],
        }

    flight_minus_video = float(validation["flightMinusVideoSec"])
    candidate_payloads = []
    for candidate in selection["candidates"]:
        item = dict(candidate)
        item["offsetSec"] = round(float(candidate["armTlogSec"]) + flight_minus_video, 3)
        candidate_payloads.append(item)

    if selection["status"] == "ambiguous":
        return {
            "status": "ambiguous",
            "confidence": "low",
            "selectedFlight": None,
            "armTlogSec": None,
            "offsetSec": None,
            "videoAnchorSec": None,
            "tlogAnchorSec": None,
            "samples": validation["samples"],
            "offsetSpreadSec": validation["offsetSpreadSec"],
            "candidates": candidate_payloads,
            "warnings": warnings + ["Кілька ARM-сесій однаково правдоподібні — потрібен вибір користувача"],
        }

    selected = selection["selected"]
    offset_sec = round(float(selected["armTlogSec"]) + flight_minus_video, 3)
    confidence = validation["confidence"]
    if selection.get("dominanceSelected") and confidence == "high":
        confidence = "medium"

    mapped_samples = []
    for sample in validation["samples"]:
        mapped = dict(sample)
        mapped["mappedTlogSec"] = round(float(selected["armTlogSec"]) + float(sample["flightTimeSec"]), 3)
        mapped_samples.append(mapped)

    return {
        "status": "success",
        "confidence": confidence,
        "selectedFlight": int(selected["number"]),
        "armTlogSec": round(float(selected["armTlogSec"]), 3),
        "offsetSec": offset_sec,
        "videoAnchorSec": 0.0,
        "tlogAnchorSec": offset_sec,
        "samples": mapped_samples,
        "offsetSpreadSec": validation["offsetSpreadSec"],
        "candidates": candidate_payloads,
        "warnings": warnings,
    }
```

- [ ] **Step 4: Run all auto-sync core tests**

```bash
pytest tests/test_flight_time_auto_sync.py tests/test_video_analysis_core.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit orchestrator**

```bash
git add backend/video_analysis.py tests/test_flight_time_auto_sync.py
git commit -m "feat: calculate Flight Time auto-sync anchors"
```

---

### Task 4: Extend `/analyze-video` without breaking manual synchronization

**Files:**
- Modify: `backend/main.py` at `# VIDEO_TLOG_ANALYSIS_ENDPOINT_V1`
- Modify: `tests/test_video_analysis_api.py`

**Interfaces:**
- Consumes: multipart fields `file`, `video`, optional `video_anchor_sec`, optional `tlog_anchor_sec`, `rois_json`, `auto_sync`, optional `flight_time_roi_json`.
- Produces: existing `videoAnalysis` plus optional `videoAnalysis.autoSync`; manual requests remain byte-for-byte compatible in their existing anchor fields.

- [ ] **Step 1: Add failing API tests for optional anchors and auto-sync**

Append to `tests/test_video_analysis_api.py`:

```python
def test_video_endpoint_auto_sync_does_not_require_manual_anchors(monkeypatch):
    async def fake_analyze(file):
        result = _base_tlog_result()
        result["flight"]["flightSessions"] = [
            {"number": 1, "armTimestamp": 1000.0, "duration": 500.0, "endedArmed": True}
        ]
        return result

    monkeypatch.setattr(main, "analyze", fake_analyze)
    import backend.video_analysis as va
    monkeypatch.setattr(va, "probe_video", lambda path: {
        "durationSec": 74.0, "width": 1920, "height": 1080, "fps": 30.0
    })
    monkeypatch.setattr(va, "run_flight_time_auto_sync", lambda *args, **kwargs: {
        "status": "success",
        "confidence": "high",
        "selectedFlight": 1,
        "armTlogSec": 0.0,
        "offsetSec": 285.0,
        "videoAnchorSec": 0.0,
        "tlogAnchorSec": 285.0,
        "samples": [],
        "offsetSpreadSec": 0.2,
        "candidates": [],
        "warnings": [],
    })

    client = TestClient(main.app)
    response = client.post(
        "/analyze-video",
        files={
            "file": ("flight.tlog", b"tlog", "application/octet-stream"),
            "video": ("clip.mp4", b"video", "video/mp4"),
        },
        data={
            "auto_sync": "true",
            "flight_time_roi_json": '{"id":"ft","label":"Flight Time","x":100,"y":50,"width":220,"height":48}',
            "rois_json": "[]",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["videoAnalysis"]["autoSync"]["status"] == "success"
    assert body["videoAnalysis"]["anchorVideoSec"] == 0.0
    assert body["videoAnalysis"]["anchorTlogSec"] == 285.0


def test_auto_sync_failure_preserves_tlog_result(monkeypatch):
    async def fake_analyze(file):
        return _base_tlog_result()

    monkeypatch.setattr(main, "analyze", fake_analyze)
    import backend.video_analysis as va
    monkeypatch.setattr(va, "probe_video", lambda path: {
        "durationSec": 74.0, "width": 1920, "height": 1080, "fps": 30.0
    })
    monkeypatch.setattr(va, "run_flight_time_auto_sync", lambda *args, **kwargs: {
        "status": "failed", "confidence": "low", "warnings": ["OCR failed"]
    })

    client = TestClient(main.app)
    response = client.post(
        "/analyze-video",
        files={
            "file": ("flight.tlog", b"tlog", "application/octet-stream"),
            "video": ("clip.mp4", b"video", "video/mp4"),
        },
        data={
            "auto_sync": "true",
            "flight_time_roi_json": '{"id":"ft","label":"Flight Time","x":100,"y":50,"width":220,"height":48}',
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["videoAnalysis"]["autoSync"]["status"] == "failed"
```

Also extend `test_video_endpoint_works_from_render_backend_root()` so its embedded request still verifies the Render-root import path after the new dependency and optional form fields are added.

- [ ] **Step 2: Run API tests RED**

```bash
pytest tests/test_video_analysis_api.py -v
```

Expected: the new auto-sync request returns validation error 422 because manual anchors are still required, or fails because auto-sync fields/handler do not exist.

- [ ] **Step 3: Make endpoint form contract backward-compatible**

At `# VIDEO_TLOG_ANALYSIS_ENDPOINT_V1`, change the signature to:

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

Extend the existing Render-safe import block:

```python
try:
    from backend.video_analysis import (
        build_sample_times,
        normalize_rois,
        probe_video,
        run_flight_time_auto_sync,
    )
except ImportError:
    from video_analysis import (
        build_sample_times,
        normalize_rois,
        probe_video,
        run_flight_time_auto_sync,
    )
```

Initialize anchors without converting `None`:

```python
video_result = {
    "enabled": True,
    "videoDurationSec": None,
    "anchorVideoSec": float(video_anchor_sec) if video_anchor_sec is not None else None,
    "anchorTlogSec": float(tlog_anchor_sec) if tlog_anchor_sec is not None else None,
    "rois": [],
    "observations": [],
    "correlations": [],
    "warnings": [],
    "autoSync": None,
}
```

After `metadata = probe_video(...)` and ROI normalization, preserve current manual validation only when both anchors are present. Then add the auto-sync branch:

```python
if auto_sync:
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
    video_result["autoSync"] = auto_result
    if auto_result.get("status") == "success" and auto_result.get("confidence") in {"high", "medium"}:
        video_result["anchorVideoSec"] = auto_result.get("videoAnchorSec")
        video_result["anchorTlogSec"] = auto_result.get("tlogAnchorSec")
elif video_anchor_sec is None or tlog_anchor_sec is None:
    video_result["warnings"].append("Для ручного відеоаналізу спочатку синхронізуй відео з TLOG")
```

Do not remove the existing MP4/MOV checks, `probe_video`, `normalize_rois`, sample-count metadata, exception isolation, or temp-file cleanup.

- [ ] **Step 4: Run API + Render-root + core regression tests GREEN**

```bash
pytest tests/test_video_analysis_api.py tests/test_flight_time_auto_sync.py tests/test_video_analysis_core.py -v
python -m py_compile backend/main.py backend/video_analysis.py
```

Expected: PASS and no syntax errors.

- [ ] **Step 5: Commit API integration**

```bash
git add backend/main.py tests/test_video_analysis_api.py
git commit -m "feat: expose Flight Time auto-sync in video API"
```

---

### Task 5: Add auto-sync controls and reuse the existing manual anchor state

**Files:**
- Modify: `index.html` in the existing `VIDEO_TLOG_ROI_CONTROLS_V1`, `VIDEO_TLOG_SYNC_V1`, and video frontend JS sections.
- Modify: `tests/test_video_analysis_frontend.py`

**Interfaces:**
- Consumes: `selectedFile`, `videoFile`, `videoRois`, `API_BASE_URL`, and existing `videoAnchorSec` / `tlogAnchorSec` / `updateVideoSyncPair()`.
- Produces: `runFlightTimeAutoSync()`, `applyAutoSyncResult(autoSync)`, ambiguity chooser, status/confidence text, and the same anchor variables used by manual sync.

- [ ] **Step 1: Add failing frontend-contract tests**

Update the exact ROI option expectation in `tests/test_video_analysis_frontend.py` to:

```python
assert options == [
    "Flight Time",
    "Напруга АКБ",
    "Ампераж",
    "dBm",
    "RSSI",
    "VISP",
    "Режим",
    "Попередження",
    "Інше",
]
```

Add:

```python
def test_flight_time_auto_sync_controls_exist():
    assert 'id="videoAutoSync"' in HTML
    assert 'id="videoAutoSyncStatus"' in HTML
    assert 'id="videoAutoSyncConfidence"' in HTML
    assert 'id="videoAutoSyncCandidate"' in HTML
    assert 'id="videoAutoSyncApplyCandidate"' in HTML
    assert "Автосинхронізація по Flight Time" in HTML


def test_auto_sync_posts_roi_and_reuses_manual_anchor_state():
    assert "runFlightTimeAutoSync" in HTML
    assert "flight_time_roi_json" in HTML
    assert "formData.append('auto_sync','true')" in HTML or 'formData.append("auto_sync","true")' in HTML
    assert "autoSync.videoAnchorSec" in HTML
    assert "autoSync.tlogAnchorSec" in HTML
    assert "videoAnchorSec=" in HTML
    assert "tlogAnchorSec=" in HTML
    assert "updateVideoSyncPair()" in HTML


def test_low_confidence_does_not_overwrite_anchors():
    assert "autoSync.confidence==='low'" in HTML or 'autoSync.confidence === "low"' in HTML
    assert "status==='ambiguous'" in HTML or 'status === "ambiguous"' in HTML
```

- [ ] **Step 2: Run frontend contract RED**

```bash
pytest tests/test_video_analysis_frontend.py -v
```

Expected: FAIL because `Flight Time` and auto-sync UI/JS are absent.

- [ ] **Step 3: Add the `Flight Time` ROI and auto-sync UI**

Change the ROI `<select>` so `Flight Time` is the first option:

```html
<select id="videoRoiLabel" aria-label="Тип зони відео">
  <option>Flight Time</option>
  <option>Напруга АКБ</option>
  <option>Ампераж</option>
  <option>dBm</option>
  <option>RSSI</option>
  <option>VISP</option>
  <option>Режим</option>
  <option>Попередження</option>
  <option>Інше</option>
</select>
```

Extend `VIDEO_TLOG_SYNC_V1`:

```html
<div class="video-sync-actions">
  <button id="videoAutoSync" type="button">⚡ Автосинхронізація по Flight Time</button>
  <button id="videoSetAnchor" type="button">⏱ Взяти поточний час відео</button>
  <button id="tlogSelectAnchor" type="button">🎯 Вибрати момент TLOG</button>
</div>
<div id="videoAutoSyncStatus">Автосинхронізація ще не запускалась.</div>
<div id="videoAutoSyncConfidence" hidden></div>
<div class="video-auto-sync-candidate-row" hidden>
  <select id="videoAutoSyncCandidate" aria-label="Політ для автосинхронізації"></select>
  <button id="videoAutoSyncApplyCandidate" type="button">Застосувати вибраний політ</button>
</div>
<div id="videoSyncPair">відео — ↔ TLOG —</div>
```

Add the new elements to `VideoSyncUI`.

- [ ] **Step 4: Implement frontend auto-sync request and safe application**

Add JS next to the existing manual sync code:

```javascript
function flightTimeRoi(){
  return videoRois.find(roi=>String(roi?.label||'')==='Flight Time')||null;
}

function autoSyncConfidenceLabel(value){
  return value==='high'?'висока':value==='medium'?'середня':'низька';
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

function renderAutoSyncResult(autoSync){
  if(!VideoSyncUI.autoStatus)return;
  const candidateRow=VideoSyncUI.candidate?.closest('.video-auto-sync-candidate-row');
  if(candidateRow)candidateRow.hidden=true;
  if(VideoSyncUI.confidence)VideoSyncUI.confidence.hidden=true;

  if(!autoSync){
    VideoSyncUI.autoStatus.textContent='Автосинхронізація не повернула результат.';
    return;
  }
  if(autoSync.status==='success'){
    const sample=(autoSync.samples||[])[0]||{};
    VideoSyncUI.autoStatus.textContent=`Flight Time ${sample.ocrText||'—'} → Політ №${autoSync.selectedFlight} → зсув ${Number(autoSync.offsetSec||0).toFixed(3)} с`;
    if(VideoSyncUI.confidence){
      VideoSyncUI.confidence.hidden=false;
      VideoSyncUI.confidence.textContent=`Впевненість: ${autoSyncConfidenceLabel(autoSync.confidence)}`;
    }
    applyAutoSyncResult(autoSync);
    return;
  }
  if(autoSync.status==='ambiguous'){
    VideoSyncUI.autoStatus.textContent='Знайдено кілька правдоподібних польотів. Обери потрібний.';
    if(VideoSyncUI.candidate){
      VideoSyncUI.candidate.innerHTML=(autoSync.candidates||[]).map(item=>
        `<option value="${Number(item.number)}" data-offset="${Number(item.offsetSec)}">Політ №${Number(item.number)} • ${Number(item.durationSec).toFixed(1)} с</option>`
      ).join('');
      if(candidateRow)candidateRow.hidden=false;
    }
    return;
  }
  VideoSyncUI.autoStatus.textContent=(autoSync.warnings||[])[0]||'Не вдалося стабільно прочитати Flight Time.';
}

async function runFlightTimeAutoSync(){
  if(!selectedFile||!videoFile){
    UI.error.textContent='❌ Спочатку обери TLOG і відео';
    UI.error.style.display='block';
    return;
  }
  const roi=flightTimeRoi();
  if(!roi){
    UI.error.textContent='❌ Намалюй зону Flight Time на відео';
    UI.error.style.display='block';
    return;
  }
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
  UI.error.style.display='none';
}

VideoSyncUI.autoSync?.addEventListener('click',()=>{
  runFlightTimeAutoSync().catch(error=>{
    UI.error.textContent=`❌ Автосинхронізація: ${error.message||error}`;
    UI.error.style.display='block';
  });
});

VideoSyncUI.applyCandidate?.addEventListener('click',()=>{
  const option=VideoSyncUI.candidate?.selectedOptions?.[0];
  const offset=Number(option?.dataset?.offset);
  if(!Number.isFinite(offset))return;
  videoAnchorSec=0;
  tlogAnchorSec=offset;
  updateVideoSyncPair();
  if(VideoSyncUI.autoStatus)VideoSyncUI.autoStatus.textContent=`Застосовано ${option.textContent}`;
});
```

Extend `VideoSyncUI` exactly:

```javascript
const VideoSyncUI={
  autoSync:document.getElementById('videoAutoSync'),
  autoStatus:document.getElementById('videoAutoSyncStatus'),
  confidence:document.getElementById('videoAutoSyncConfidence'),
  candidate:document.getElementById('videoAutoSyncCandidate'),
  applyCandidate:document.getElementById('videoAutoSyncApplyCandidate'),
  videoAnchor:document.getElementById('videoSetAnchor'),
  tlogAnchor:document.getElementById('tlogSelectAnchor'),
  pair:document.getElementById('videoSyncPair')
};
```

- [ ] **Step 5: Run frontend contract and embedded JS syntax GREEN**

Run:

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
```

Expected: PASS and `node --check` exits 0.

- [ ] **Step 6: Commit frontend integration**

```bash
git add index.html tests/test_video_analysis_frontend.py
git commit -m "feat: add Flight Time auto-sync controls"
```

---

### Task 6: Add real-sample validation hook and complete regression verification

**Files:**
- Create: `tools/validate_flight_time_auto_sync.py`
- Modify: `.github/workflows/video-tlog-analysis.yml` only if the current workflow does not already run `tests/test_flight_time_auto_sync.py` through its video-test glob/list.
- Test: real user-provided files remain outside git.

**Interfaces:**
- Consumes: `TLOG_PATH`, `VIDEO_PATH`, and a JSON Flight Time ROI supplied on the command line; never assumes the user's filenames.
- Produces: a concise JSON diagnostic showing OCR samples, confidence, selected session, offset, and warnings.

- [ ] **Step 1: Add a validation utility that exercises the same production helpers**

Create `tools/validate_flight_time_auto_sync.py`:

```python
import argparse
import json
from pathlib import Path

from backend.main import analyze_flight_sessions
from backend.video_analysis import probe_video, run_flight_time_auto_sync
from pymavlink import mavutil


def read_arm_sessions_from_tlog(path):
    raw_timeline=[]
    mav=mavutil.mavlink_connection(str(path),robust_parsing=True)
    last_ts=None
    while True:
        msg=mav.recv_match(blocking=False)
        if msg is None:
            break
        ts=getattr(msg,'_timestamp',None)
        if ts is None:
            continue
        last_ts=float(ts)
        msg_type=msg.get_type()
        if msg_type=='STATUSTEXT':
            text=str(getattr(msg,'text','') or '')
            raw_timeline.append({'timestamp':last_ts,'system_text':text})
        elif msg_type=='HEARTBEAT':
            base_mode=int(getattr(msg,'base_mode',0) or 0)
            armed=bool(base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            raw_timeline.append({
                'timestamp':last_ts,
                'system_text':'🟢 Двигуни запущено' if armed else '🔴 Двигуни зупинено',
            })
    return analyze_flight_sessions(raw_timeline,last_ts)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('tlog',type=Path)
    parser.add_argument('video',type=Path)
    parser.add_argument('--roi',required=True,help='JSON object with x,y,width,height,label')
    args=parser.parse_args()
    metadata=probe_video(args.video)
    sessions=read_arm_sessions_from_tlog(args.tlog)
    result=run_flight_time_auto_sync(args.video,metadata,json.loads(args.roi),sessions)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
```

During implementation, if direct `analyze_flight_sessions()` requires richer timeline row fields than this lightweight utility supplies, replace `read_arm_sessions_from_tlog()` with a call through the production FastAPI/TestClient path rather than duplicating analyzer logic. The acceptance criterion is that the utility must call the same `run_flight_time_auto_sync()` used in production; it must not contain special-case timing values.

- [ ] **Step 2: Run the production test suite before real-file validation**

```bash
pytest tests/test_flight_time_auto_sync.py tests/test_video_analysis_core.py tests/test_video_analysis_api.py tests/test_video_analysis_frontend.py -v
python -m py_compile backend/main.py backend/video_analysis.py tools/validate_flight_time_auto_sync.py
```

Expected: PASS.

- [ ] **Step 3: Validate on the uploaded real pair using a user-drawn Flight Time ROI**

In the active environment, run the utility with the uploaded files and the ROI copied from the UI. Example invocation shape:

```bash
python tools/validate_flight_time_auto_sync.py \
  "/mnt/data/47 2026-09-14 11-49-46(1).tlog" \
  "/mnt/data/WhatsApp Video 2026-09-14 at 12.00.00.mp4" \
  --roi '{"id":"flight-time","label":"Flight Time","x":X,"y":Y,"width":W,"height":H}'
```

Before running, replace `X/Y/W/H` with the actual ROI exported by the UI; do not commit those sample-specific coordinates. Expected evidence:

- recognized samples increase from approximately `00:04:45` toward `00:05:59` over the clip;
- early ~10-second sessions are excluded by the session-duration check;
- the long fourth session is selected if it is the only or clearly dominant plausible session;
- `offsetSpreadSec <= 2.0` for an auto-applied result;
- any larger spread produces Low confidence and no anchor application.

- [ ] **Step 4: Run high-value existing regressions**

Run the existing regression set used by `Video TLOG analysis CI`, including at minimum:

```bash
pytest \
  tests/test_ai_reconstruction.py \
  tests/test_ai_reconstruction_frontend_contract.py \
  tests/test_board_messages_complete_list.py \
  tests/test_dashboard_summary_vtx_engine.py \
  tests/test_map_default_flight.py \
  tests/test_report_export.py \
  tests/test_video_analysis_core.py \
  tests/test_video_analysis_api.py \
  tests/test_video_analysis_frontend.py \
  tests/test_flight_time_auto_sync.py -v
```

If one of these exact filenames has changed in the branch, use the current equivalent already referenced by `.github/workflows/video-tlog-analysis.yml`; do not silently drop the regression category.

- [ ] **Step 5: Ensure CI installs OCR and runs the new tests**

Verify `.github/workflows/video-tlog-analysis.yml` installs `backend/requirements.txt`. If it already does, only add `tests/test_flight_time_auto_sync.py` to the video test command. The test step should include:

```yaml
- name: Run video TLOG tests
  run: |
    pytest \
      tests/test_video_analysis_core.py \
      tests/test_video_analysis_api.py \
      tests/test_video_analysis_frontend.py \
      tests/test_flight_time_auto_sync.py -v
```

Do not add the real 8 MB video or 3 MB TLOG to git or CI artifacts.

- [ ] **Step 6: Commit validation/CI changes**

```bash
git add tools/validate_flight_time_auto_sync.py .github/workflows/video-tlog-analysis.yml
git commit -m "test: validate Flight Time auto-sync pipeline"
```

- [ ] **Step 7: Final verification before PR**

```bash
pytest tests/test_flight_time_auto_sync.py tests/test_video_analysis_core.py tests/test_video_analysis_api.py tests/test_video_analysis_frontend.py -v
python -m py_compile backend/main.py backend/video_analysis.py tools/validate_flight_time_auto_sync.py
git status --short
git log --oneline --max-count=8
```

Expected:

- all targeted tests PASS;
- syntax checks PASS;
- no uncommitted production/test files remain;
- `main` is untouched until the feature PR is explicitly merged.
