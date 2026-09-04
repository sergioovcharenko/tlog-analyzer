# Graph + Attitude Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate interactive telemetry graph viewer with selectable metrics and a synchronized artificial horizon to the existing TLOG Analyzer without breaking the current analysis flow.

**Architecture:** Extend the backend response with a compact `graph_data` payload built from parsed MAVLink/TLOG messages, then add a self-contained viewer module inside the existing `index.html`. The viewer opens from a new `📈 Переглянути графік` button, renders one metric at a time against elapsed time, and updates a custom attitude indicator using the nearest roll/pitch sample to the selected graph time.

**Tech Stack:** Python/FastAPI backend, pymavlink data already parsed by the project, static HTML/CSS/vanilla JavaScript frontend, existing GitHub Pages deployment, focused Python contract tests, Node syntax check for embedded JavaScript.

**Spec:** `docs/superpowers/specs/2026-09-04-graph-attitude-viewer-design.md`

## Global Constraints

- Stable rollback baseline: `b9953d0febe233580428c19cc2eb0f9bac7a1b04`.
- Create backup branch `backup-before-graph-attitude-viewer` from the stable baseline before implementation.
- Keep the existing main analysis view and existing result rendering behavior unchanged.
- Phase 1 supports one selected metric at a time.
- Do not copy UAVLogViewer Vue components or source code.
- Do not add Vue or another frontend framework solely for this feature.
- Missing telemetry must never crash the viewer.
- Phase 1 does not synchronize the existing map, TX16S sticks, or Timeline.
- Online version first; offline mirroring is deferred until the online feature is stable.

---

### Task 1: Protect the current stable version and define the graph-data contract

**Files:**
- Create branch: `backup-before-graph-attitude-viewer`
- Create: `tests/test_graph_data_contract.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: existing parsed MAVLink message stream inside `backend/main.py`.
- Produces: response field `graph_data: dict[str, list]` with aligned time/value arrays where data exists.
- Required keys when available: `time_ms`, `altitude_m`, `voltage_v`, `current_a`, `groundspeed_ms`, `engine_load_pct`, `radio_dbm`, `roll_deg`, `pitch_deg`, `yaw_deg`.

- [ ] **Step 1: Create the rollback branch**

Create `backup-before-graph-attitude-viewer` from commit `b9953d0febe233580428c19cc2eb0f9bac7a1b04` and verify the branch points to that exact SHA.

- [ ] **Step 2: Write the failing backend contract test**

Create `tests/test_graph_data_contract.py` with tests that import the graph-data helper planned below and assert:

```python
import math

from backend.main import _build_graph_data


def test_build_graph_data_converts_attitude_radians_to_degrees():
    messages = {
        "ATTITUDE": [
            {"time_boot_ms": 1000, "roll": math.pi / 2, "pitch": -math.pi / 4, "yaw": math.pi},
        ]
    }
    graph = _build_graph_data(messages)
    assert graph["attitude_time_ms"] == [1000]
    assert graph["roll_deg"] == [90.0]
    assert graph["pitch_deg"] == [-45.0]
    assert graph["yaw_deg"] == [180.0]


def test_build_graph_data_omits_missing_metric_series():
    graph = _build_graph_data({"ATTITUDE": []})
    assert "voltage_v" not in graph
    assert "current_a" not in graph


