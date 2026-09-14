# Automatic Flight Time ↔ TLOG Synchronization Design

Date: 2026-09-14
Branch: `feature/flight-time-auto-sync`

## Goal

Automatically synchronize an uploaded flight video with the correct TLOG timeline by reading the OSD `Flight Time` value from several video frames and anchoring that value to the ARM time of the matching flight session in the TLOG.

The user should no longer need to manually pick a video time and then click a matching TLOG row in the common case. Manual synchronization remains available as a fallback.

## Current State

The analyzer already supports:

- standard TLOG analysis;
- optional MP4/MOV upload;
- ROI drawing on video;
- manual video ↔ TLOG anchor selection;
- time conversion with `map_video_to_tlog_time()`;
- FFmpeg-backed frame extraction and video metadata;
- isolated `/analyze-video` handling that does not break standard `/analyze`.

The current `/analyze-video` endpoint does not yet OCR the OSD or automatically derive a synchronization offset.

## User Experience

The video section gains a new ROI label `Flight Time` and a new action: `⚡ Автосинхронізація по Flight Time`.

The v1 flow is:

1. User uploads TLOG and video.
2. Standard TLOG analysis identifies flight sessions.
3. User draws one `Flight Time` ROI over the OSD timer.
4. User clicks auto-sync.
5. The backend samples several frames across the video and OCRs only that ROI.
6. The backend validates that recognized values increase at approximately the same rate as video playback time.
7. The analyzer checks which TLOG flight session can physically contain those Flight Time values.
8. It computes the synchronization offset and returns a confidence score plus evidence.
9. If confidence is high enough, the UI applies the anchor automatically.
10. If confidence is insufficient or multiple sessions remain plausible, the UI explains why and leaves manual synchronization available.

The UI should show a concise result such as:

`Flight Time 00:05:05 → Політ №4 → TLOG 08:10.397 → зсув +07:50.397`

It should also show `Автосинхронізація: висока / середня / низька впевненість`.

Automatic detection of the Flight Time screen position is explicitly out of scope for v1; the user supplies the ROI.

## Synchronization Model

For one OCR observation:

- `video_sec` = media player time for the sampled frame;
- `flight_time_sec` = OSD Flight Time parsed from that frame;
- `arm_tlog_sec` = ARM time for a candidate TLOG session.

The corresponding TLOG time is:

`mapped_tlog_sec = arm_tlog_sec + flight_time_sec`

The implied video-to-TLOG offset is:

`offset_sec = mapped_tlog_sec - video_sec`

Across multiple valid OCR samples, the system calculates a robust central offset using the median rather than a simple mean.

The final automatic anchor is represented as:

- `video_anchor_sec = 0`;
- `tlog_anchor_sec = median_offset_sec`.

The existing mapping function remains unchanged:

`TLOG = tlog_anchor_sec + (video_time_sec - video_anchor_sec)`

## Flight Session Selection

OCR timing consistency alone cannot distinguish different ARM sessions: adding a different ARM timestamp shifts all derived offsets by the same constant. Therefore session selection must use session bounds, not offset spread.

For each valid ARMED session:

1. compute `mapped_tlog_sec = ARM + Flight Time` for every valid OCR sample;
2. if the session has DISARM, require mapped samples to stay inside `ARM ... DISARM` with a small timing tolerance;
3. if the TLOG ends while still ARMED, use the end of available TLOG data as the upper bound;
4. reject any session whose duration is shorter than the observed Flight Time values;
5. reject a session when mapped samples fall outside its bounds.

Selection rules:

- if exactly one session remains plausible, select it;
- if several sessions remain plausible, prefer the longest session only when it is clearly dominant;
- if the top candidates are similarly plausible, return them and require user confirmation rather than silently guessing.

For the provided sample, the earlier ~10-second sessions are rejected immediately because an OSD Flight Time around `00:04:45` cannot fit inside them, while the long fourth ARMED session can.

## OCR Scope

OCR is intentionally restricted to the `Flight Time` ROI.

Why:

- smaller image region;
- fewer false positives;
- faster processing;
- no need to understand unrelated OSD text;
- easier validation against the expected time structure.

The OCR parser accepts:

- `HH:MM:SS`;
- `MM:SS`;
- common OCR substitutions where the parse remains unambiguous, including `O→0`, `I/l→1`, and separators confused with punctuation.

The parser must reject values that cannot be interpreted safely.

