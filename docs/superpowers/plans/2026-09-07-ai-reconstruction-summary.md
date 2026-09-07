# AI Reconstruction Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, evidence-based `🤖 AI ВИСНОВОК` below the existing findings that reconstructs likely event sequences across different TLOG patterns without removing or weakening any current rules.

**Architecture:** Keep the current parser and detailed findings intact. Add a backend reconstruction builder that consumes structured telemetry facts and emits a structured `ai_reconstruction` object; render that object in `index.html` below the existing findings. The builder prioritizes radio-link, propulsion/power, or neutral scenarios based on corroborating evidence, and uses cautious wording for absent actions and alternatives.

**Tech Stack:** Python 3.11 backend, pymavlink-derived telemetry already present in `backend/main.py`, plain HTML/CSS/JavaScript frontend in `index.html`, Python `unittest` regression tests, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-07-ai-reconstruction-summary-design.md`

## Global Constraints

- Preserve rollback branch `backup-before-ai-reconstruction` at commit `398f355b0e6e5e80a40c1b8f618f190ec8b4cf5b`; do not rewrite or delete it.
- Do not remove, reorder, or weaken the existing technical findings list.
- Do not rely on a remote LLM or external AI API.
- Do not invent facts not present in parsed TLOG data.
- Do not label pilot actions as definite mistakes.
- Use measured altitude values from telemetry; never hardcode `70 m`.
- Initial short-transition threshold: `RTL -> LAND <= 2.0 s`.
- Stable-altitude threshold during a reaction window: total altitude spread `<= 5.0 m`.
- Existing graph/timeline behavior must remain unchanged.

---

### Task 1: Define the reconstruction contract and core rule engine

**Files:**
- Create: `backend/ai_reconstruction.py`
- Create: `tests/test_ai_reconstruction.py`

**Interfaces:**
- Consumes: a plain structured fact dictionary produced by the analyzer.
- Produces: `build_ai_reconstruction(facts: dict) -> dict` with keys `what_happened`, `likely_sequence`, `pilot_actions`, `possible_alternatives`, `confidence`, `evidence`, `dominant_scenario`.

- [ ] **Step 1: Write failing contract tests for radio, power, and neutral scenarios**

```python
import unittest

from backend.ai_reconstruction import build_ai_reconstruction


class AIReconstructionTest(unittest.TestCase):
    def test_radio_scenario_uses_actual_altitude_and_cautious_language(self):
        facts = {
            "radio_loss_episodes": [
                {"time_s": 120.0, "dbm": -128, "recovered": True},
                {"time_s": 180.0, "dbm": -128, "recovered": False},
            ],
            "critical_radio_episode": {
                "time_s": 180.0,
                "altitude_m": 69.8,
                "altitude_window_min_m": 68.9,
                "altitude_window_max_m": 71.2,
                "vtx_changed": False,
            },
            "mode_transitions": [
                {"from": "RTL", "to": "LAND", "time_s": 201.1, "delta_s": 0.7}
            ],
            "land_distance_home_m": 1360.0,
            "ended_armed": True,
            "power": {},
        }
        result = build_ai_reconstruction(facts)
        self.assertEqual(result["dominant_scenario"], "radio")
        joined = " ".join(
            result["what_happened"]
            + result["likely_sequence"]
            + result["pilot_actions"]
            + result["possible_alternatives"]
        )
        self.assertIn("69.8", joined)
        self.assertIn("RTL", joined)
        self.assertIn("LAND", joined)
        self.assertIn("не зафіксовано", joined)
        self.assertNotIn("помилка пілота", joined.lower())
        self.assertNotIn("потрібно було", joined.lower())

    def test_confirmed_vtx_change_is_not_reported_as_missing(self):
        facts = {
            "radio_loss_episodes": [{"time_s": 90.0, "dbm": -128, "recovered": True}],
            "critical_radio_episode": {
                "time_s": 90.0,
                "altitude_m": 80.0,
                "altitude_window_min_m": 79.0,
                "altitude_window_max_m": 83.0,
                "vtx_changed": True,
            },
            "mode_transitions": [],
            "land_distance_home_m": None,
            "ended_armed": False,
            "power": {},
        }
        result = build_ai_reconstruction(facts)
        joined = " ".join(result["pilot_actions"])
        self.assertNotIn("зміна відеоканалу не зафіксована", joined.lower())

    def test_power_scenario_wins_when_power_evidence_is_stronger(self):
        facts = {
            "radio_loss_episodes": [{"time_s": 50.0, "dbm": -128, "recovered": True}],
            "critical_radio_episode": None,
            "mode_transitions": [],
            "land_distance_home_m": None,
            "ended_armed": True,
            "power": {
                "potential_thrust_loss_count": 3,
                "rpm_asymmetry_pct": 47.0,
                "min_voltage_v": 10.09,
                "max_current_a": 83.9,
            },
        }
        result = build_ai_reconstruction(facts)
        self.assertEqual(result["dominant_scenario"], "power")

    def test_normal_log_does_not_invent_a_failure(self):
        facts = {
            "radio_loss_episodes": [],
            "critical_radio_episode": None,
            "mode_transitions": [],
            "land_distance_home_m": None,
            "ended_armed": False,
            "power": {},
        }
        result = build_ai_reconstruction(facts)
        self.assertEqual(result["dominant_scenario"], "none")
        self.assertTrue(any("не виявлено" in x.lower() for x in result["what_happened"]))
