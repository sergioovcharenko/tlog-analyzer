# Video + TLOG Analysis — Design

Date: 2026-09-14

## Goal
Add optional video-assisted analysis to the existing TLOG analyzer without changing the current TLOG-only flow.

The operator may have only a short video fragment from the middle or end of a flight. The system must therefore support manual time alignment between the video fragment and any moment in the TLOG.

## Safety / rollback
Before implementation, the current stable `main` is pinned at commit `0b906c51f20302aa3e4cd832e3b906b37e48d45f` in branch:

`backup/stable-before-video-analysis-2026-09-14`

All work is isolated in:

`feature/video-tlog-analysis`

The stable TLOG-only workflow must remain unchanged when video mode is disabled.

## MVP scope
One `.tlog` plus zero or one video file per analysis.

Supported initial video types: MP4 and MOV where the server can decode them.

No requirement that the video starts at ARM or contains the full flight.

## Frontend flow
The existing TLOG upload stays as-is.

Add checkbox:

`☐ Є відео польоту`

When unchecked:
- no video controls are shown;
- no video file is uploaded;
- the current `/analyze` TLOG-only path behaves exactly as before.

When checked:
- show video file selector;
- show local video preview;
- allow one or more rectangular ROI zones to be drawn over the video;
- each ROI has a label such as `Напруга`, `dBm`, `Режим`, `Попередження`, `Відеоканал`, `Інше`;
- show a synchronization panel where the user selects one timestamp in the video and one timestamp in the TLOG timeline.

## Time synchronization
The core mapping is one manual anchor pair:

`video_anchor_seconds <-> tlog_anchor_seconds`

For every analyzed video frame:

`tlog_time = tlog_anchor + (video_time - video_anchor)`

This supports partial video clips of any length from any part of the flight.

The first MVP does not require automatic synchronization. Later versions may suggest alignment based on visible telemetry values, but the user remains able to override it.

## ROI analysis
Only user-selected ROIs are processed for detailed visual analysis.

The backend samples frames at a low normal rate, initially about 1 frame/s. Around important TLOG events, the backend may sample more densely within a small time window.

The analysis should capture observations such as:
- visible text / telemetry value changes;
- mode indication changes;
- video degradation, freezes, black frames, heavy artifacts;
- warning banners/messages;
- loss and restoration of visible video.

The system must preserve uncertainty. It may say `часово збігається`, `передувало`, or `на відео видно`, but must not claim causality unless the evidence supports it.

## Backend architecture
Keep existing `/analyze` unchanged for TLOG-only requests.

Add a separate video-assisted path rather than making the current endpoint dependent on video processing.

Suggested components:
1. Video upload endpoint or multipart extension dedicated to video mode.
2. Temporary per-analysis video storage.
3. Frame extractor (FFmpeg/OpenCV-compatible backend implementation).
4. ROI crop processor.
5. Visual observation extractor.
6. Synchronization layer that maps video timestamps to TLOG timestamps.
7. Correlator that joins visual observations with existing deterministic TLOG events.

Video artifacts must be temporary and deleted after analysis or expiry.

## Result model
Add optional result section:

`videoAnalysis`

Suggested fields:
- `enabled`
- `videoDurationSec`
- `anchorVideoSec`
- `anchorTlogSec`
- `rois[]`
- `observations[]`
- `correlations[]`
- `warnings[]`

Each visual observation should include:
- video timestamp;
- mapped TLOG timestamp;
- ROI id/label;
- observation type;
- short description;
- confidence;
- optional extracted text/value.

Each correlation should include:
- related TLOG event/time;
- related video observation/time;
- time delta;
- wording that distinguishes correlation from causation.

## UI result
Add a section:

`AI — ВІДЕО + TLOG`

Example wording:

`13:49:58 — у TLOG сигнал погіршується. На відео в зоні "Відеоканал" у цей самий період з'являються сильні артефакти. Події часово збігаються.`

The section is hidden entirely for TLOG-only analysis.

## Failure handling
If video decoding fails, the user should still receive the normal TLOG analysis plus a clear video-analysis warning.

If the anchor maps outside the TLOG range, block video analysis and ask for a valid anchor.

If an ROI is outside the video frame or zero-sized, reject only that ROI and explain why.

If visual analysis is unavailable, do not fail the TLOG analysis.

## Performance
Do not analyze every frame.

Default sampling: approximately 1 fps.

Higher sampling is allowed only around selected/critical TLOG events and should be bounded.

The browser should not upload video unless the checkbox is enabled.

## Testing
Required test layers:
- frontend checkbox keeps current TLOG-only path unchanged;
- video controls appear only when enabled;
- anchor mapping math;
- ROI coordinate validation;
- backend accepts a partial clip independent of ARM;
- video-analysis failure does not break TLOG result;
- visual/TLOG correlation preserves timestamps and uncertainty wording;
- no video mode regression in current TLOG analyzer workflows.

## Out of scope for MVP
- multiple video clips per TLOG;
- fully automatic synchronization;
- real-time/live video analysis;
- permanent video storage;
- analyzing the entire frame with no ROI selection by default.

## Future extension
The result schema and UI should allow later expansion to multiple clips (`videoClips[]`) without rewriting the TLOG analysis model.