## OCR Engine

V1 uses **RapidOCR with ONNX Runtime** (`rapidocr_onnxruntime`) on the backend.

Reasons:

- no cloud API or API key;
- no separate system `tesseract` binary;
- deployable with Python dependencies on Render;
- suitable for small cropped text regions;
- OCR implementation can remain isolated behind a helper function.

The OCR layer must be wrapped behind a function such as `read_flight_time_text(image_path_or_array)` so it can be replaced later without changing the synchronization logic or API contract.

Unit tests for synchronization must not depend on OCR model accuracy; OCR outputs are injected/mocked there. A real-sample validation test separately exercises the OCR pipeline.

## Sampling Strategy

The backend does not OCR every frame.

V1 strategy:

- sample 7 frames spread across the usable video span;
- avoid sampling only the first/last second;
- for clips too short for 7 useful samples, use at least 3 when possible;
- extract frames through the existing packaged FFmpeg path;
- crop each frame to the Flight Time ROI;
- optionally upscale and increase contrast before OCR;
- run OCR only on the crop.

After parsing, validate that for samples `i` and `j`:

`(flight_time_j - flight_time_i)` is approximately equal to `(video_time_j - video_time_i)`.

A tolerance of ±2 seconds is accepted in v1 because OSD updates and extracted frames may straddle whole-second transitions.

## Confidence Model

Confidence is based on multiple signals.

Positive signals:

- at least 3 valid OCR samples;
- monotonic Flight Time values;
- slope close to 1.0 second per second;
- low spread of computed offsets;
- exactly one TLOG session satisfying the session-bound checks.

Negative signals:

- too few recognized values;
- non-monotonic time;
- large offset variance;
- multiple plausible flight sessions;
- Flight Time reset inside the clip.

V1 categories:

- **High**: at least 4 valid samples, exactly one plausible TLOG session, and offset spread ≤ 1.0 s;
- **Medium**: at least 3 valid samples, one plausible session, and offset spread > 1.0 s but ≤ 2.0 s;
- **Low**: fewer than 3 valid samples, multiple plausible sessions, non-monotonic Flight Time, or spread > 2.0 s.

Only High and Medium results may auto-populate anchors. Low confidence leaves manual synchronization active and does not silently change anchors.

The backend returns measured residual/spread values so the decision is inspectable.

## Backend Components

### `backend/video_analysis.py`

Add focused helpers for:

- cropping an extracted frame to an ROI;
- preprocessing the crop for OCR;
- running RapidOCR on the crop;
- parsing Flight Time text;
- validating a sequence of OCR observations;
- computing robust offsets;
- validating candidate TLOG session bounds;
- selecting a session or returning ambiguity;
- returning an auto-sync result with confidence and evidence.

The generic time-mapping and ROI validation helpers remain reusable.

### TLOG session data

Auto-sync reuses the existing flight-session source of truth rather than introducing a second ARM/DISARM parser.

For each candidate session it needs:

- session number;
- ARM timeline time;
- DISARM timeline time when present;
- duration;
- whether the session ends while still armed;
- end-of-log timeline time for an unfinished ARMED session.

### `/analyze-video`

Keep the current endpoint and preserve manual behavior.

Change the request contract in a backward-compatible way:

- `video_anchor_sec`: optional instead of required;
- `tlog_anchor_sec`: optional instead of required;
- add `auto_sync: bool = false`;
- add `flight_time_roi_json`, optional unless `auto_sync=true`.

Behavior:

- existing manual requests with both anchors continue to work unchanged;
- when `auto_sync=true`, the backend runs TLOG analysis, OCR synchronization, and returns derived anchors;
- if auto-sync fails, the endpoint still returns the normal TLOG result with `videoAnalysis.autoSync.status = "failed"` and warnings.

The result includes:

```json
{
  "videoAnalysis": {
    "autoSync": {
      "status": "success",
      "confidence": "high",
      "selectedFlight": 4,
      "armTlogSec": 185.397,
      "offsetSec": 470.397,
      "videoAnchorSec": 0.0,
      "tlogAnchorSec": 470.397,
      "samples": [
        {
          "videoSec": 20.0,
          "flightTimeSec": 305.0,
          "ocrText": "00:05:05",
          "ocrConfidence": 0.96
        }
      ],
      "offsetSpreadSec": 0.42,
      "warnings": []
    }
  }
}
```