```

- [ ] **Step 2: Run the new test module and verify RED**

Run:

```bash
python -m unittest tests.test_ai_reconstruction -v
```

Expected: FAIL because `backend.ai_reconstruction` does not exist yet.

- [ ] **Step 3: Implement the minimal deterministic builder**

Create `backend/ai_reconstruction.py` with these exact public helpers:

```python
from __future__ import annotations

from typing import Any

STABLE_ALTITUDE_SPREAD_M = 5.0
SHORT_RTL_LAND_S = 2.0
LAND_AWAY_HOME_M = 100.0


def _confidence(label_points: int) -> str:
    if label_points >= 4:
        return "Висока"
    if label_points >= 2:
        return "Середня"
    return "Низька"


def build_ai_reconstruction(facts: dict[str, Any]) -> dict[str, Any]:
    radio = facts.get("radio_loss_episodes") or []
    episode = facts.get("critical_radio_episode")
    power = facts.get("power") or {}
    transitions = facts.get("mode_transitions") or []

    radio_score = len(radio)
    power_score = 0
    if power.get("potential_thrust_loss_count", 0):
        power_score += 2
    if (power.get("rpm_asymmetry_pct") or 0) >= 20:
        power_score += 2
    if power.get("min_voltage_v") is not None:
        power_score += 1
    if (power.get("max_current_a") or 0) >= 80:
        power_score += 1

    if power_score >= max(3, radio_score + 1):
        dominant = "power"
    elif radio_score >= 2 or episode:
        dominant = "radio"
    else:
        dominant = "none"

    out = {
        "what_happened": [],
        "likely_sequence": [],
        "pilot_actions": [],
        "possible_alternatives": [],
        "confidence": "Низька",
        "evidence": [],
        "dominant_scenario": dominant,
    }

    points = 0

    if dominant == "radio":
        out["what_happened"].append(
            f"Зафіксовано повторні епізоди нестабільної радіолінії ({len(radio)})."
        )
        points += 1
        if radio and radio[-1].get("recovered") is False:
            out["what_happened"].append("Останнє відновлення зв’язку після критичного епізоду не підтверджене TLOG.")
            points += 1

        if episode:
            alt = episode.get("altitude_m")
            amin = episode.get("altitude_window_min_m")
            amax = episode.get("altitude_window_max_m")
            if alt is not None and amin is not None and amax is not None and (amax - amin) <= STABLE_ALTITUDE_SPREAD_M:
                out["pilot_actions"].append(
                    f"Висота утримувалась приблизно біля {alt:.1f} м; вираженого набору висоти після втрати зв’язку не зафіксовано."
                )
                out["possible_alternatives"].append(
                    "Набір висоти інколи може покращити радіогоризонт, але TLOG не дозволяє стверджувати, що це гарантовано відновило б зв’язок."
                )
                points += 1
            if episode.get("vtx_changed") is False:
                out["pilot_actions"].append("Зміна VTX/відеоканалу після критичного епізоду не зафіксована.")
                out["possible_alternatives"].append(
                    "Зміна відеоканалу могла бути одним із варіантів перевірки якості відеолінії, але її ефект за цим TLOG наперед невідомий."
                )
                points += 1

        for tr in transitions:
            if tr.get("from") == "RTL" and tr.get("to") == "LAND" and (tr.get("delta_s") or 999) <= SHORT_RTL_LAND_S:
                out["likely_sequence"].append(
                    f"RTL змінився на LAND приблизно через {tr['delta_s']:.1f} с, тому RTL мав дуже мало часу для продовження повернення."
                )
                points += 1
                break

        dist = facts.get("land_distance_home_m")
        if dist is not None and dist >= LAND_AWAY_HOME_M:
            out["likely_sequence"].append(f"LAND розпочався приблизно за {dist:.0f} м від HOME.")
            points += 1

    elif dominant == "power":
        out["what_happened"].append("Сукупність телеметрії більше відповідає проблемі силової установки або живлення, ніж радіолінії.")
        if power.get("potential_thrust_loss_count", 0):
            out["evidence"].append(f"Potential Thrust Loss: {power['potential_thrust_loss_count']} подій")
            points += 1
        if power.get("rpm_asymmetry_pct") is not None:
            out["evidence"].append(f"Максимальна асиметрія RPM: {power['rpm_asymmetry_pct']:.1f}%")
            points += 1
        if power.get("min_voltage_v") is not None:
            out["evidence"].append(f"Мінімальна напруга: {power['min_voltage_v']:.2f} V")
            points += 1
        if power.get("max_current_a") is not None:
            out["evidence"].append(f"Піковий струм: {power['max_current_a']:.1f} A")
            points += 1

    else:
        out["what_happened"].append("За даними TLOG не виявлено одного домінуючого механізму відмови, підтвердженого кількома незалежними ознаками.")

    if facts.get("ended_armed"):
        out["what_happened"].append("Лог завершився при ARMED без підтвердженого DISARM.")
        points += 1

    out["confidence"] = _confidence(points)
    return out
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
python -m unittest tests.test_ai_reconstruction -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the core rule engine**