def test_build_graph_data_filters_non_finite_values():
    messages = {
        "ATTITUDE": [
            {"time_boot_ms": 1000, "roll": float("nan"), "pitch": 0.0, "yaw": 0.0},
            {"time_boot_ms": 2000, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
        ]
    }
    graph = _build_graph_data(messages)
    assert graph["attitude_time_ms"] == [2000]
    assert graph["roll_deg"] == [0.0]
```

- [ ] **Step 3: Run the test and verify RED**

Run:

```bash
python -m unittest tests.test_graph_data_contract -v
```

Expected: FAIL because `_build_graph_data` does not yet exist.

- [ ] **Step 4: Add `_build_graph_data(messages)` to `backend/main.py`**

Implement a focused helper with this contract:

```python
def _build_graph_data(messages: dict) -> dict:
    """Return finite telemetry series for graph playback.

    Each metric owns its own time array when sampling rates differ.
    ATTITUDE values are converted from radians to degrees.
    Missing series are omitted.
    """
```

Use per-series time arrays to avoid invalid assumptions about equal sampling rates. Use these names:

```python
{
    "altitude_time_ms": [], "altitude_m": [],
    "voltage_time_ms": [], "voltage_v": [],
    "current_time_ms": [], "current_a": [],
    "groundspeed_time_ms": [], "groundspeed_ms": [],
    "engine_load_time_ms": [], "engine_load_pct": [],
    "radio_time_ms": [], "radio_dbm": [],
    "attitude_time_ms": [], "roll_deg": [], "pitch_deg": [], "yaw_deg": []
}
```

Only include a pair when at least one valid sample exists. Reuse existing parser values where already available; do not duplicate parsing logic unnecessarily.

- [ ] **Step 5: Attach `graph_data` to the normal analysis response**

At the final response assembly point in `backend/main.py`, add:

```python
result["graph_data"] = _build_graph_data(parsed_messages)
```

Use the actual in-scope parsed-message variable from the existing function; do not re-read the TLOG.

- [ ] **Step 6: Run backend tests**

Run:

```bash
python -m unittest tests.test_graph_data_contract -v
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py tests/test_graph_data_contract.py
git commit -m "feat: expose graph telemetry series"
```

---

### Task 2: Add the viewer shell and metric registry without affecting current rendering

**Files:**
- Modify: `index.html`
- Create: `tests/test_graph_viewer_ui_contract.py`

**Interfaces:**
- Consumes: `result.graph_data` from Task 1.
- Produces frontend functions:
  - `openGraphViewer(result)`
  - `closeGraphViewer()`
  - `buildGraphMetricRegistry(graphData)`
  - `setGraphMetric(metricKey)`
- Produces DOM ids:
  - `graphViewerBtn`
  - `graphViewerOverlay`
  - `graphMetricSelect`
  - `graphCanvas`
  - `graphNoData`
  - `attitudePanel`
  - `attitudeHorizon`

- [ ] **Step 1: Write the failing UI contract test**

Create `tests/test_graph_viewer_ui_contract.py`:

```python
from pathlib import Path
import unittest


class GraphViewerUIContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("index.html").read_text(encoding="utf-8")

    def test_graph_viewer_entry_points_exist(self):
        self.assertIn('id="graphViewerBtn"', self.html)
        self.assertIn('id="graphViewerOverlay"', self.html)
        self.assertIn('id="graphMetricSelect"', self.html)
        self.assertIn('id="graphCanvas"', self.html)
        self.assertIn('id="attitudeHorizon"', self.html)

    def test_graph_viewer_functions_exist(self):
        self.assertIn("function openGraphViewer", self.html)
        self.assertIn("function closeGraphViewer", self.html)
        self.assertIn("function buildGraphMetricRegistry", self.html)
        self.assertIn("function setGraphMetric", self.html)

    def test_graph_viewer_does_not_reanalyze_tlog(self):
        marker = "function openGraphViewer"
        start = self.html.index(marker)
        block = self.html[start:start + 5000]
        self.assertNotIn("analyzeOnServer(", block)
```

- [ ] **Step 2: Run the test and verify RED**

```bash
python -m unittest tests.test_graph_viewer_ui_contract -v
```

Expected: FAIL because the new viewer DOM/functions are absent.

- [ ] **Step 3: Add the viewer button**

Add a hidden/disabled-by-default button near the existing post-analysis controls:

```html
<button id="graphViewerBtn" type="button" hidden>📈 Переглянути графік</button>
```

After a successful `renderResults(result)`, reveal it only when `result.graph_data` exists and contains at least one plottable metric.

- [ ] **Step 4: Add the fullscreen-style overlay markup**

Add a self-contained overlay with:

```html
<section id="graphViewerOverlay" hidden aria-hidden="true">
  <div class="graph-viewer-toolbar">
    <button id="graphViewerClose" type="button">← Назад до аналізу</button>
    <label for="graphMetricSelect">Показник</label>
    <select id="graphMetricSelect"></select>
  </div>
  <div class="graph-viewer-layout">
    <div class="graph-viewer-chart-wrap">
      <canvas id="graphCanvas"></canvas>
      <div id="graphNoData" hidden>Немає даних у цьому TLOG</div>
    </div>
    <aside id="attitudePanel">
      <div id="attitudeHorizon" aria-label="Авіагоризонт"></div>
      <div id="attitudeValues"></div>
    </aside>
  </div>
</section>
```

Keep it inside the existing page so closing it returns immediately to the current results.

- [ ] **Step 5: Add responsive CSS**

Desktop: graph left, attitude right. Mobile: one-column layout with graph first and attitude below. No page-level horizontal overflow. Use project dark-theme tokens/colors rather than introducing an unrelated visual style.

- [ ] **Step 6: Add the metric registry**

Implement:

```javascript
function buildGraphMetricRegistry(graphData) {
  const defs = [
    {key:'altitude', label:'Висота', unit:'m', timeKey:'altitude_time_ms', valueKey:'altitude_m'},
    {key:'voltage', label:'Напруга', unit:'V', timeKey:'voltage_time_ms', valueKey:'voltage_v'},
    {key:'current', label:'Струм', unit:'A', timeKey:'current_time_ms', valueKey:'current_a'},
    {key:'groundspeed', label:'Швидкість', unit:'m/s', timeKey:'groundspeed_time_ms', valueKey:'groundspeed_ms'},
    {key:'engine_load', label:'Engine Load', unit:'%', timeKey:'engine_load_time_ms', valueKey:'engine_load_pct'},
    {key:'radio_dbm', label:'Радіосигнал', unit:'dBm', timeKey:'radio_time_ms', valueKey:'radio_dbm'},
    {key:'roll', label:'Roll', unit:'°', timeKey:'attitude_time_ms', valueKey:'roll_deg'},
    {key:'pitch', label:'Pitch', unit:'°', timeKey:'attitude_time_ms', valueKey:'pitch_deg'},
    {key:'yaw', label:'Yaw', unit:'°', timeKey:'attitude_time_ms', valueKey:'yaw_deg'}
  ];
  return defs.map(d => ({...d, available:Array.isArray(graphData?.[d.timeKey]) && Array.isArray(graphData?.[d.valueKey]) && graphData[d.valueKey].length > 0}));
}
```

Populate the `<select>` from this registry. Disable unavailable options or omit them; if none are available, show `Немає даних у цьому TLOG`.

- [ ] **Step 7: Run UI contract and all existing tests**

```bash
python -m unittest tests.test_graph_viewer_ui_contract -v
python -m unittest discover -s tests -v
```

Expected: PASS, including existing TX16S/Timeline contracts.

- [ ] **Step 8: Commit**

```bash
git add index.html tests/test_graph_viewer_ui_contract.py
git commit -m "feat: add graph viewer shell"
```

---

### Task 3: Implement the interactive graph and time selection

**Files:**
- Modify: `index.html`
- Modify: `tests/test_graph_viewer_ui_contract.py`

**Interfaces:**
- Consumes: metric objects from `buildGraphMetricRegistry(graphData)`.
- Produces:
  - `renderGraphSeries(metric)`
  - `selectGraphTime(timeMs)`
  - `nearestSampleIndex(times, targetMs)`
- Shared state:
  - `graphViewerState.result`
  - `graphViewerState.metricKey`
  - `graphViewerState.selectedTimeMs`

- [ ] **Step 1: Add failing tests for graph functions**

Extend `tests/test_graph_viewer_ui_contract.py`:

```python
    def test_graph_interaction_functions_exist(self):
        self.assertIn("function renderGraphSeries", self.html)
        self.assertIn("function selectGraphTime", self.html)
        self.assertIn("function nearestSampleIndex", self.html)
        self.assertIn("selectedTimeMs", self.html)
```

- [ ] **Step 2: Run the test and verify RED**

```bash
python -m unittest tests.test_graph_viewer_ui_contract -v
```

Expected: FAIL on the new function names.

- [ ] **Step 3: Implement `nearestSampleIndex(times, targetMs)`**

Use a binary search or bounded linear search that returns the index whose timestamp is closest to `targetMs`; return `-1` for an empty array.

Behavior examples:

```javascript
nearestSampleIndex([], 1000) === -1
nearestSampleIndex([1000, 2000, 3000], 2400) === 1
nearestSampleIndex([1000, 2000, 3000], 2700) === 2
```

- [ ] **Step 4: Implement graph rendering with a browser-safe chart layer**

Use the smallest compatible approach already supported by the page. If no chart library is currently loaded, add a single pinned CDN dependency that works on static GitHub Pages and supports line charts, hover, click, and zoom/pan without Vue. Keep the viewer isolated so a library-load failure only affects the graph panel.

`renderGraphSeries(metric)` must:

1. read `timeKey` and `valueKey` from the chosen metric;
2. discard non-finite values defensively;
3. convert milliseconds to elapsed `mm:ss` labels for display while keeping raw `timeMs` for selection;
4. render one line series;
5. show exact time/value on hover;
6. call `selectGraphTime(rawTimeMs)` on click;
7. preserve `graphViewerState.selectedTimeMs` when the metric changes where possible.

- [ ] **Step 5: Add a visible selected-time cursor**

When `selectGraphTime(timeMs)` is called, update the graph with a vertical marker at the selected timestamp and persist that timestamp in `graphViewerState.selectedTimeMs`.

- [ ] **Step 6: Add graceful chart errors**

If the chart library is unavailable or the selected series is empty, show a readable Ukrainian message inside `graphNoData`; do not throw through to the main page.

- [ ] **Step 7: Verify JavaScript syntax**

Extract embedded JavaScript from `index.html` using the same Node syntax-check pattern already used by existing workflows, then run:

```bash
node --check /tmp/tlog-index-script.js
```

Expected: no syntax errors.

- [ ] **Step 8: Run regression tests**

```bash
python -m unittest tests.test_graph_viewer_ui_contract -v
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add index.html tests/test_graph_viewer_ui_contract.py
git commit -m "feat: render selectable telemetry graph"
```

---

### Task 4: Add the synchronized artificial horizon

**Files:**
- Modify: `index.html`
- Modify: `tests/test_graph_viewer_ui_contract.py`

**Interfaces:**
- Consumes: `graph_data.attitude_time_ms`, `roll_deg`, `pitch_deg`, `yaw_deg`; selected time from `graphViewerState.selectedTimeMs`.
- Produces:
  - `updateAttitudeAtTime(timeMs)`
  - `renderAttitude(rollDeg, pitchDeg, yawDeg, altitudeM)`

- [ ] **Step 1: Add failing attitude contract tests**

Extend the UI contract with:

```python
    def test_attitude_functions_exist(self):
        self.assertIn("function updateAttitudeAtTime", self.html)
        self.assertIn("function renderAttitude", self.html)
        self.assertIn("Немає ATTITUDE у цьому TLOG", self.html)
```

- [ ] **Step 2: Run the test and verify RED**

```bash
python -m unittest tests.test_graph_viewer_ui_contract -v
```

Expected: FAIL.

- [ ] **Step 3: Build the artificial-horizon markup/CSS**

Inside `attitudeHorizon`, create independent project-owned elements for:

- sky half;
- ground half;
- horizon line;
- pitch ladder marks;
- fixed aircraft reference wings;
- roll scale / pointer.

Implement motion using CSS transforms:

- rotate the moving horizon layer by `-rollDeg`;
- translate the moving horizon vertically from `pitchDeg` using a clamped pixels-per-degree scale;
- keep aircraft reference wings fixed.

No copied UAVLogViewer/Vue code.

- [ ] **Step 4: Implement `updateAttitudeAtTime(timeMs)`**

Use `nearestSampleIndex(graphData.attitude_time_ms, timeMs)` to choose the closest attitude sample. If no sample exists, show `Немає ATTITUDE у цьому TLOG` and keep the graph operational.

- [ ] **Step 5: Implement `renderAttitude(...)`**

Update both the visual horizon and numeric readout:

```text
Roll: -12.4°
Pitch: +3.8°
Yaw: 217.0°
Altitude: 154.6 m
```

For altitude at the selected time, use `nearestSampleIndex(graphData.altitude_time_ms, timeMs)` independently because altitude and attitude sampling rates can differ.

- [ ] **Step 6: Wire graph selection to attitude playback**

At the end of `selectGraphTime(timeMs)`, call:

```javascript
updateAttitudeAtTime(timeMs);
```

Opening the viewer should select the first available timestamp and initialize the horizon immediately.

- [ ] **Step 7: Run tests and syntax checks**

```bash
python -m unittest tests.test_graph_viewer_ui_contract -v
python -m unittest discover -s tests -v
node --check /tmp/tlog-index-script.js
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add index.html tests/test_graph_viewer_ui_contract.py
git commit -m "feat: sync artificial horizon with graph time"
```

---

### Task 5: Integration verification and deployment safety

**Files:**
- Modify only if needed after test failures: `index.html`, `backend/main.py`, focused tests from prior tasks.
- Optional create: `.github/workflows/graph-attitude-contract.yml` if no existing workflow covers the new tests.

**Interfaces:**
- Consumes all interfaces from Tasks 1–4.
- Produces a deployable phase-1 feature that can be reverted independently.

- [ ] **Step 1: Add CI coverage if existing workflows do not discover the new tests**

Create `.github/workflows/graph-attitude-contract.yml` with checkout, Python setup, and:

```bash
python -m unittest tests.test_graph_data_contract -v
python -m unittest tests.test_graph_viewer_ui_contract -v
python -m unittest discover -s tests -v
```

Also run the existing embedded-JS `node --check` extraction used by current frontend workflows.

- [ ] **Step 2: Run the complete local/CI test suite**

Required green checks:

```bash
python -m unittest tests.test_graph_data_contract -v
python -m unittest tests.test_graph_viewer_ui_contract -v
python -m unittest discover -s tests -v
node --check /tmp/tlog-index-script.js
```

- [ ] **Step 3: Manual verification with a TLOG containing ATTITUDE**

Verify:

1. normal analysis still completes;
2. `📈 Переглянути графік` appears after analysis;
3. Altitude/Voltage/Current/Engine Load options appear when present;
4. changing metric redraws without re-uploading the log;
5. clicking the graph moves the selected-time cursor;
6. roll/pitch horizon changes at the same selected time;
7. close returns to the exact existing analysis results.

- [ ] **Step 4: Manual verification with partial telemetry**

Use a TLOG missing at least one target metric or ATTITUDE and verify:

- missing metrics are disabled/omitted;
- graph viewer still opens for available metrics;
- missing attitude displays `Немає ATTITUDE у цьому TLOG`;
- no uncaught error breaks the main analyzer.

- [ ] **Step 5: Confirm rollback path before release**

Verify branch `backup-before-graph-attitude-viewer` still points at `b9953d0febe233580428c19cc2eb0f9bac7a1b04` and document the recovery action:

```bash
git checkout main
git reset --hard backup-before-graph-attitude-viewer
git push --force-with-lease origin main
```

Use this only if the user explicitly chooses full rollback; otherwise revert only the feature commits.

- [ ] **Step 6: Final commit if CI/workflow file was added**

```bash
git add .github/workflows/graph-attitude-contract.yml
git commit -m "ci: verify graph attitude viewer"
```

- [ ] **Step 7: Verify GitHub Pages deployment**

After the final production commit reaches `main`, wait for the Pages workflow associated with that SHA and require `conclusion: success` before calling the feature deployed.
