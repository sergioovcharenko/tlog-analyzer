# AI Flight Expert Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a session-aware internal expert analyzer that evaluates each ARM session independently, analyzes six UAV subsystems, reconstructs event chronology conservatively, and renders a deeper AI conclusion without any external AI service.

**Architecture:** Keep the stable TLOG parser and current `ai_reconstruction` output unchanged as the factual source and fallback. Add a new `ai_expert` pipeline: ARM-session segmentation and classification -> per-session evidence extraction -> six subsystem analyzers -> conservative chronology reconstruction -> session prioritization -> structured narrative -> frontend rendering. The new pipeline is additive and fail-closed.

**Tech Stack:** Python 3.11, FastAPI, pymavlink-derived timeline already produced by `backend/main.py`, plain HTML/CSS/JavaScript in `index.html`, Python `unittest`, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-16-ai-flight-expert-analyzer-design.md`

## Global Constraints

- Do not call external/cloud AI or LLM services.
- Do not upload raw TLOG data to third parties.
- Do not replace the stable parser.
- Never mix events from different ARM sessions unless explicitly comparing sessions.
- Distinguish `arm_check`, `flight`, and `uncertain` sessions.
- Repeated events from the same evidence class must not inflate confidence.
- Temporal proximity must never be converted automatically into causality.
- `ended ARMED` means only that the recording ended while ARMED; it does not prove crash, landing, or the final aircraft state.
- Existing `ai_reconstruction` and all stable telemetry sections remain available as fallback.
- Expert analysis failure must not fail the `/analyze` request.
- Implementation stays on `feature/ai-flight-expert-analyzer`; `main` remains untouched until explicit merge approval.
- No new Python dependency is required for this iteration.

---

### Task 1: ARM-session segmentation and classification

**Files:**
- Create: `backend/ai_expert_sessions.py`
- Create: `tests/test_ai_expert_sessions.py`

**Interfaces:**
- Consumes: existing `timeline` rows from `backend/main.py`.
- Produces:
  - `parse_timeline_time_s(value) -> float | None`
  - `segment_arm_sessions(timeline: list[dict]) -> list[dict]`
  - `classify_arm_session(session: dict) -> str`
- Session object keys: `session_id`, `start_s`, `end_s`, `duration_s`, `ended_with_disarm`, `ended_by_log`, `rows`, `classification`, `classification_evidence`, `metrics`.

- [ ] **Step 1: Write failing session tests**

```python
import unittest

from backend.ai_expert_sessions import segment_arm_sessions