```bash
git add backend/ai_reconstruction.py tests/test_ai_reconstruction.py
git commit -m "feat: add deterministic AI reconstruction engine"
```

---

### Task 2: Extract structured reconstruction facts from existing analyzer telemetry

**Files:**
- Modify: `backend/main.py`
- Test: `tests/test_ai_reconstruction_integration.py`

**Interfaces:**
- Consumes: telemetry/events already parsed in `backend/main.py`.
- Produces: `ai_reconstruction` in the analysis JSON by calling `build_ai_reconstruction(facts)`.

- [ ] **Step 1: Write failing integration tests for fact extraction**

Create tests that exercise a focused helper rather than a whole binary TLOG parse. Add this public helper to the intended interface:

```python
build_ai_reconstruction_facts(
    *,
    radio_loss_episodes,
    mode_transitions,
    altitude_samples,
    vtx_events,
    home_distance_samples,
    ended_armed,
    power_metrics,
) -> dict
```

Test fixture:

```python
import unittest
from backend.main import build_ai_reconstruction_facts


class AIReconstructionIntegrationTest(unittest.TestCase):
    def test_extracts_stable_altitude_and_short_rtl_land(self):
        facts = build_ai_reconstruction_facts(
            radio_loss_episodes=[{"time_s": 180.0, "dbm": -128, "recovered": False}],
            mode_transitions=[
                {"from": "RTL", "to": "LAND", "time_s": 201.1, "delta_s": 0.7}
            ],
            altitude_samples=[
                {"time_s": 176.0, "altitude_m": 69.2},
                {"time_s": 180.0, "altitude_m": 69.8},
                {"time_s": 184.0, "altitude_m": 71.0},
            ],
            vtx_events=[],
            home_distance_samples=[{"time_s": 201.1, "distance_m": 1360.0}],
            ended_armed=True,
            power_metrics={},
        )
        ep = facts["critical_radio_episode"]
        self.assertAlmostEqual(ep["altitude_m"], 69.8, places=1)
        self.assertLessEqual(ep["altitude_window_max_m"] - ep["altitude_window_min_m"], 5.0)
        self.assertFalse(ep["vtx_changed"])
        self.assertEqual(facts["land_distance_home_m"], 1360.0)
```

- [ ] **Step 2: Run integration test and verify RED**

Run:

```bash
python -m unittest tests.test_ai_reconstruction_integration -v
```

Expected: FAIL because `build_ai_reconstruction_facts` is missing.

- [ ] **Step 3: Add fact extraction helper and wire existing parser data into it**

Implementation rules:

```python
AI_REACTION_WINDOW_S = 10.0
```

