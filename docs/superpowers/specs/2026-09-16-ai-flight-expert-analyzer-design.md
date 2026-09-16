# AI Flight Expert Analyzer — Design

Date: 2026-09-16
Branch: `feature/ai-flight-expert-analyzer`
Base: `main`

## Goal

Replace the current single-pass AI reconstruction with an internal expert-analysis engine that produces deeper, session-aware UAV diagnostics without using any external/online AI service.

The stable analyzer remains the source of truth for telemetry parsing. The new AI layer consumes structured facts produced by the analyzer and explains them more accurately, with explicit uncertainty and per-flight context.

## Core principles

1. Never mix events from separate ARM sessions unless the conclusion explicitly compares sessions.
2. Distinguish short ARM checks from confirmed flights.
3. Prefer factual wording over causal claims.
4. Separate confirmed facts, interpretation, unknowns, and post-flight checks.
5. Confidence grows from independent evidence sources, not from repeated messages of the same type.
6. Keep the existing analyzer operational as a fallback. The expert layer must fail closed: if it cannot produce a result, the ordinary TLOG analysis still returns normally.
7. `main` is untouched until the feature branch is reviewed and explicitly approved for merge.

## High-level flow

`TLOG -> stable parser -> ARM session segmentation -> per-session feature extraction -> subsystem analyzers -> event reconstruction -> session prioritization -> narrative output`

## ARM session model

Every ARM session is classified as one of:

- `arm_check` — short ARM session with no convincing evidence of actual flight.
- `flight` — movement/altitude/distance/flight telemetry confirms a real flight.
- `uncertain` — insufficient evidence to classify reliably.

Classification uses multiple signals rather than one threshold: duration, altitude change, movement/home distance, velocity, flight modes and continuity of telemetry.

Each session receives its own time bounds, facts, detected anomalies, confidence values, and event timeline.

## Session prioritization

All sessions are analyzed. The UI shows a compact summary for normal sessions and expands sessions that contain meaningful anomalies.

The primary session is selected by severity and breadth of independent evidence, not raw event count. One critical anomaly can outweigh dozens of repeated low-value messages.

If multiple sessions are problematic, none is discarded; the most severe is shown first and the others remain available as separate analyses.

## Expert subsystem analyzers

The initial version contains six independent modules:

### 1. Radio / MAVLink

Inputs include RADIO_STATUS/RSSI/dBm, packet-loss episodes, communication gaps, recovered/not recovered state, failsafe-related messages, and relevant mode changes.

Outputs include problem status, severity, confidence, start/end time, evidence, counter-evidence, and related events.

### 2. Navigation / GPS / EKF

Inputs include GPS health, satellites/HDOP when available, EKF warnings, aiding state, position-estimate failures, SmartRTL deactivation, bad-position messages, and navigation-related mode behavior.

### 3. Power / battery

Inputs include voltage, current, sag, minimum voltage, high-current episodes, power-related warnings and timing relative to maneuver/load.

### 4. ESC / RPM / thrust

Inputs include ESC telemetry, RPM asymmetry, RPM drops, motor imbalance, Potential Thrust Loss events and related attitude/power behavior.

### 5. Pilot control / modes

Inputs include flight-mode transitions, RC/channel changes when available, emergency-stop/drop events, failsafe transitions, RTL/LAND behavior and other control actions.

This module reports what was observed, not what the pilot “should have” done.

### 6. Flight termination / critical events

Inputs include DISARM, crash/disarm reason, log ending while ARMED, landing confirmation, last telemetry, and terminal warning sequences.

A TLOG ending in ARMED is described only as: recording ended while ARMED; subsequent state is unknown unless another source confirms it.

## Standard module result

Each module returns a structured object similar to:

```json
{
  "status": "confirmed_problem | probable_problem | no_significant_issue | unknown",
  "severity": "info | warning | critical",
  "confidence": 0.0,
  "start_time_s": null,
  "end_time_s": null,
  "evidence": [],
  "counter_evidence": [],
  "related_events": []
}
```

Confidence must reflect independent signal classes. Repeated identical messages do not count as independent evidence.

## Reconstruction engine

The reconstruction engine merges only high-value events from the same session into chronological order and labels relationships conservatively:

- before
- after
- simultaneous/near-simultaneous
- correlated in time
- possible relation
- causal relation not established

It must never convert temporal proximity into causality automatically.

Repeated events are grouped into episodes to avoid verbose output.

For a problematic flight, the engine should generate a focused chronology around the important part of the session, especially the final 30–60 seconds when appropriate.

## Narrative output

The final AI panel should be session-aware and contain:

### General summary

Example:

> 4 ARM sessions were detected. The first three were short sessions without confirmed critical deviations. The main anomalies are concentrated in session #4.

### Primary flight header

- session number
- ARM time
- DISARM time or “not recorded”
- duration
- classification (`flight`, `arm_check`, `uncertain`)
- overall severity

### Short technical conclusion

2–4 sentences summarizing the session without overstating causality.

### Key event chronology

A compact list of meaningful events and grouped episodes.

### Subsystem analysis

Separate cards/sections for radio, navigation/EKF, power, ESC/RPM/thrust, control/modes, and termination state.

Each section shows status, confidence, evidence, counter-evidence when useful, and timing.

### Confirmed by TLOG

Facts only.

### Probable interpretation

Engineering interpretation with explicit confidence and caveats.

### What cannot be established

Mandatory section for important unknowns, such as post-log DISARM/landing or causal links that cannot be proven from TLOG alone.

### What to inspect after flight

Concrete technical checks derived only from the affected subsystems. This replaces wording such as “what could have helped.”

## UI behavior

Normal ARM checks remain compact. Problematic flights expand automatically, with the primary problem session shown first.

The current AI block should be replaced or upgraded without removing the stable non-AI telemetry sections.

The UI should make confidence understandable but not decorative: confidence reflects data support, not model certainty in a conversational sense.

## Backward compatibility

Existing analyzer response fields remain available unless explicitly deprecated later.

The new expert result should be added as a new structured field first so frontend migration is reversible.

If expert analysis throws an exception, the API still returns the stable TLOG result with an expert-analysis warning rather than failing the request.

## Testing strategy

Tests must cover at minimum:

1. Multiple ARM sessions with only one problematic flight.
2. Multiple normal short ARM checks.
3. Two problematic flights in one TLOG.
4. Log ending ARMED without overclaiming crash/landing.
5. Repeated radio messages not inflating confidence.
6. Independent radio evidence increasing confidence.
7. EKF/GPS and radio events occurring near each other without automatic causal claim.
8. Power problem without radio problem.
9. ESC/RPM/thrust issue with supporting evidence.
10. No dominant problem: output remains cautious and useful.
11. Existing analyzer response still succeeds when expert layer fails.
12. Frontend renders compact normal sessions and expanded problematic sessions correctly.

## Rollback strategy

All implementation is isolated on `feature/ai-flight-expert-analyzer`. `main` remains unchanged until explicit merge approval.

The expert result is introduced alongside existing output so the feature can be removed or disabled without rewriting the stable parser.

If the result is not satisfactory, the branch can be abandoned and the existing analyzer behavior remains intact.

## Out of scope for this iteration

- External/cloud AI or LLM calls.
- Raw TLOG upload to third-party services.
- Video/TLOG joint inference.
- Automatic model learning from past logs.
- Replacing the stable parser.

These can be considered later after the session-aware expert engine proves reliable.
