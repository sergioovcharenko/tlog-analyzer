# Video + TLOG Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional video-assisted analysis to the existing TLOG analyzer while preserving the current TLOG-only workflow unchanged when video mode is disabled.

**Architecture:** Keep `/analyze` as the stable TLOG-only path. Add a separate `/analyze-video` path that accepts a video clip plus synchronization/ROI metadata and combines video observations with the already-produced TLOG analysis model. The frontend only shows/uploads video when the user enables `Є відео польоту`; video clips may be partial and are aligned with one manual anchor pair.

**Tech Stack:** Existing GitHub Pages frontend (`index.html`), FastAPI backend (`backend/main.py`), Python, `python-multipart`, FFmpeg subprocess for frame extraction/metadata, pytest-style repository tests / script assertions, browser-native `<video>` preview and canvas overlay.

**Spec:** `docs/superpowers/specs/2026-09-14-video-tlog-analysis-design.md`

## Global Constraints

- Stable rollback branch is `backup/stable-before-video-analysis-2026-09-14` at commit `0b906c51f20302aa3e4cd832e3b906b37e48d45f`.
- All development stays on `feature/video-tlog-analysis` until verification is complete.
- Existing `/analyze` behavior must remain unchanged for TLOG-only use.
- One `.tlog` plus zero or one MP4/MOV clip in MVP.
- Partial clips may start anywhere in the flight; no ARM-at-video-start assumption.
- Manual sync formula: `tlog_time = tlog_anchor + (video_time - video_anchor)`.
- Default frame sampling is approximately 1 fps; denser sampling is bounded around relevant TLOG events.
- Detailed visual analysis is restricted to user-selected ROIs.
- Video-processing failure must not invalidate the completed TLOG analysis.
- Temporary video/frame artifacts must be deleted after request completion.
- Correlation wording must distinguish temporal association from causation.

---

## File Structure

- `index.html` — optional-video checkbox, file selection, local preview, ROI editor, anchor UI, request wiring, result rendering.
- `backend/main.py` — new video-assisted endpoint orchestration only; current `/analyze` stays unchanged.
- `backend/video_analysis.py` — video metadata, anchor mapping, ROI validation, FFmpeg frame extraction, lightweight visual observations, TLOG/video correlation.
- `backend/requirements.txt` — keep Python dependencies minimal; use system FFmpeg rather than adding OpenCV in MVP.
- `tests/test_video_analysis_core.py` — pure unit tests for anchor mapping, ROI validation, correlation wording.
- `tests/test_video_analysis_api.py` — endpoint/failure-isolation contract tests.
- `tests/test_video_analysis_frontend.py` — frontend contract tests for checkbox, hidden controls, no upload in TLOG-only mode, ROI/anchor payload.
- `.github/workflows/video-tlog-analysis.yml` — focused CI for the new subsystem plus JS/Python syntax checks.

---

### Task 1: Pure synchronization and ROI validation core

**Files:**
- Create: `backend/video_analysis.py`
- Create: `tests/test_video_analysis_core.py`

**Interfaces:**
- Produces: `map_video_to_tlog_time(video_time_sec: float, video_anchor_sec: float, tlog_anchor_sec: float) -> float`
- Produces: `validate_roi(roi: dict, frame_width: int, frame_height: int) -> dict`
- Produces: `normalize_rois(rois: list[dict], frame_width: int, frame_height: int) -> tuple[list[dict], list[str]]`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/test_video_analysis_core.py -v`

Expected: FAIL because `backend.video_analysis` does not exist.

- [ ] **Step 3: Implement the minimal pure helpers**

```python
def map_video_to_tlog_time(video_time_sec, video_anchor_sec, tlog_anchor_sec):
    return float(tlog_anchor_sec) + (float(video_time_sec) - float(video_anchor_sec))
```

`validate_roi()` must reject non-positive dimensions and any rectangle extending outside `[0,width] x [0,height]`; `normalize_rois()` must return valid ROIs plus per-ROI warnings instead of throwing for the entire set.

- [ ] **Step 4: Run core tests to verify GREEN**

Run: `python -m pytest tests/test_video_analysis_core.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/video_analysis.py tests/test_video_analysis_core.py
git commit -m "feat: add video sync and ROI core"
```

---

### Task 2: FFmpeg-backed video metadata and sampled frame extraction

**Files:**
- Modify: `backend/video_analysis.py`
- Modify: `tests/test_video_analysis_core.py`

**Interfaces:**
- Produces: `probe_video(path: str) -> dict` with `durationSec`, `width`, `height`, `fps`
- Produces: `build_sample_times(duration_sec: float, normal_fps: float = 1.0, dense_windows: list[tuple[float,float]] | None = None) -> list[float]`
- Produces: `extract_frame(path: str, time_sec: float, output_path: str) -> None`

- [ ] **Step 1: Add failing tests for bounded sample generation**

```python
from backend.video_analysis import build_sample_times


