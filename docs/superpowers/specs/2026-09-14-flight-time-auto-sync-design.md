# Automatic Flight Time ↔ TLOG Synchronization Design

Date: 2026-09-14
Branch: `feature/flight-time-auto-sync`

## Goal

Automatically synchronize an uploaded flight video with the correct TLOG timeline by reading the OSD `Flight Time` value from several video frames and anchoring that value to the ARM time of the most likely flight session in the TLOG.

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

The video section gains a new action: `⚡ Автосинхронізація по Flight Time`.

The intended flow is:

1. User uploads TLOG and video.
2. Standard TLOG analysis identifies flight sessions.
3. User either draws a `Flight Time` ROI or allows the analyzer to use a default/remembered OSD area when available.
4. User clicks auto-sync.
5. The backend samples several frames across the video and OCRs only the `Flight Time` ROI.
6. The backend validates that the recognized values increase at approximately the same rate as video playback time.
7. The analyzer selects the primary TLOG flight session, preferring the longest valid ARMED session.
8. It computes the synchronization offset and returns a confidence score plus evidence.
9. If confidence is high enough, the UI applies the anchor automatically.
10. If confidence is insufficient, the UI explains why and leaves manual synchronization available.

The UI should show a concise result such as:

`Flight Time 00:05:05 → Політ №4 → TLOG 08:10.397 → зсув +07:50.397`

It should also show `Автосинхронізація: висока / середня / низька впевненість`.

## Synchronization Model

For one OCR observation:

- `video_sec` = media player time for the sampled frame;
- `flight_time_sec` = OSD Flight Time parsed from that frame;
- `arm_tlog_sec` = ARM time for the selected TLOG session.

The corresponding TLOG time is:

`mapped_tlog_sec = arm_tlog_sec + flight_time_sec`

The implied video-to-TLOG offset is:

`offset_sec = mapped_tlog_sec - video_sec`

Across multiple valid OCR samples, the system calculates a robust central offset using the median rather than a simple mean.

The final automatic anchor may be represented as:

- `video_anchor_sec = 0` and `tlog_anchor_sec = median_offset_sec`, or
- an equivalent pair using one validated sample.

The existing mapping function remains unchanged:

`TLOG = tlog_anchor_sec + (video_time_sec - video_anchor_sec)`

## Flight Session Selection

The default selection rule is:

1. consider only valid ARMED sessions;
2. prefer sessions with meaningful duration;
3. select the longest session as the primary candidate;
4. if two or more sessions are close enough to be plausible, evaluate each candidate against the OCR-derived offset consistency;
5. choose the candidate with the lowest residual timing error;
6. if ambiguity remains above the confidence threshold, return multiple candidates and require user confirmation.

This avoids blindly assuming that the first ARM in a TLOG is the actual flight.

## OCR Scope

OCR is intentionally restricted to the `Flight Time` ROI.

Why:

- smaller image region;
- fewer false positives;
- faster processing;
- no need to understand unrelated OSD text;
- easier validation against the expected `HH:MM:SS` or `MM:SS` structure.

The OCR parser accepts:

- `HH:MM:SS`;
- `MM:SS`;
- common OCR substitutions where confidence is still recoverable, such as `O/0`, `I/1`, or missing separators when the pattern is otherwise unambiguous.

The parser must reject values that cannot be interpreted safely.

## Sampling Strategy

The backend should not OCR every frame.

Recommended first version:

- sample 7–10 frames across the usable video span;
- avoid only sampling the first/last second;
- if the video is short, reduce sample count while keeping at least 3 samples where possible;
- extract the frame with the existing packaged FFmpeg path;
- crop to the Flight Time ROI;
- run OCR only on the crop.

After parsing, validate that for samples `i` and `j`:

`(flight_time_j - flight_time_i)` is approximately equal to `(video_time_j - video_time_i)`.

A tolerance of roughly ±1–2 seconds is acceptable for the initial version because OSD updates and frame extraction may not land exactly on a whole-second transition.

## Confidence Model

Confidence should be based on several signals rather than one OCR result.

Positive signals:

- at least 3 valid OCR samples;
- monotonic Flight Time values;
- slope close to 1.0 second per second;
- low spread of computed offsets;
- one TLOG flight candidate clearly better than the others.

Negative signals:

- too few recognized values;
- non-monotonic time;
- large offset variance;
- multiple equally plausible ARM sessions;
- Flight Time reset inside the clip.

Suggested categories:

- High: enough valid samples and offset spread ≤ 1.0 s;
- Medium: enough samples but spread > 1.0 s and ≤ 2.0 s;
- Low: insufficient consistency; do not apply automatically.

The exact thresholds may be adjusted from real flight data, but the backend must return the measured residuals so the decision remains inspectable.

## Backend Components

### `backend/video_analysis.py`

Add focused helpers for:

- cropping an extracted frame to an ROI;
- parsing Flight Time text;
- validating a sequence of OCR observations;
- computing robust offsets;
- ranking TLOG flight session candidates;
- returning an auto-sync result with confidence and evidence.

The existing generic video helpers should remain reusable and should not be overloaded with TLOG parsing logic beyond the synchronization helpers.

### TLOG session data

The existing TLOG analyzer already derives flight sessions for the UI. Auto-sync should reuse that source of truth rather than parse ARM/DISARM a second independent way if practical.

The backend needs, for each candidate session:

- session number;
- ARM timeline time;
- DISARM timeline time when present;
- duration;
- whether the session ends while still armed.

### `/analyze-video`

Keep current behavior compatible.

Extend the result with an optional structure such as:

```json
{
  "videoAnalysis": {
    "autoSync": {
      "status": "success",
      "confidence": "high",
      "selectedFlight": 4,
      "armTlogSec": 185.397,
      "offsetSec": 470.397,
      "videoAnchorSec": 20.0,
      "tlogAnchorSec": 490.397,
      "samples": [
        {
          "videoSec": 20.0,
          "flightTimeSec": 305.0,
          "ocrText": "00:05:05",
          "confidence": 0.96
        }
      ],
      "residualSec": 0.42,
      "warnings": []
    }
  }
}
```

If auto-sync fails, standard TLOG results must still be returned.

## OCR Engine Choice

The first implementation should use a lightweight backend OCR dependency that can run on Render without requiring a separate external service.

Selection criteria:

- deployable from Python requirements or bundled runtime;
- works on cropped OSD digits;
- acceptable CPU time for 7–10 crops;
- no cloud API key required;
- deterministic enough for regression tests.

If the chosen OCR package proves unreliable for this specific OSD, the parser/crop pipeline should remain isolated so the OCR implementation can be replaced without changing the synchronization API.

## Frontend Changes

The existing video panel should add:

- ROI label `Flight Time`;
- button `⚡ Автосинхронізація по Flight Time`;
- progress/status text while OCR runs;
- result line containing detected Flight Time, selected flight, calculated TLOG time, and offset;
- confidence badge;
- fallback button/section for manual synchronization.

The automatic result should populate the same anchor state already used by manual synchronization so downstream code does not need two separate time-mapping systems.

## Error Handling

Auto-sync must fail safely.

Cases:

- No Flight Time ROI: prompt the user to draw one.
- OCR cannot read enough samples: show `Не вдалося стабільно прочитати Flight Time`.
- Flight Time does not progress consistently: do not auto-apply.
- Multiple TLOG flights remain plausible: show candidates for confirmation.
- Video clip contains a Flight Time reset: split observations into monotonic segments or fail to manual sync in v1.
- OCR dependency unavailable in production: preserve normal TLOG analysis and return a video auto-sync warning.

No auto-sync failure may break ordinary TLOG analysis.

## Security and Resource Limits

- Process only MP4/MOV already accepted by the endpoint.
- Reuse existing temporary-file cleanup.
- OCR only cropped frames, not the full video stream.
- Cap sample count.
- Keep FFmpeg process timeouts.
- Reject invalid or out-of-frame ROI coordinates through existing ROI validation.

## Testing Strategy

Implementation follows TDD.

### Unit tests

Add tests for:

- parsing `00:05:05` and `05:05`;
- common digit OCR substitutions;
- invalid time strings;
- monotonic validation;
- median offset calculation;
- selecting the longest TLOG flight;
- candidate ranking when multiple sessions exist;
- low confidence when offset spread is too large.

### Integration tests

Add tests for:

- `/analyze-video` returning `videoAnalysis.autoSync`;
- Render-style imports from `rootDir: backend`;
- auto-sync failure preserving TLOG result;
- manual sync remaining available.

### Frontend contract tests

Add tests for:

- `Flight Time` ROI label;
- auto-sync button;
- confidence/result fields;
- auto-sync result populating existing manual anchor variables;
- no regression to ordinary TLOG upload.

### Real sample validation

Use the provided pair:

- `47 2026-09-14 11-49-46(1).tlog`;
- `WhatsApp Video 2026-09-14 at 12.00.00.mp4`.

Expected behavior for this sample:

- OCR should observe Flight Time values increasing from approximately `00:04:45` to `00:05:59` over the clip;
- the analyzer should prefer the long fourth ARMED session rather than one of the earlier ~10-second sessions;
- computed offsets from multiple samples should be approximately constant;
- if they are not, auto-sync must refuse to claim high confidence.

The real sample is validation data, not a hard-coded special case.

## Non-Goals for This Change

This feature does not yet attempt to:

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
4. The primary/longest TLOG flight is selected by default, with ambiguity handling.
5. A stable offset is calculated and applied to the existing video↔TLOG mapping state.
6. The user sees the selected flight, calculated offset, confidence, and evidence.
7. Low-confidence cases fall back to manual sync instead of silently applying a bad offset.
8. Existing TLOG-only analysis and manual video sync remain unchanged and tested.