For the last critical radio-loss episode:
- choose the altitude sample nearest in time as `altitude_m`;
- collect altitude samples in `[episode_time - 5 s, episode_time + 10 s]` to compute min/max;
- set `vtx_changed=True` only if a recorded VTX/channel event occurs in `[episode_time, episode_time + 10 s]`;
- for a `LAND` transition, use the nearest home-distance sample to compute `land_distance_home_m`;
- pass through existing propulsion/power metrics without changing how they are calculated.

Add near the final response assembly in `backend/main.py`:

```python
from backend.ai_reconstruction import build_ai_reconstruction

facts = build_ai_reconstruction_facts(...)
result["ai_reconstruction"] = build_ai_reconstruction(facts)
```

Use existing parsed structures where present; do not reparse the TLOG and do not derive facts by matching already-rendered Ukrainian alert strings when structured values exist.

- [ ] **Step 4: Run integration + core tests**

Run:

```bash
python -m unittest tests.test_ai_reconstruction tests.test_ai_reconstruction_integration -v
```

Expected: PASS.

- [ ] **Step 5: Run backend syntax check**

```bash
python -m py_compile backend/main.py backend/ai_reconstruction.py
```

Expected: no output, exit code 0.

- [ ] **Step 6: Commit backend integration**

```bash
git add backend/main.py backend/ai_reconstruction.py tests/test_ai_reconstruction_integration.py
git commit -m "feat: feed telemetry facts into AI reconstruction"
```

---

### Task 3: Render the AI reconstruction block below the existing findings

**Files:**
- Modify: `index.html`
- Create: `tests/test_ai_reconstruction_frontend_contract.py`

**Interfaces:**
- Consumes: `result.ai_reconstruction` from backend JSON.
- Produces: visible block `🤖 AI ВИСНОВОК` immediately below the existing detailed findings; no changes to the existing findings content/order.

- [ ] **Step 1: Write failing frontend contract test**

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class AIReconstructionFrontendContractTest(unittest.TestCase):
    def test_ai_reconstruction_block_exists_below_existing_findings(self):
        self.assertIn("AI_RECONSTRUCTION_V1", INDEX)
        self.assertIn("🤖 AI ВИСНОВОК", INDEX)
        self.assertIn("Що сталося", INDEX)
        self.assertIn("Ймовірна послідовність", INDEX)
        self.assertIn("Дії, зафіксовані в TLOG", INDEX)
        self.assertIn("Що могло допомогти", INDEX)
        self.assertIn("Впевненість аналізу", INDEX)
        self.assertIn("ai_reconstruction", INDEX)
```

- [ ] **Step 2: Run test and verify RED**

```bash
python -m unittest tests.test_ai_reconstruction_frontend_contract -v
```

Expected: FAIL because the block marker is absent.

- [ ] **Step 3: Add minimal HTML/CSS/JS renderer**

Add one new block directly after the existing findings container, not before it and not inside the list:

```html
<!-- AI_RECONSTRUCTION_V1 -->
<section id="aiReconstructionBlock" class="ai-reconstruction" hidden>
  <h3>🤖 AI ВИСНОВОК</h3>
  <div id="aiReconWhat"></div>
  <div id="aiReconSequence"></div>
  <div id="aiReconActions"></div>
  <div id="aiReconAlternatives"></div>
  <div id="aiReconConfidence"></div>