def test_sample_times_support_short_partial_clip():
    times = build_sample_times(5.0, normal_fps=1.0)
    assert times == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]


def test_dense_windows_do_not_create_unbounded_samples():
    times = build_sample_times(20.0, normal_fps=1.0, dense_windows=[(9.0, 11.0)])
    assert len(times) < 100
    assert any(9.0 < t < 10.0 for t in times)
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_video_analysis_core.py -v`

Expected: FAIL on missing `build_sample_times`.

- [ ] **Step 3: Implement FFmpeg/ffprobe helpers**

Use `subprocess.run(..., timeout=...)` with argument arrays, never shell strings. `probe_video` reads JSON from `ffprobe`; `extract_frame` writes exactly one JPEG/PNG frame. `build_sample_times` uses about 1 fps baseline and at most 4 fps inside dense windows, deduplicated and clamped to clip duration.

- [ ] **Step 4: Run GREEN and syntax check**

Run:
```bash
python -m pytest tests/test_video_analysis_core.py -v
python -m py_compile backend/video_analysis.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/video_analysis.py tests/test_video_analysis_core.py
git commit -m "feat: add bounded video frame sampling"
```

---

### Task 3: Lightweight ROI observations and temporal correlation model

**Files:**
- Modify: `backend/video_analysis.py`
- Modify: `tests/test_video_analysis_core.py`

**Interfaces:**
- Produces: `build_observation(video_time_sec: float, mapped_tlog_sec: float, roi: dict, kind: str, description: str, confidence: float, extracted_text: str | None = None) -> dict`
- Produces: `correlate_observations(observations: list[dict], tlog_events: list[dict], max_delta_sec: float = 2.0) -> list[dict]`

- [ ] **Step 1: Write failing correlation tests**

```python
from backend.video_analysis import build_observation, correlate_observations


def test_correlation_uses_non_causal_wording():
    obs = [build_observation(10.0, 810.0, {"id":"v","label":"Відеоканал"}, "video_degradation", "Сильні артефакти", 0.9)]
    events = [{"timeSec": 810.4, "type": "RADIO_LOSS", "text": "-128 dBm"}]
    out = correlate_observations(obs, events, max_delta_sec=2.0)
    assert len(out) == 1
    assert out[0]["deltaSec"] == 0.4
    assert "часово" in out[0]["summary"].lower()
    assert "причин" not in out[0]["summary"].lower()
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_video_analysis_core.py -v`

Expected: FAIL on missing correlation functions.

- [ ] **Step 3: Implement normalized observations/correlations**

Observation schema must contain: `videoTimeSec`, `tlogTimeSec`, `roiId`, `roiLabel`, `type`, `description`, `confidence`, optional `extractedText`.

Correlation schema must contain: `tlogEvent`, `videoObservation`, `deltaSec`, `summary`. Summary language uses `часово збігається`, `передувало`, or `після`, never an automatic causal statement.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest tests/test_video_analysis_core.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/video_analysis.py tests/test_video_analysis_core.py
git commit -m "feat: correlate video observations with tlog events"
```

---

### Task 4: Add isolated `/analyze-video` API path with cleanup and failure isolation

**Files:**
- Modify: `backend/main.py`
- Create: `tests/test_video_analysis_api.py`

**Interfaces:**
- Consumes: existing TLOG analysis result shape from current analyzer code.
- Consumes: helpers from `backend.video_analysis`.
- Produces: `POST /analyze-video` response containing existing TLOG result plus optional `videoAnalysis`.

- [ ] **Step 1: Write failing endpoint contract tests**

Tests must assert:

```python
assert response_json["videoAnalysis"]["enabled"] is True
assert response_json["videoAnalysis"]["anchorVideoSec"] == 37.0
assert response_json["videoAnalysis"]["anchorTlogSec"] == 822.0
```

and a mocked decode failure must return the normal TLOG payload with:

```python
assert response_json["videoAnalysis"]["enabled"] is True
assert response_json["videoAnalysis"]["warnings"]
```