If several sessions remain plausible, `status` becomes `ambiguous` and the response includes the candidate session numbers instead of auto-applying anchors.

## Frontend Changes

The existing video panel adds:

- ROI label `Flight Time`;
- button `⚡ Автосинхронізація по Flight Time`;
- progress/status text while OCR runs;
- result line containing detected Flight Time, selected flight, calculated TLOG time, and offset;
- confidence badge;
- ambiguous-candidate selector when required;
- existing manual synchronization remains visible as fallback.

A successful automatic result populates the exact same `video_anchor_sec` / `tlog_anchor_sec` state used by manual synchronization so downstream mapping has only one source of truth.

## Error Handling

Auto-sync fails safely.

Cases:

- no Flight Time ROI: prompt the user to draw one;
- OCR cannot read enough samples: show `Не вдалося стабільно прочитати Flight Time`;
- Flight Time does not progress consistently: do not auto-apply;
- no TLOG flight can contain the recognized Flight Time: explain that OSD timing does not match any session;
- multiple TLOG flights remain plausible: show candidates for confirmation;
- video clip contains a Flight Time reset: fail to manual synchronization in v1;
- OCR dependency unavailable in production: preserve normal TLOG analysis and return a video auto-sync warning.

No auto-sync failure may break ordinary TLOG analysis.

## Security and Resource Limits

- Process only MP4/MOV already accepted by the endpoint.
- Reuse existing temporary-file cleanup.
- OCR only 3–7 cropped frames, never the whole video stream.
- Keep FFmpeg process timeouts.
- Reject invalid or out-of-frame ROI coordinates through existing ROI validation.
- Keep OCR execution bounded to one request and return an ordinary warning if it fails.

## Testing Strategy

Implementation follows TDD.

### Unit tests

Add tests for:

- parsing `00:05:05` and `05:05`;
- common OCR digit substitutions;
- invalid time strings;
- monotonic validation;
- median offset calculation;
- rejecting a 10-second session when Flight Time is ~285 seconds;
- selecting the long fourth flight when it is the only session whose bounds fit;
- ambiguity when multiple long sessions can contain the samples;
- low confidence when offset spread is too large.

### Integration tests

Add tests for:

- `/analyze-video` accepting auto-sync without manual anchors;
- manual `/analyze-video` requests remaining backward compatible;
- `videoAnalysis.autoSync` success and failure responses;
- Render-style imports from `rootDir: backend`;
- auto-sync failure preserving the ordinary TLOG result.

### Frontend contract tests

Add tests for:

- `Flight Time` ROI label;
- auto-sync button;
- confidence/result fields;
- ambiguous candidate UI;
- successful auto-sync populating existing anchor variables;
- no regression to ordinary TLOG upload or manual video sync.

### Real sample validation

Use the provided pair:

- `47 2026-09-14 11-49-46(1).tlog`;
- `WhatsApp Video 2026-09-14 at 12.00.00.mp4`.

Expected behavior for this sample:

- OCR should observe Flight Time increasing from approximately `00:04:45` to `00:05:59` over the clip;
- the earlier ~10-second TLOG sessions should be rejected as impossible;
- the long fourth ARMED session should remain plausible and be selected;
- offsets from multiple OCR samples should be approximately constant;
- if OCR observations do not satisfy those checks, the feature must refuse to claim High/Medium confidence.

The real sample is validation data, not a hard-coded special case.

## Non-Goals for This Change

This feature does not yet attempt to:

- automatically locate the Flight Time ROI on screen;
- OCR voltage, current, RSSI, VISP, dBm, mode, or warnings;
- analyze visual vibration, image loss, obstacles, or horizon;
- infer causal relationships between video and TLOG events;
- remove manual synchronization;
- change existing TLOG timing semantics.

Those can build on the synchronized timeline later.

## Success Criteria

The feature is complete when:

1. TLOG + video can be uploaded as today.
2. `Flight Time` ROI can be selected.
3. Auto-sync reads multiple OSD timestamps from the video.
4. Impossible TLOG sessions are eliminated by session-bound checks.
5. The matching session is selected, or ambiguity is surfaced instead of guessed.
6. A stable offset is calculated and applied to the existing video↔TLOG mapping state.
7. The user sees the selected flight, calculated offset, confidence, and evidence.
8. Low-confidence cases fall back to manual sync instead of silently applying a bad offset.
9. Existing TLOG-only analysis and manual video sync remain unchanged and tested.