</section>
```

Add a renderer that escapes text through DOM APIs and creates lists from arrays:

```javascript
function renderAiReconstruction(recon){
  const block = document.getElementById('aiReconstructionBlock');
  if(!block || !recon){
    if(block) block.hidden = true;
    return;
  }

  const sections = [
    ['aiReconWhat', 'Що сталося', recon.what_happened || []],
    ['aiReconSequence', 'Ймовірна послідовність', recon.likely_sequence || []],
    ['aiReconActions', 'Дії, зафіксовані в TLOG', recon.pilot_actions || []],
    ['aiReconAlternatives', 'Що могло допомогти', recon.possible_alternatives || []],
  ];

  sections.forEach(([id, title, items]) => {
    const host = document.getElementById(id);
    host.replaceChildren();
    if(!items.length) return;
    const h = document.createElement('div');
    h.className = 'ai-recon-section-title';
    h.textContent = title;
    const ul = document.createElement('ul');
    items.forEach(text => {
      const li = document.createElement('li');
      li.textContent = text;
      ul.appendChild(li);
    });
    host.append(h, ul);
  });

  const confidence = document.getElementById('aiReconConfidence');
  confidence.textContent = `Впевненість аналізу: ${recon.confidence || 'Низька'}`;
  block.hidden = false;
}
```

At the end of the existing `renderResults(result)` flow, after the current detailed findings have been rendered, call:

```javascript
renderAiReconstruction(result.ai_reconstruction || null);
```

Keep styling visually distinct but compact; use existing CSS variables and do not change theme or timeline styles.

- [ ] **Step 4: Run frontend contract test**

```bash
python -m unittest tests.test_ai_reconstruction_frontend_contract -v
```

Expected: PASS.

- [ ] **Step 5: Run inline JavaScript syntax validation used by the repo**

Use the repository’s existing inline-JS syntax validation command/workflow. If no standalone helper is available, extract inline `<script>` contents in the same manner as the existing CI workflow and run `node --check` on the generated file.

Expected: PASS.

- [ ] **Step 6: Commit frontend rendering**

```bash
git add index.html tests/test_ai_reconstruction_frontend_contract.py
git commit -m "feat: render AI reconstruction below findings"
```

---

### Task 4: Protect existing findings and wording behavior with regression tests

**Files:**
- Modify: `tests/test_ai_reconstruction.py`
- Modify: `tests/test_ai_reconstruction_integration.py`
- Modify: `tests/test_ai_reconstruction_frontend_contract.py`
- If an existing findings contract test exists, modify that existing file instead of duplicating its coverage.

**Interfaces:**
- Consumes: current analyzer response and HTML ordering.
- Produces: regression guarantees that the old findings remain and the new narrative stays evidence-based.

- [ ] **Step 1: Add wording guard tests**

Add assertions that generated output never contains categorical phrases:

```python
FORBIDDEN = [
    "помилка пілота",
    "пілот винен",
    "точна причина",
    "потрібно було",
]

text = " ".join(
    result["what_happened"]
    + result["likely_sequence"]
    + result["pilot_actions"]
    + result["possible_alternatives"]
).lower()
for phrase in FORBIDDEN:
    self.assertNotIn(phrase, text)
```

- [ ] **Step 2: Add ordering guard for old findings before AI block**

In the frontend contract, locate the existing findings list/container marker already used by the current UI and assert its position is before `AI_RECONSTRUCTION_V1`:

```python
self.assertLess(INDEX.index(EXISTING_FINDINGS_MARKER), INDEX.index("AI_RECONSTRUCTION_V1"))
```

Use the real existing marker/id from `index.html`; do not introduce a synthetic duplicate marker solely for the test.

- [ ] **Step 3: Add a repeated-loss test that includes exact `-128 dBm` evidence**

The output should mention the measured value when the fact is available:

```python
self.assertTrue(any("-128" in item for item in result["evidence"] + result["what_happened"]))
```

If Task 1’s minimal implementation does not yet include dBm in evidence, extend only the evidence text; do not change scenario scoring.

- [ ] **Step 4: Add a real-log-derived fixture only if already present in repository test assets**

Search existing tests/fixtures for a representative TLOG-derived JSON fixture. If present, add one assertion that the reconstruction runs against it. If no such fixture exists, do not add a binary TLOG to the repository in this task; synthetic structured fixtures remain the canonical unit coverage.

- [ ] **Step 5: Run the full AI reconstruction test set**

```bash
python -m unittest \
  tests.test_ai_reconstruction \
  tests.test_ai_reconstruction_integration \
  tests.test_ai_reconstruction_frontend_contract -v
```

Expected: PASS.

- [ ] **Step 6: Commit regression guards**

```bash
git add tests/test_ai_reconstruction.py tests/test_ai_reconstruction_integration.py tests/test_ai_reconstruction_frontend_contract.py
git commit -m "test: protect AI reconstruction evidence and wording"
```

---

### Task 5: Add CI coverage and run full regression verification

**Files:**
- Create: `.github/workflows/ai-reconstruction-summary.yml`
- Possibly modify: none of the legacy auto-patcher workflows unless they are proven to rewrite the new block.

**Interfaces:**
- Consumes: branch/PR changes.
- Produces: CI signal for backend reconstruction, frontend contract, Python syntax, and JavaScript syntax.

- [ ] **Step 1: Add workflow**

```yaml
name: AI reconstruction summary