class AIExpertSessionTest(unittest.TestCase):
    def test_three_short_checks_and_one_real_flight_are_separated(self):
        timeline = [
            {"time": "00:01.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "00:05.000", "eventType": "SNAPSHOT", "alt": 0.2, "dist": "1 m", "groundSpeed": 0.1},
            {"time": "00:08.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "01:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "01:05.000", "eventType": "SNAPSHOT", "alt": 0.3, "dist": "2 m", "groundSpeed": 0.2},
            {"time": "01:09.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "02:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "02:06.000", "eventType": "SNAPSHOT", "alt": 0.4, "dist": "1 m", "groundSpeed": 0.2},
            {"time": "02:10.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "05:05.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "05:12.000", "eventType": "SNAPSHOT", "alt": 4.0, "dist": "25 m", "groundSpeed": 4.2},
            {"time": "07:00.000", "eventType": "SNAPSHOT", "alt": 100.0, "dist": "900 m", "groundSpeed": 11.0},
        ]
        sessions = segment_arm_sessions(timeline)
        self.assertEqual([s["classification"] for s in sessions], ["arm_check", "arm_check", "arm_check", "flight"])
        self.assertTrue(sessions[-1]["ended_by_log"])
        self.assertFalse(sessions[-1]["ended_with_disarm"])

    def test_no_takeoff_evidence_is_not_called_flight(self):
        timeline = [
            {"time": "00:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "00:45.000", "eventType": "SNAPSHOT", "alt": 0.5, "dist": "4 m", "groundSpeed": 0.4},
            {"time": "00:50.000", "eventType": "FLIGHT_SESSION_END"},
        ]
        self.assertEqual(segment_arm_sessions(timeline)[0]["classification"], "uncertain")
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python -m unittest tests.test_ai_expert_sessions -v
```

Expected: FAIL because `backend.ai_expert_sessions` does not exist.

- [ ] **Step 3: Implement time parsing, segmentation, metrics, and conservative classification**

Use exact initial thresholds:

```python
FLIGHT_ALTITUDE_SPAN_M = 2.0
FLIGHT_HOME_DISTANCE_M = 15.0
FLIGHT_GROUND_SPEED_MS = 2.5
ARM_CHECK_MAX_DURATION_S = 30.0
```

Classification rule:

```python
is_flight = duration_s >= 5.0 and (
    altitude_span_m >= FLIGHT_ALTITUDE_SPAN_M
    or max_distance_m >= FLIGHT_HOME_DISTANCE_M
    or max_ground_speed_ms >= FLIGHT_GROUND_SPEED_MS
)
if is_flight:
    return "flight"
if duration_s <= ARM_CHECK_MAX_DURATION_S and altitude_span_m < 2.0 and max_distance_m < 15.0 and max_ground_speed_ms < 2.5:
    return "arm_check"
return "uncertain"
```

`dist` must support meters and kilometers. An open final session ends at the last valid timeline time and sets `ended_by_log=True`.

- [ ] **Step 4: Run session tests and existing AI tests**

```bash
python -m unittest tests.test_ai_expert_sessions tests.test_ai_reconstruction -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/ai_expert_sessions.py tests/test_ai_expert_sessions.py
git commit -m "feat: segment and classify ARM sessions"
```

---

### Task 2: Standard evidence model and six subsystem analyzers

**Files:**
- Create: `backend/ai_expert_modules.py`
- Create: `tests/test_ai_expert_modules.py`

**Interfaces:**
- Consumes: one normalized session plus session-scoped radio/thrust/RPM events.
- Produces these exact functions:
  - `analyze_radio(session, radio_events) -> dict`
  - `analyze_navigation(session) -> dict`
  - `analyze_power(session) -> dict`
  - `analyze_propulsion(session, thrust_events, rpm_events) -> dict`
  - `analyze_control_modes(session) -> dict`
  - `analyze_termination(session) -> dict`
- Every result contains: `status`, `severity`, `confidence`, `start_time_s`, `end_time_s`, `evidence`, `counter_evidence`, `related_events`, `source_classes`.

- [ ] **Step 1: Write failing tests for independent-evidence confidence**

```python
import unittest

from backend.ai_expert_modules import analyze_radio, analyze_navigation, analyze_termination


class AIExpertModuleTest(unittest.TestCase):
    def setUp(self):
        self.session = {
            "session_id": 4,
            "start_s": 300.0,
            "end_s": 600.0,
            "classification": "flight",
            "rows": [],
        }

    def test_twenty_repeated_radio_gaps_do_not_count_as_twenty_independent_sources(self):
        events = [{"time_s": 400.0 + i, "dbm": -128, "recovered": True} for i in range(20)]
        result = analyze_radio(self.session, events)
        self.assertIn("mavlink_gap", result["source_classes"])
        self.assertLessEqual(len(result["source_classes"]), 3)
        self.assertLess(result["confidence"], 0.90)

    def test_independent_radio_sources_raise_confidence(self):
        events = [
            {"time_s": 420.0, "dbm": -128, "recovered": False},
            {"time_s": 430.0, "type": "failsafe", "text": "Radio failsafe"},
        ]
        result = analyze_radio(self.session, events)
        self.assertGreaterEqual(len(result["source_classes"]), 3)
        self.assertGreaterEqual(result["confidence"], 0.85)

    def test_navigation_message_is_reported_without_radio_causality(self):
        self.session["rows"] = [
            {"time": "07:46.000", "systemText": "EKF3 IMU0 stopped aiding"},
            {"time": "07:47.000", "systemText": "SmartRTL deactivated: bad position"},
        ]
        result = analyze_navigation(self.session)
        joined = " ".join(result["evidence"]).lower()
        self.assertIn("stopped aiding", joined)
        self.assertIn("bad position", joined)
        self.assertNotIn("через раді", joined)

    def test_ended_armed_never_claims_crash(self):
        self.session["ended_by_log"] = True
        self.session["ended_with_disarm"] = False
        result = analyze_termination(self.session)
        joined = " ".join(result["evidence"] + result["counter_evidence"]).lower()
        self.assertIn("armed", joined)
        self.assertNotIn("авар", joined)
        self.assertNotIn("crash", joined)
```

- [ ] **Step 2: Verify RED**

```bash
python -m unittest tests.test_ai_expert_modules -v
```

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement the common module result and confidence helper**

Use a confidence map based on unique evidence classes only:

```python
def confidence_from_sources(source_classes):
    count = len(set(source_classes))
    if count <= 0:
        return 0.0
    if count == 1:
        return 0.55
    if count == 2:
        return 0.75
    if count == 3:
        return 0.88
    return 0.94
```

Radio source classes are limited to `mavlink_gap`, `critical_dbm`, `unrecovered_link`, `failsafe_text`. Repeated messages in one class do not increase confidence.

Navigation source classes include `ekf_state`, `position_estimate`, `smartrtl_bad_position`, `gps_quality` when those facts are actually present.

Power must not declare a fault from high current or a minimum voltage alone. Use combinations such as voltage sag plus high load, explicit battery/power warning, or multiple independent power indicators.

Propulsion source classes include `thrust_loss`, `rpm_asymmetry`, `rpm_drop`, `esc_warning`.

Control/mode analysis is observational; it may describe `RTL -> LAND`, failsafe transitions, Emergency STOP/drop events, and RC activity, but never phrase them as pilot blame.

Termination reports DISARM when recorded, and otherwise reports recording termination conservatively.

- [ ] **Step 4: Run module tests**

```bash
python -m unittest tests.test_ai_expert_modules -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/ai_expert_modules.py tests/test_ai_expert_modules.py
git commit -m "feat: add expert subsystem analyzers"
```

---

### Task 3: Session orchestration, prioritization, chronology, and narrative

**Files:**
- Create: `backend/ai_expert.py`
- Create: `tests/test_ai_expert.py`

**Interfaces:**
- `build_ai_expert_analysis(*, timeline, radio_events, thrust_events, rpm_events) -> dict`
- Result shape:

```python
{
    "version": 1,
    "summary": str,
    "primary_session_id": int | None,
    "sessions": [
        {
            "session_id": int,
            "classification": str,
            "start_s": float,
            "end_s": float,
            "duration_s": float,
            "overall_severity": str,
            "short_conclusion": str,
            "chronology": list,
            "subsystems": dict,
            "confirmed": list,
            "interpretation": list,
            "unknowns": list,
            "checks": list,
        }
    ],
    "warnings": [],
}
```

- [ ] **Step 1: Write failing orchestration tests for the target 4-session behavior**

```python
import unittest

from backend.ai_expert import build_ai_expert_analysis


class AIExpertTest(unittest.TestCase):
    def test_problem_is_attributed_to_fourth_session_only(self):
        timeline = [
            {"time": "00:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "00:08.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "01:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "01:08.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "02:00.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "02:08.000", "eventType": "FLIGHT_SESSION_END"},
            {"time": "05:05.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "05:15.000", "eventType": "SNAPSHOT", "alt": 10.0, "dist": "40 m", "groundSpeed": 5.0},
            {"time": "07:46.000", "systemText": "EKF3 IMU0 stopped aiding"},
            {"time": "07:47.000", "systemText": "SmartRTL deactivated: bad position"},
            {"time": "08:00.000", "eventType": "SNAPSHOT", "alt": 80.0, "dist": "900 m", "groundSpeed": 10.0},
        ]
        result = build_ai_expert_analysis(
            timeline=timeline,
            radio_events=[{"time_s": 450.0, "dbm": -128, "recovered": False}],
            thrust_events=[],
            rpm_events=[],
        )
        self.assertEqual(result["primary_session_id"], 4)
        self.assertEqual(len(result["sessions"]), 4)
        self.assertTrue(all(s["overall_severity"] == "info" for s in result["sessions"][:3]))
        self.assertIn("4", result["summary"])

    def test_radio_then_ekf_is_described_as_sequence_not_cause(self):
        timeline = [
            {"time": "05:05.000", "eventType": "FLIGHT_SESSION_START"},
            {"time": "05:15.000", "eventType": "SNAPSHOT", "alt": 12.0, "dist": "30 m", "groundSpeed": 4.0},
            {"time": "07:46.000", "systemText": "EKF3 IMU0 stopped aiding"},
        ]
        result = build_ai_expert_analysis(
            timeline=timeline,
            radio_events=[{"time_s": 430.0, "dbm": -128, "recovered": False}],
            thrust_events=[],
            rpm_events=[],
        )
        session = result["sessions"][0]
        joined = " ".join(session["interpretation"]).lower()
        self.assertIn("раніше", joined)
        self.assertIn("причин", joined)
        self.assertNotIn("спричини", joined)
```

- [ ] **Step 2: Verify RED**

```bash
python -m unittest tests.test_ai_expert -v
```

- [ ] **Step 3: Implement session-scoped event assignment and priority**

Assign an event only when `session.start_s <= event.time_s <= session.end_s`. Never reuse one event in another session.

Primary-session ordering is deterministic and based on:

```python
severity_rank = {"info": 0, "warning": 1, "critical": 2}
key = (
    severity_rank[session["overall_severity"]],
    affected_subsystem_count,
    unique_evidence_class_count,
    session["session_id"],
)
```

Sort descending. Raw event count is not part of the key.

- [ ] **Step 4: Implement conservative chronology and narrative**

Chronology contains grouped high-value events only. If two subsystem events are close in time, permitted language is `часово близькі` or `зафіксовано раніше/пізніше`; append `причинний зв'язок за TLOG не встановлено` when an interpretation compares them.

Mandatory unknown for open ARMED session:

```text
Запис TLOG завершився, коли стан ARMED ще був активний. Подальший DISARM або фактичний стан апарата в цьому файлі не зафіксовані.
```

Post-flight checks are subsystem-derived only:
- radio -> antennas, RF connectors/modules, transmitter/receiver link and interference context;
- navigation -> GPS, compass/IMU, EKF source configuration, external-nav source;
- power -> battery, connectors, voltage sag under load;
- propulsion -> ESC telemetry, motors, propellers, RPM symmetry;
- termination/control -> review mode/failsafe configuration and exact RC/event timeline.

- [ ] **Step 5: Run all expert unit tests**

```bash
python -m unittest tests.test_ai_expert_sessions tests.test_ai_expert_modules tests.test_ai_expert -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/ai_expert.py tests/test_ai_expert.py
git commit -m "feat: reconstruct per-flight expert analysis"
```

---

### Task 4: Integrate expert analysis into the existing backend with fallback

**Files:**
- Modify: `backend/main.py` around `AI_RECONSTRUCTION_IMPORT_V1`, `AI_RECONSTRUCTION_BACKEND_V1`, and the response dictionary.
- Create: `tests/test_ai_expert_integration.py`

**Interfaces:**
- Existing response key `ai_reconstruction` remains unchanged.
- Add response keys `ai_expert` and `ai_expert_warning`.
- `ai_expert` is `None` only when expert analysis cannot be built.

- [ ] **Step 1: Write failing integration/contract tests**

```python
from pathlib import Path
import unittest

SOURCE = Path("backend/main.py").read_text(encoding="utf-8")


class AIExpertIntegrationTest(unittest.TestCase):
    def test_backend_keeps_legacy_and_adds_expert_fields(self):
        self.assertIn('"ai_reconstruction": ai_reconstruction', SOURCE)
        self.assertIn('"ai_expert": ai_expert', SOURCE)
        self.assertIn('"ai_expert_warning": ai_expert_warning', SOURCE)

    def test_expert_builder_is_guarded_by_exception_fallback(self):
        self.assertIn("build_ai_expert_analysis", SOURCE)
        self.assertIn("ai_expert_warning", SOURCE)
        self.assertIn("except Exception as", SOURCE)
```

- [ ] **Step 2: Verify RED**

```bash
python -m unittest tests.test_ai_expert_integration -v
```

- [ ] **Step 3: Normalize existing parser events for the expert engine**

Reuse timeline fields already produced by the parser (`alt`, `dist`, `groundSpeed`, `volt`, `curr`, `dbm`, `mode`, `esc`, `systemText`). Convert `communication_loss_episodes`, `potential_thrust_loss_events`, and `rpm_drop_events` to `time_s` relative to `base_t` before passing them to the expert engine.

Do not use global min/max from one flight as evidence in another flight when a session-scoped sample is available.

- [ ] **Step 4: Call the expert builder in a fail-closed block**

Required pattern:

```python
ai_expert = None
ai_expert_warning = None
try:
    ai_expert = build_ai_expert_analysis(
        timeline=timeline,
        radio_events=_expert_radio_events,
        thrust_events=_expert_thrust_events,
        rpm_events=_expert_rpm_events,
    )
except Exception as exc:
    ai_expert_warning = f"Експертний AI-аналіз недоступний: {exc}"
```

The ordinary analysis response must still be returned.

- [ ] **Step 5: Run backend regression tests**

```bash
python -m unittest tests.test_ai_reconstruction tests.test_ai_reconstruction_integration tests.test_ai_expert_sessions tests.test_ai_expert_modules tests.test_ai_expert tests.test_ai_expert_integration -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/test_ai_expert_integration.py
git commit -m "feat: integrate expert analysis with safe fallback"
```

---

### Task 5: Render the expanded session-aware AI conclusion

**Files:**
- Modify: `index.html` near the existing `aiReconstructionBlock`, its CSS, and `renderAiReconstruction`/`renderResults`.
- Create: `tests/test_ai_expert_frontend_contract.py`

**Interfaces:**
- New renderer: `renderAiExpert(expert)`.
- New container IDs: `aiExpertBlock`, `aiExpertSummary`, `aiExpertSessions`, `aiExpertDetails`.
- If `data.ai_expert` exists, render it and hide the legacy reconstruction block.
- If `data.ai_expert` is absent, preserve current `renderAiReconstruction(data.ai_reconstruction)` behavior.

- [ ] **Step 1: Write failing frontend contract tests**

```python
from pathlib import Path
import unittest

HTML = Path("index.html").read_text(encoding="utf-8")


class AIExpertFrontendContractTest(unittest.TestCase):
    def test_expert_ui_and_renderer_exist(self):
        for marker in (
            'id="aiExpertBlock"',
            'id="aiExpertSummary"',
            'id="aiExpertSessions"',
            'id="aiExpertDetails"',
            'function renderAiExpert(expert)',
            'renderAiExpert(data.ai_expert)',
        ):
            self.assertIn(marker, HTML)

    def test_legacy_renderer_remains_as_fallback(self):
        self.assertIn("function renderAiReconstruction(recon)", HTML)
        self.assertIn("data.ai_reconstruction", HTML)

    def test_new_headings_use_confirmed_probable_unknown_checks(self):
        for text in ("ПІДТВЕРДЖЕНО TLOG", "ЙМОВІРНА ІНТЕРПРЕТАЦІЯ", "ЩО НЕМОЖЛИВО ВСТАНОВИТИ", "ЩО ПЕРЕВІРИТИ"):
            self.assertIn(text, HTML)
```

- [ ] **Step 2: Verify RED**

```bash
python -m unittest tests.test_ai_expert_frontend_contract -v
```

- [ ] **Step 3: Add compact session cards and an expanded primary session**

Normal `arm_check` sessions show one compact line with ARM start, duration, classification, and `критичних відхилень не виявлено` when appropriate.

The primary problematic session expands automatically and shows:
- short conclusion;
- chronology;
- six subsystem cards with status/confidence/evidence;
- `ПІДТВЕРДЖЕНО TLOG`;
- `ЙМОВІРНА ІНТЕРПРЕТАЦІЯ`;
- `ЩО НЕМОЖЛИВО ВСТАНОВИТИ`;
- `ЩО ПЕРЕВІРИТИ`.

Do not show the old label `Що могло допомогти` in the expert block.

- [ ] **Step 4: Preserve fallback rendering**

Required flow inside `renderResults(data)`:

```javascript
if (data.ai_expert) {
  renderAiExpert(data.ai_expert);
} else {
  renderAiExpert(null);
  renderAiReconstruction(data.ai_reconstruction);
}
```

- [ ] **Step 5: Run frontend contracts and JavaScript syntax check**

```bash
python -m unittest tests.test_ai_reconstruction_frontend_contract tests.test_ai_expert_frontend_contract -v
python - <<'PY'
from pathlib import Path
import re
s = Path('index.html').read_text(encoding='utf-8')
scripts = re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', s, flags=re.S|re.I)
Path('/tmp/tlog-inline.js').write_text('\n'.join(scripts), encoding='utf-8')
PY
node --check /tmp/tlog-inline.js
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add index.html tests/test_ai_expert_frontend_contract.py
git commit -m "feat: render session-aware expert AI conclusion"
```

---

### Task 6: CI, full regression, and rollback verification

**Files:**
- Modify: `.github/workflows/ai-reconstruction.yml`
- Test: full `tests/test_*.py` suite

**Interfaces:**
- CI runs on `feature/ai-flight-expert-analyzer` changes.
- The workflow compiles `backend/ai_expert.py`, `backend/ai_expert_sessions.py`, and `backend/ai_expert_modules.py` in addition to existing backend files.

- [ ] **Step 1: Extend workflow paths and tests**

Add the feature branch to push triggers and include:

```yaml
- backend/ai_expert.py
- backend/ai_expert_sessions.py
- backend/ai_expert_modules.py
- tests/test_ai_expert.py
- tests/test_ai_expert_sessions.py
- tests/test_ai_expert_modules.py
- tests/test_ai_expert_integration.py
- tests/test_ai_expert_frontend_contract.py
```

Add one explicit expert test step:

```yaml
- name: Run AI flight expert tests
  run: python -m unittest tests.test_ai_expert_sessions tests.test_ai_expert_modules tests.test_ai_expert tests.test_ai_expert_integration tests.test_ai_expert_frontend_contract -v
```

Do not let this workflow auto-commit generated expert changes; expert files and UI are edited directly on the feature branch.

- [ ] **Step 2: Run focused tests locally/CI**

```bash
python -m unittest \
  tests.test_ai_reconstruction \
  tests.test_ai_reconstruction_integration \
  tests.test_ai_reconstruction_frontend_contract \
  tests.test_ai_expert_sessions \
  tests.test_ai_expert_modules \
  tests.test_ai_expert \
  tests.test_ai_expert_integration \
  tests.test_ai_expert_frontend_contract -v
```

Expected: PASS.

- [ ] **Step 3: Run full regression**

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: PASS. If a pre-existing unrelated test is already failing on the branch baseline, document it explicitly and verify no new failure is introduced.

- [ ] **Step 4: Compile backend and validate JS syntax**

```bash
python -m py_compile backend/main.py backend/ai_reconstruction.py backend/ai_expert.py backend/ai_expert_sessions.py backend/ai_expert_modules.py
node --check /tmp/tlog-inline.js
```

Expected: PASS.

- [ ] **Step 5: Verify reversibility against `main`**

```bash
git diff --stat main...feature/ai-flight-expert-analyzer
git diff main...feature/ai-flight-expert-analyzer -- backend/main.py index.html backend/ai_expert.py backend/ai_expert_sessions.py backend/ai_expert_modules.py
```

Confirm that removing the new `ai_expert` integration leaves the existing `ai_reconstruction` path intact.

- [ ] **Step 6: Commit workflow changes**

```bash
git add .github/workflows/ai-reconstruction.yml
git commit -m "ci: verify AI flight expert analyzer"
```

---

## Self-review results

- Spec coverage: all six expert modules, ARM-session separation, session priority, confidence by independent evidence, conservative chronology, mandatory unknowns, post-flight checks, frontend behavior, backend fallback, and rollback are assigned to explicit tasks.
- Placeholder scan: no `TODO`, `TBD`, or undefined implementation placeholders remain in this plan.
- Type consistency: session keys and module-result keys are identical across Tasks 1–5; the API key is consistently `ai_expert`.
- Backward compatibility: legacy `ai_reconstruction` is never removed in this iteration.
