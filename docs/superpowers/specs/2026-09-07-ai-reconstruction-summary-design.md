# AI Reconstruction Summary Design

Date: 2026-09-07
Repository: `sergioovcharenko/tlog-analyzer`
Feature branch: `feature/ai-reconstruction-summary`
Rollback branch: `backup-before-ai-reconstruction`
Rollback baseline commit: `398f355b0e6e5e80a40c1b8f618f190ec8b4cf5b`

## Goal

Keep the current detailed rule-based findings unchanged and add a new AI-style reconstruction block below them. The block must synthesize existing TLOG evidence into a concise narrative that explains:

1. what happened;
2. the most likely event sequence;
3. what pilot actions were observed or not observed;
4. what alternative actions could have helped, phrased cautiously;
5. confidence level.

The new layer must work across different TLOGs and must not be hardcoded to one flight.

## Non-goals

- Do not remove, reorder, or weaken the existing technical findings list.
- Do not rely on a remote LLM or external AI API.
- Do not invent facts not present in parsed TLOG data.
- Do not label pilot actions as definite mistakes.
- Do not replace the current analyzer rules; this is an additional synthesis layer.

## Architecture

Add a deterministic `AI reconstruction` layer on top of already parsed telemetry and existing findings. It will consume structured facts already produced by the backend/timeline logic and produce a structured summary object for the frontend.

Recommended output structure:

- `what_happened`
- `likely_sequence`
- `pilot_actions`
- `possible_alternatives`
- `confidence`
- `evidence`

The frontend renders this as a new `🤖 AI ВИСНОВОК` block below the current findings.

## Universal inference rules

### Radio-link instability

If repeated radio-loss episodes or repeated `-128 dBm` values are detected, classify the radio link as unstable. Include the number of episodes when available.

If the final radio-loss episode is not followed by a confirmed recovery, state that the final loss remained unconfirmed as recovered.

### VTX/video channel reaction

After a critical radio/video-loss episode, check whether a VTX/video channel change occurred within the configured reaction window. If not, state only that no channel change was recorded in that episode.

Do not say a channel change would definitely have restored control/video.

### Altitude reaction

For each critical radio-loss episode, inspect altitude around the episode.

If the aircraft remains within approximately 5 m of the episode altitude for the reaction window, report that no pronounced climb was recorded. Example wording:

> Висота утримувалась приблизно біля 70 м; вираженого набору висоти після втрати зв’язку не зафіксовано.

The value must be computed from the TLOG, not hardcoded.

The conclusion may add that gaining altitude can sometimes improve radio line-of-sight, but must phrase this as a possible option rather than a guaranteed correction.

### RTL to LAND transition

Detect mode transitions and compute time deltas.

If `RTL -> LAND` occurs within a short threshold (initial proposal: <= 2.0 s), state that RTL had very little time to continue before LAND began.

If LAND begins far from HOME, state that the aircraft began landing away from the home point.

Do not claim causation unless telemetry supports it.

### Armed termination

If the TLOG ends while ARMED and no DISARM is confirmed, include this as a significant end-state fact.

### Propulsion/power scenario

If a different TLOG contains combinations such as Potential Thrust Loss, RPM asymmetry, voltage sag, high current, ESC/motor anomalies, the AI reconstruction must prioritize the propulsion/power scenario instead of forcing a radio-link narrative.

### Normal flights

If no strong critical pattern is present, the block should say that no single dominant failure mechanism was identified rather than inventing one.

## Confidence model

Use a simple deterministic confidence score based on corroborating evidence.

Suggested labels:

- `Висока` — several independent telemetry facts support the same scenario;
- `Середня` — a plausible sequence exists but some links are indirect;
- `Низька` — evidence is sparse or ambiguous.

The visible text should explain uncertainty when confidence is not high.

## Safety and wording rules

Prefer wording such as:

- `не зафіксовано` instead of `не зробив` when telemetry cannot prove intent;
- `могло допомогти` instead of `потрібно було`;
- `ймовірний сценарій` instead of `точна причина` unless directly confirmed;
- `за даними TLOG` whenever interpreting absent actions.

The analyzer must not infer pilot intent from missing telemetry.

## UI

The existing findings remain exactly where they are.

Immediately below them, add a visually distinct block:

`🤖 AI ВИСНОВОК`

Recommended sections:

- `Що сталося`
- `Ймовірна послідовність`
- `Дії, зафіксовані в TLOG`
- `Що могло допомогти`
- `Впевненість аналізу`

The block should be concise enough to read quickly but preserve specific values and timestamps where useful.

## Example behavior for the currently discussed log

The exact wording will be generated from telemetry, but the logic should be able to produce a conclusion equivalent to:

- repeated radio-link drops to `-128 dBm` were observed;
- the aircraft remained around roughly 70 m without a pronounced climb during the relevant loss episode;
- no VTX/video-channel change was recorded after the critical episode;
- RTL was followed by LAND after a very short interval;
- landing then began away from HOME;
- the final loss of communication was not confirmed as recovered;
- this combination makes radio-link instability the leading scenario, while clearly marking it as probabilistic.

## Data flow

1. Existing MAVLink/TLOG parser produces telemetry and timeline facts.
2. Existing rule engine continues producing the detailed findings list.
3. New reconstruction builder consumes structured facts, not rendered Ukrainian strings where avoidable.
4. Reconstruction builder emits a structured JSON object.
5. Frontend renders the AI block below the existing list.

## Testing

Add regression tests covering at least:

1. repeated `-128 dBm` + no VTX change + stable altitude;
2. repeated `-128 dBm` + confirmed VTX change;
3. short `RTL -> LAND` transition;
4. LAND far from HOME;
5. propulsion/power-dominated incident so radio logic does not dominate incorrectly;
6. normal log with no critical scenario;
7. wording guard: no categorical `pilot mistake` statements;
8. existing detailed findings remain present and unchanged.

Use synthetic structured fixtures where possible and at least one representative real-log-derived fixture if already available in the repository.

## Rollback

Before implementation, the exact current production baseline has been preserved in branch:

`backup-before-ai-reconstruction`

pointing to commit:

`398f355b0e6e5e80a40c1b8f618f190ec8b4cf5b`

If the new reconstruction behaves incorrectly, production can be restored from this branch without affecting the preserved historical backup branches.

## Acceptance criteria

The change is accepted when:

- all current technical findings still render;
- the new AI block appears below them;
- its content changes appropriately across different log patterns;
- it includes stable-altitude context when applicable, using the actual measured altitude;
- it recognizes short RTL-to-LAND transitions;
- it can note missing VTX/channel changes after critical loss episodes;
- it uses cautious, evidence-based language;
- existing graph/timeline functionality remains unchanged;
- regression tests pass;
- rollback branch remains untouched.