on:
  push:
    branches:
      - feature/ai-reconstruction-summary
    paths:
      - backend/main.py
      - backend/ai_reconstruction.py
      - index.html
      - tests/test_ai_reconstruction.py
      - tests/test_ai_reconstruction_integration.py
      - tests/test_ai_reconstruction_frontend_contract.py
      - .github/workflows/ai-reconstruction-summary.yml
  pull_request:
    paths:
      - backend/main.py
      - backend/ai_reconstruction.py
      - index.html
      - tests/test_ai_reconstruction.py
      - tests/test_ai_reconstruction_integration.py
      - tests/test_ai_reconstruction_frontend_contract.py
      - .github/workflows/ai-reconstruction-summary.yml

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: AI reconstruction tests
        run: |
          python -m unittest \
            tests.test_ai_reconstruction \
            tests.test_ai_reconstruction_integration \
            tests.test_ai_reconstruction_frontend_contract -v
      - name: Python syntax
        run: python -m py_compile backend/main.py backend/ai_reconstruction.py
      - name: JavaScript syntax
        run: |
          python - <<'PY'
          from pathlib import Path
          import re
          html = Path('index.html').read_text(encoding='utf-8')
          scripts = re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', html, flags=re.S|re.I)
          Path('/tmp/index-inline.js').write_text('\n'.join(scripts), encoding='utf-8')
          PY
          node --check /tmp/index-inline.js
```

- [ ] **Step 2: Run all relevant local tests**

Run the AI tests plus existing high-value contracts for graph/timeline/findings that already exist in `tests/`:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

If the full suite contains environment-specific tests that cannot run locally, record the exact failing modules and verify the feature-specific suite plus CI instead of suppressing failures.

- [ ] **Step 3: Verify rollback branch remains unchanged**

Run:

```bash
git rev-parse backup-before-ai-reconstruction
```

Expected exactly:

```text
398f355b0e6e5e80a40c1b8f618f190ec8b4cf5b
```

- [ ] **Step 4: Commit CI workflow**

```bash
git add .github/workflows/ai-reconstruction-summary.yml
git commit -m "ci: verify AI reconstruction summary"
```

---

### Task 6: PR review, merge, deployment verification, and first-log validation

**Files:**
- No source files unless review uncovers a defect.

**Interfaces:**
- Consumes: completed feature branch.
- Produces: merged `main` with rollback path preserved and deployed UI.

- [ ] **Step 1: Open PR from `feature/ai-reconstruction-summary` to `main`**

PR description must state:
- existing findings are preserved;
- reconstruction is deterministic, not remote LLM-generated;
- stable-altitude rule uses measured altitude with <=5 m spread;
- short RTL→LAND threshold is <=2.0 s;
- rollback branch is `backup-before-ai-reconstruction` at `398f355...`.

- [ ] **Step 2: Review diff for scope creep**

Reject the PR if it unexpectedly changes:
- graph viewer behavior;
- timeline columns/logic;
- theme behavior;
- current detailed alert text/order;
- rollback branch.

- [ ] **Step 3: Wait for all relevant CI checks and merge only on green**

Expected: new AI reconstruction workflow passes and no required existing regression workflow fails because of the feature.

- [ ] **Step 4: Verify final `main` contains the reconstruction marker and backend field**

Check final main for:

```text
AI_RECONSTRUCTION_V1
ai_reconstruction
```

- [ ] **Step 5: Verify GitHub Pages deployment for the final main SHA succeeds**

Do not claim deployment success before the Pages workflow reports `completed/success` for the merged main SHA.

- [ ] **Step 6: Re-analyze the discussed TLOG and validate the narrative**

Expected behavior for that log, based only on actual telemetry:
- repeated `-128 dBm` episodes are reflected;
- the actual altitude near the critical episode is printed (roughly 70 m only if telemetry says so);
- no pronounced climb is stated only when altitude spread is <=5 m in the reaction window;
- missing VTX/channel change is stated only if none was recorded;
- short RTL→LAND transition is stated with the actual delta;
- LAND distance from HOME is printed if available;
- the conclusion uses probabilistic language;
- all existing technical findings remain above it.

- [ ] **Step 7: If behavior is wrong, do not patch production blindly**

First reproduce the wrong inference with a failing fixture test, fix the rule on the feature/fix branch, rerun tests, then merge. If the whole feature must be removed quickly, restore production from `backup-before-ai-reconstruction` rather than manually deleting pieces.