rather than failing the whole request.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_video_analysis_api.py -v`

Expected: FAIL because `/analyze-video` does not exist.

- [ ] **Step 3: Implement endpoint without modifying `/analyze` semantics**

`/analyze-video` accepts multipart fields: `file` (TLOG), `video`, `video_anchor_sec`, `tlog_anchor_sec`, `rois_json`. Save both uploads to temporary files, run the existing TLOG analyzer first, then video processing. Wrap video-specific work in its own exception boundary. Always delete temporary video/frame data in `finally`.

- [ ] **Step 4: Run API tests and current analyzer syntax checks**

Run:
```bash
python -m pytest tests/test_video_analysis_api.py -v
python -m py_compile backend/main.py backend/video_analysis.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/video_analysis.py tests/test_video_analysis_api.py
git commit -m "feat: add isolated video-assisted analysis endpoint"
```

---

### Task 5: Frontend optional video controls and zero-regression TLOG-only path

**Files:**
- Modify: `index.html`
- Create: `tests/test_video_analysis_frontend.py`

**Interfaces:**
- Produces frontend state: `videoEnabled`, `videoFile`, `videoRois`, `videoAnchorSec`, `tlogAnchorSec`.
- TLOG-only mode continues posting only to `/analyze`.
- Video-enabled mode posts multipart to `/analyze-video`.

- [ ] **Step 1: Write failing frontend contract tests**

Assertions must require exact user-facing control text and branching behavior:

```python
assert 'Є відео польоту' in html
assert 'id="videoFlightEnabled"' in html
assert 'id="videoUploadPanel"' in html
assert 'id="videoPreview"' in html
assert '/analyze-video' in html
assert "if(!videoEnabled" in html or equivalent_branch_is_present
```

Also assert the existing `API_BASE_URL + '/analyze'` path remains present.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_video_analysis_frontend.py -v`

Expected: FAIL because controls are absent.

- [ ] **Step 3: Add checkbox, hidden upload panel, local preview and request branching**

When unchecked, clear any selected video state and do not append video fields. When checked, require a video before starting assisted analysis. Use `URL.createObjectURL(videoFile)` for local preview and revoke old URLs on replacement/reset.

- [ ] **Step 4: Run GREEN and JavaScript syntax extraction check**

Run the repository's existing inline-JS syntax command/workflow plus:

```bash
python -m pytest tests/test_video_analysis_frontend.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_video_analysis_frontend.py
git commit -m "feat: add optional video upload flow"
```

---

### Task 6: ROI drawing/editing on the video preview

**Files:**
- Modify: `index.html`
- Modify: `tests/test_video_analysis_frontend.py`

**Interfaces:**
- Produces normalized ROI payload in source-pixel coordinates: `{id,label,x,y,width,height}`.
- Labels: `Напруга`, `dBm`, `Режим`, `Попередження`, `Відеоканал`, `Інше`.

- [ ] **Step 1: Add failing tests for ROI controls and payload conversion**

Require canvas/overlay element, `Додати зону`, label selector, delete/reset controls, and a function that converts display coordinates to intrinsic video resolution.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_video_analysis_frontend.py -v`

Expected: FAIL on missing ROI UI/functions.

- [ ] **Step 3: Implement pointer-drag ROI editor**

Overlay must track the rendered video rectangle and scale selections to `video.videoWidth/video.videoHeight`. Prevent zero-size rectangles and clamp dragging to the video bounds. Store multiple ROI rectangles but keep one video clip in MVP.

- [ ] **Step 4: Run GREEN and JS syntax**

Run frontend tests and inline JavaScript syntax verification.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_video_analysis_frontend.py
git commit -m "feat: add video ROI editor"
```

---

### Task 7: Manual partial-clip synchronization UI

**Files:**
- Modify: `index.html`
- Modify: `tests/test_video_analysis_frontend.py`

**Interfaces:**
- Produces `videoAnchorSec` from current `<video>.currentTime`.
- Produces `tlogAnchorSec` from selected Timeline/graph timestamp.

- [ ] **Step 1: Write failing tests**

Require UI strings/buttons equivalent to `Взяти поточний час відео` and `Вибрати момент TLOG`, plus payload fields `video_anchor_sec` and `tlog_anchor_sec`.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_video_analysis_frontend.py -v`

Expected: FAIL.

- [ ] **Step 3: Implement one-anchor pairing**

Allow a clip timestamp from any point in the video. Allow selecting the TLOG timestamp from existing Timeline rows; display the resolved pair as `відео mm:ss ↔ TLOG mm:ss`. Block assisted analysis until both anchors are set, but do not affect normal TLOG-only analysis.

- [ ] **Step 4: Run GREEN and JS syntax**

Run frontend tests and inline JavaScript syntax verification.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_video_analysis_frontend.py
git commit -m "feat: synchronize partial video clips to tlog"
```

---

### Task 8: Render `AI — ВІДЕО + TLOG` results

**Files:**
- Modify: `index.html`
- Modify: `tests/test_video_analysis_frontend.py`

**Interfaces:**
- Consumes: optional `result.videoAnalysis`.
- Produces: hidden-by-default results section rendered only when `videoAnalysis.enabled === true`.

- [ ] **Step 1: Write failing rendering tests**

Require heading `AI — ВІДЕО + TLOG`, observation time, ROI label, confidence, correlation delta, warnings, and absence of the block when `videoAnalysis` is missing.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_video_analysis_frontend.py -v`

Expected: FAIL.

- [ ] **Step 3: Implement result renderer**

Render correlations first, then observations and warnings. Do not use causal language unless the backend explicitly supplies a causal classification in a future schema; MVP displays the backend's temporal wording verbatim.

- [ ] **Step 4: Run GREEN and report-export regression tests**

Run:
```bash
python -m pytest tests/test_video_analysis_frontend.py -v
python -m pytest tests/test_report_export.py tests/test_report_export_full.py tests/test_report_export_runtime_vtx.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_video_analysis_frontend.py
git commit -m "feat: render combined video and tlog findings"
```

---

### Task 9: Focused CI and end-to-end regression guard

**Files:**
- Create: `.github/workflows/video-tlog-analysis.yml`
- Modify only if required by discovered current test harness: relevant test configuration files.

**Interfaces:**
- Produces a dedicated PR workflow checking the video subsystem without masking committed-source regressions.

- [ ] **Step 1: Add workflow that runs committed source directly**

Workflow steps:

```yaml
- run: python -m pytest tests/test_video_analysis_core.py -v
- run: python -m pytest tests/test_video_analysis_api.py -v
- run: python -m pytest tests/test_video_analysis_frontend.py -v
- run: python -m py_compile backend/main.py backend/video_analysis.py
```

Add the repository's existing inline JavaScript syntax validation command as a separate step. Do not run a generator/patcher before these assertions.

- [ ] **Step 2: Run all new tests locally/in CI and verify GREEN**

Expected: all dedicated video-analysis steps pass.

- [ ] **Step 3: Run high-value existing regression suites**

At minimum verify report export, AI reconstruction, VTX matrix, Board Messages/STATUSTEXT, map default flight, and current TLOG-only frontend upload behavior. Record unrelated stale workflows separately; do not claim they are fixed.

- [ ] **Step 4: Manual MVP acceptance with one short clip**

Acceptance sequence:
1. Analyze a TLOG with video checkbox OFF and confirm current behavior is unchanged.
2. Enable video, select a short MP4/MOV fragment from the middle of a flight.
3. Draw at least two ROIs.
4. Set an arbitrary video anchor and matching TLOG anchor.
5. Run assisted analysis.
6. Confirm `AI — ВІДЕО + TLOG` appears, timestamps map correctly, and TLOG result remains available if video processing emits a warning.

- [ ] **Step 5: Commit CI**

```bash
git add .github/workflows/video-tlog-analysis.yml
git commit -m "ci: verify video assisted tlog analysis"
```

---

### Task 10: Final verification and PR

**Files:**
- No production file changes unless verification exposes a defect.

**Interfaces:**
- Produces a reviewable PR from `feature/video-tlog-analysis` to `main` while preserving the rollback branch.

- [ ] **Step 1: Run fresh verification suite**

Run all new tests, syntax checks, and the selected high-value regression suites from Task 9 on the final head SHA.

- [ ] **Step 2: Inspect final diff for scope creep**

Confirm `/analyze` semantics were not changed, no permanent video storage was introduced, no automatic sync was slipped into MVP, and no multi-video UI was added.

- [ ] **Step 3: Open PR as draft first**

PR body must include:
- rollback branch name and stable SHA;
- new endpoint and UI behavior;
- exact test evidence;
- known limitations: one clip, manual anchor, ROI-only detailed analysis, FFmpeg availability requirement.

- [ ] **Step 4: Mark ready only after fresh CI GREEN**

Do not merge on stale or partially passing evidence.

- [ ] **Step 5: Merge only after user confirms the MVP behavior on a real clip**

Keep `backup/stable-before-video-analysis-2026-09-14` untouched after merge so rollback remains available.
