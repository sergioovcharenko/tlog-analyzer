# Dynamic MAVLink Plot Viewer + Board Messages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dynamic MAVLink field browser with checkbox-driven multi-series plotting and a time-synchronized `ПОВІДОМЛЕННЯ БОРТА` panel inside the existing TLOG graph/attitude viewer.

**Architecture:** Add a focused backend collector that observes every decoded MAVLink packet, extracts finite numeric scalar fields, assigns elapsed `time_ms`, conservatively infers units, and downsamples chart-only series. Keep existing `graph_data`, diagnostics, Timeline, TX16S, and attitude logic intact. The frontend receives `mavlink_plot` plus `board_messages`, renders searchable/collapsible MAVLink groups below the graph, draws selected series with deterministic colors and unit-aware Y-axis groups, and filters board messages around the same selected graph time.

**Tech Stack:** Python 3.12, FastAPI, pymavlink, plain HTML/CSS/JavaScript canvas UI, Python `unittest`, Node `--check`, GitHub Actions, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-09-05-dynamic-mavlink-plot-and-board-messages-design.md`

## Global Constraints

- Preserve the existing graph viewer, artificial horizon, flight-mode badge, right-side telemetry cards, Timeline, TX16S, map behavior, and analyzer calculations.
- Dynamic field catalog must come from MAVLink messages actually present in the uploaded TLOG; do not use a fixed allowlist as the source of truth.
- Plot only finite numeric scalar values; skip strings, bytes, non-numeric arrays, nested payloads, NaN, and Inf.
- Use the same elapsed-time basis as the existing graph viewer.
- Downsampling is chart-only and deterministic; it must not alter analysis or Timeline values.
- Unknown units remain neutral rather than guessed.
- Board messages use a bounded approximately ±5 second window around selected graph time.
- Do not copy ArduPilot Plot/UAVLogViewer source code directly.
- Keep a rollback branch/reference before implementation.

---

### Task 1: Preserve a rollback point and add backend collector contracts

**Files:**
- Create: `tests/test_dynamic_mavlink_plot_backend.py`
- Create: `backend/mavlink_plot.py`
- Modify later in Task 2: `backend/main.py`

**Interfaces:**
- Produces: `MavlinkPlotCollector(max_points_per_series: int = 1200)`
- Produces: `MavlinkPlotCollector.add(message_type: str, fields: dict, timestamp: float) -> None`
- Produces: `MavlinkPlotCollector.build(base_timestamp: float) -> dict`
- Produces: `build_board_messages(timeline_rows: list[dict], base_timestamp: float) -> list[dict]`

- [ ] **Step 1: Create rollback reference**

Create a branch from the current stable `main` named `backup-before-dynamic-mavlink-plot`.

- [ ] **Step 2: Write failing collector tests**

Create `tests/test_dynamic_mavlink_plot_backend.py` with tests equivalent to:

```python
import math
import unittest
from backend.mavlink_plot import MavlinkPlotCollector, build_board_messages

class DynamicMavlinkPlotBackendTest(unittest.TestCase):
    def test_collects_numeric_scalars_and_skips_non_numeric_payloads(self):
        c = MavlinkPlotCollector(max_points_per_series=10)
        c.add("ATTITUDE", {"roll": 0.25, "pitch": -0.1, "name": "x", "payload": [1, 2]}, 101.0)
        out = c.build(100.0)
        self.assertIn("ATTITUDE", out["groups"])
        self.assertIn("roll", out["groups"]["ATTITUDE"])
        self.assertNotIn("name", out["groups"]["ATTITUDE"])
        self.assertNotIn("payload", out["groups"]["ATTITUDE"])
        self.assertEqual(out["groups"]["ATTITUDE"]["roll"]["time_ms"], [1000])

    def test_rejects_nan_and_inf(self):
        c = MavlinkPlotCollector()
        c.add("TEST", {"a": math.nan, "b": math.inf, "c": 4.0}, 1.0)
        out = c.build(0.0)
        self.assertEqual(set(out["groups"]["TEST"]), {"c"})

    def test_downsampling_caps_points_and_preserves_endpoints(self):
        c = MavlinkPlotCollector(max_points_per_series=5)
        for i in range(20):
            c.add("VFR_HUD", {"alt": float(i)}, float(i))
        s = c.build(0.0)["groups"]["VFR_HUD"]["alt"]
        self.assertLessEqual(len(s["values"]), 5)
        self.assertEqual(s["values"][0], 0.0)
        self.assertEqual(s["values"][-1], 19.0)

    def test_board_messages_use_elapsed_time_and_severity(self):
        rows = [
            {"timestamp": 102.0, "eventType": "SYSTEM", "system_text": "EKF variance", "severity": 3},
            {"timestamp": 108.0, "eventType": "SYSTEM", "system_text": "GPS OK", "severity": 6},
        ]
        msgs = build_board_messages(rows, 100.0)
        self.assertEqual(msgs[0]["time_ms"], 2000)
        self.assertEqual(msgs[0]["level"], "error")
        self.assertEqual(msgs[1]["level"], "info")
```

- [ ] **Step 3: Run the test and verify RED**

Run:

```bash
python -m unittest tests.test_dynamic_mavlink_plot_backend -v
```

Expected: FAIL because `backend.mavlink_plot` does not exist yet.

- [ ] **Step 4: Implement the focused collector**

Create `backend/mavlink_plot.py` with:

```python
import math

TRANSPORT_FIELDS = {"mavpackettype", "_timestamp"}
ANGLE_FIELDS = {("ATTITUDE", "roll"), ("ATTITUDE", "pitch"), ("ATTITUDE", "yaw")}


def _finite_scalar(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _downsample(times, values, limit):
    if len(values) <= limit:
        return list(times), list(values)
    if limit <= 2:
        return [times[0], times[-1]], [values[0], values[-1]]
    step = (len(values) - 1) / (limit - 1)
    idx = sorted({0, len(values) - 1, *[round(i * step) for i in range(1, limit - 1)]})
    return [times[i] for i in idx], [values[i] for i in idx]


def infer_unit(message_type, field):
    key = (message_type, field)
    if key in ANGLE_FIELDS:
        return "deg"
    f = field.lower()
    if f in {"voltage_battery", "voltages"} or "voltage" in f:
        return "native"
    if "current" in f:
        return "native"
    if f in {"throttle", "battery_remaining", "load"} or f.endswith("_pct"):
        return "%"
    if "temp" in f:
        return "native"
    if "rpm" in f:
        return "rpm"
    return ""


class MavlinkPlotCollector:
    def __init__(self, max_points_per_series=1200):
        self.max_points_per_series = max(2, int(max_points_per_series))
        self._series = {}

    def add(self, message_type, fields, timestamp):
        if not isinstance(fields, dict) or not _finite_scalar(timestamp):
            return
        msg = str(message_type or "UNKNOWN")
        for field, raw in fields.items():
            if field in TRANSPORT_FIELDS or not _finite_scalar(raw):
                continue
            value = float(raw)
            if (msg, field) in ANGLE_FIELDS:
                value = math.degrees(value)
            bucket = self._series.setdefault((msg, str(field)), {"timestamps": [], "values": []})
            bucket["timestamps"].append(float(timestamp))
            bucket["values"].append(value)

    def build(self, base_timestamp):
        base = float(base_timestamp or 0.0)
        groups = {}
        for (msg, field), bucket in sorted(self._series.items()):
            times = [int(round((ts - base) * 1000.0)) for ts in bucket["timestamps"]]
            times, values = _downsample(times, bucket["values"], self.max_points_per_series)
            groups.setdefault(msg, {})[field] = {
                "id": f"{msg}.{field}",
                "label": f"{msg}.{field}",
                "unit": infer_unit(msg, field),
                "time_ms": times,
                "values": values,
            }
        return {"groups": groups}


def _severity_level(severity):
    try:
        s = int(severity)
    except (TypeError, ValueError):
        return "info"
    if s <= 3:
        return "error"
    if s <= 4:
        return "warning"
    if s <= 6:
        return "info"
    return "recovery"


def build_board_messages(timeline_rows, base_timestamp):
    base = float(base_timestamp or 0.0)
    out = []
    for row in timeline_rows or []:
        if not isinstance(row, dict):
            continue
        text = str(row.get("system_text") or row.get("analysis_text") or "").strip()
        ts = row.get("timestamp")
        if not text or not _finite_scalar(ts):
            continue
        out.append({
            "time_ms": int(round((float(ts) - base) * 1000.0)),
            "level": _severity_level(row.get("severity")),
            "text": text,
            "event_type": str(row.get("eventType") or "SYSTEM"),
        })
    return sorted(out, key=lambda item: item["time_ms"])
```

- [ ] **Step 5: Run backend tests and verify GREEN**

```bash
python -m unittest tests.test_dynamic_mavlink_plot_backend -v
python -m py_compile backend/mavlink_plot.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/mavlink_plot.py tests/test_dynamic_mavlink_plot_backend.py
git commit -m "feat: add dynamic MAVLink plot collector"
```

---

### Task 2: Feed every decoded MAVLink packet into the collector and return `mavlink_plot`

**Files:**
- Modify: `backend/main.py`
- Test: `tests/test_dynamic_mavlink_plot_backend.py`

**Interfaces:**
- Consumes: `MavlinkPlotCollector`, `build_board_messages`
- Produces in API result: `mavlink_plot: {groups: ...}`
- Produces in API result: `board_messages: list[{time_ms, level, text, event_type}]`

- [ ] **Step 1: Add a failing integration contract**

Extend the backend test to assert `backend/main.py` imports and emits both structures:

```python
from pathlib import Path

main_text = Path("backend/main.py").read_text(encoding="utf-8")
self.assertIn("MavlinkPlotCollector", main_text)
self.assertIn('"mavlink_plot"', main_text)
self.assertIn('"board_messages"', main_text)
```

- [ ] **Step 2: Run and verify RED**

```bash
python -m unittest tests.test_dynamic_mavlink_plot_backend -v
```

- [ ] **Step 3: Integrate collector into the parse loop**

In `backend/main.py`:

```python
from backend.mavlink_plot import MavlinkPlotCollector, build_board_messages
```

Before the read loop:

```python
mavlink_plot_collector = MavlinkPlotCollector(max_points_per_series=1200)
```

Change the packet read so the dynamic collector can see all MAVLink message types:

```python
msg = mav.recv_match(blocking=False)
```

Immediately after `msg_type` and packet timestamp are available:

```python
try:
    mavlink_plot_collector.add(msg_type, msg.to_dict(), timestamp)
except Exception:
    pass
```

Do not add new analysis branches for unknown message types; existing specialized `if/elif` handling remains unchanged.

When building the final response, using the same base timestamp already supplied to `_build_graph_data(...)`, add:

```python
"mavlink_plot": mavlink_plot_collector.build(base_timestamp),
"board_messages": build_board_messages(raw_timeline, base_timestamp),
```

Preserve current `graph_data` unchanged.

- [ ] **Step 4: Verify syntax and backend contracts**

```bash
python -m unittest tests.test_dynamic_mavlink_plot_backend -v
python -m py_compile backend/main.py backend/mavlink_plot.py
```

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_dynamic_mavlink_plot_backend.py
git commit -m "feat: expose dynamic MAVLink plot data"
```

---

### Task 3: Add the searchable MAVLink checkbox browser below the graph

**Files:**
- Modify: `index.html`
- Create: `tests/test_dynamic_mavlink_plot_ui.py`
- Create: `tools/apply_dynamic_mavlink_plot.py`

**Interfaces:**
- Consumes: `graphViewerState.result.mavlink_plot.groups`
- Produces DOM ids: `mavlinkPlotPanel`, `mavlinkPlotSearch`, `mavlinkPlotGroups`, `mavlinkPlotClear`
- Produces JS functions: `buildDynamicMavlinkCatalog()`, `renderMavlinkFieldBrowser()`, `setMavlinkSeriesSelected(id, checked)`

- [ ] **Step 1: Write failing UI contract**

Create `tests/test_dynamic_mavlink_plot_ui.py`:

```python
from pathlib import Path
import unittest

HTML = Path("index.html").read_text(encoding="utf-8")

class DynamicMavlinkPlotUiTest(unittest.TestCase):
    def test_field_browser_exists(self):
        for marker in (
            'id="mavlinkPlotPanel"',
            'id="mavlinkPlotSearch"',
            'id="mavlinkPlotGroups"',
            'id="mavlinkPlotClear"',
            'function buildDynamicMavlinkCatalog()',
            'function renderMavlinkFieldBrowser()',
            'function setMavlinkSeriesSelected(id,checked)',
        ):
            self.assertIn(marker, HTML)
```

- [ ] **Step 2: Run and verify RED**

```bash
python -m unittest tests.test_dynamic_mavlink_plot_ui -v
```

- [ ] **Step 3: Add panel markup below `.graph-viewer-chart-wrap`**

Add:

```html
<section id="mavlinkPlotPanel">
  <div class="mavlink-plot-head">
    <b>MAVLink параметри</b>
    <input id="mavlinkPlotSearch" type="search" placeholder="Пошук: rpm, battery, roll...">
    <button id="mavlinkPlotClear" type="button">Очистити</button>
  </div>
  <div id="mavlinkPlotGroups"></div>
</section>
```

The panel lives under the graph in the horizontal area highlighted by the user.

- [ ] **Step 4: Add catalog/browser state and rendering**

Extend `graphViewerState` with:

```javascript
selectedSeries:new Set(),
seriesColors:new Map(),
```

Add deterministic field flattening:

```javascript
function buildDynamicMavlinkCatalog(){
  const groups=graphViewerState.result?.mavlink_plot?.groups||{};
  const out=[];
  Object.entries(groups).forEach(([message,fields])=>{
    Object.entries(fields||{}).forEach(([field,series])=>{
      out.push({message,field,id:series.id||`${message}.${field}`,label:series.label||`${message}.${field}`,unit:series.unit||'',time_ms:series.time_ms||[],values:series.values||[]});
    });
  });
  return out;
}
```

Render `<details>` per message type, a checkbox per field, unit text, and filter groups/fields using `mavlinkPlotSearch`.

- [ ] **Step 5: Add selection behavior**

```javascript
function setMavlinkSeriesSelected(id,checked){
  if(checked)graphViewerState.selectedSeries.add(id);
  else graphViewerState.selectedSeries.delete(id);
  renderMavlinkFieldBrowser();
  drawGraphViewer();
}
```

`Очистити` clears the set and redraws. Manual checkbox changes set the existing preset selector to `Custom` if that option exists; otherwise leave the current selector untouched until Task 5.

- [ ] **Step 6: Verify UI contract and JS syntax**

```bash
python -m unittest tests.test_dynamic_mavlink_plot_ui -v
node --check /tmp/extracted-inline-script.js
```

Use the existing workflow technique to extract every inline `<script>` block and run `node --check` on each.

- [ ] **Step 7: Commit**

```bash
git add index.html tests/test_dynamic_mavlink_plot_ui.py tools/apply_dynamic_mavlink_plot.py
git commit -m "feat: add dynamic MAVLink field browser"
```

---

### Task 4: Convert the chart from one selected metric to multiple selected series

**Files:**
- Modify: `index.html`
- Test: `tests/test_dynamic_mavlink_plot_ui.py`

**Interfaces:**
- Produces: `getSelectedMavlinkSeries() -> Array<series>`
- Produces: `seriesColor(id) -> CSS color string`
- Produces: `unitAxisGroups(seriesList) -> Map<unit, series[]>`
- Existing `updateAttitudeAtTime(timeMs)` remains the shared time consumer.

- [ ] **Step 1: Add failing multi-series contracts**

```python
for marker in (
    'function getSelectedMavlinkSeries()',
    'function seriesColor(id)',
    'function unitAxisGroups(seriesList)',
    'graphViewerState.selectedSeries',
):
    self.assertIn(marker, HTML)
```

- [ ] **Step 2: Run and verify RED**

```bash
python -m unittest tests.test_dynamic_mavlink_plot_ui -v
```

- [ ] **Step 3: Implement deterministic colors**

Use a fixed palette and stable hash so the same field keeps the same color between redraws:

```javascript
const MAVLINK_SERIES_COLORS=['#38bdf8','#f97316','#22c55e','#e879f9','#facc15','#fb7185','#a78bfa','#2dd4bf','#f8fafc','#60a5fa'];
function seriesColor(id){
  let h=0;for(const ch of String(id))h=((h<<5)-h+ch.charCodeAt(0))|0;
  return MAVLINK_SERIES_COLORS[Math.abs(h)%MAVLINK_SERIES_COLORS.length];
}
```

- [ ] **Step 4: Implement unit-aware axis grouping**

```javascript
function unitAxisGroups(seriesList){
  const m=new Map();
  for(const s of seriesList){
    const key=s.unit||s.id;
    if(!m.has(key))m.set(key,[]);
    m.get(key).push(s);
  }
  return m;
}
```

Cap incompatible axis groups to 4 visible groups. If more than 4 are selected, show a visible warning such as `Забагато різних шкал: показано перші 4` and do not silently normalize unrelated units together.

- [ ] **Step 5: Draw all selected series**

Refactor the canvas drawing path so it loops over selected dynamic series, maps each series to its unit group's min/max, and draws each line with `seriesColor(series.id)`. Keep one shared X/time viewport and one yellow selected-time cursor.

If no dynamic checkbox is selected, preserve the existing single-series `Показник` graph unchanged.

- [ ] **Step 6: Make tooltip multi-series**

At hover/click time, show nearest values for every visible selected series:

```text
03:17.000
ATTITUDE.roll  -2.3 deg
SYS_STATUS.voltage_battery  24100 native
VFR_HUD.throttle  42 %
```

Do not invent a value when a series has no nearby sample.

- [ ] **Step 7: Verify graph, attitude and TX16 regressions**

```bash
python -m unittest tests.test_dynamic_mavlink_plot_ui -v
python -m unittest tests.test_attitude_dashboard_v22_contract -v
python -m unittest tests.test_tx16_ui_contract -v
```

Also run inline JS syntax checking.

- [ ] **Step 8: Commit**

```bash
git add index.html tests/test_dynamic_mavlink_plot_ui.py
git commit -m "feat: plot multiple MAVLink series"
```

---

### Task 5: Add presets that drive dynamic checkbox selection

**Files:**
- Modify: `index.html`
- Test: `tests/test_dynamic_mavlink_plot_ui.py`

**Interfaces:**
- Produces: `applyGraphPreset(name)`
- Presets: `Altitude`, `Power`, `Radio`, `Attitude`, `ESC`, `Custom`

- [ ] **Step 1: Add failing preset contract**

```python
for marker in ('Altitude','Power','Radio','Attitude','ESC','Custom','function applyGraphPreset(name)'):
    self.assertIn(marker, HTML)
```

- [ ] **Step 2: Run and verify RED**

- [ ] **Step 3: Implement best-effort preset matching**

`applyGraphPreset(name)` searches the dynamic catalog for available field IDs; for example:

```javascript
const wanted={
  Altitude:['GLOBAL_POSITION_INT.relative_alt','VFR_HUD.alt','ALTITUDE.altitude_relative'],
  Power:['SYS_STATUS.voltage_battery','SYS_STATUS.current_battery','BATTERY_STATUS.current_battery'],
  Radio:['RADIO_STATUS.rssi','RADIO_STATUS.remrssi','RADIO.rssi'],
  Attitude:['ATTITUDE.roll','ATTITUDE.pitch','ATTITUDE.yaw'],
};
```

This mapping is only a convenience preset. It does not limit the dynamic catalog.

For `ESC`, select every available field whose message type starts with `ESC_` and field contains `rpm`, `current`, `voltage`, or `temperature`.

- [ ] **Step 4: Verify preset behavior and JS syntax**

- [ ] **Step 5: Commit**

```bash
git add index.html tests/test_dynamic_mavlink_plot_ui.py
git commit -m "feat: add MAVLink graph presets"
```

---

### Task 6: Add `ПОВІДОМЛЕННЯ БОРТА` below the attitude dashboard

**Files:**
- Modify: `index.html`
- Create: `tests/test_board_messages_panel.py`

**Interfaces:**
- Consumes: `graphViewerState.result.board_messages`
- Produces DOM: `boardMessagesPanel`, `boardMessagesList`
- Produces: `renderBoardMessagesAtTime(timeMs)`
- Window: ±5000 ms

- [ ] **Step 1: Write failing panel contract**

```python
from pathlib import Path
import unittest
HTML=Path("index.html").read_text(encoding="utf-8")

class BoardMessagesPanelTest(unittest.TestCase):
    def test_panel_and_time_window_exist(self):
        for marker in (
            'id="boardMessagesPanel"',
            'ПОВІДОМЛЕННЯ БОРТА',
            'id="boardMessagesList"',
            'function renderBoardMessagesAtTime(timeMs)',
            'Math.abs(Number(m.time_ms)-timeMs)<=5000',
            'Немає повідомлень',
            'board-msg-error',
            'board-msg-warning',
            'board-msg-info',
            'board-msg-recovery',
        ):
            self.assertIn(marker, HTML)
```

- [ ] **Step 2: Run and verify RED**

```bash
python -m unittest tests.test_board_messages_panel -v
```

- [ ] **Step 3: Add panel markup in the user-highlighted area below telemetry cards**

```html
<section id="boardMessagesPanel">
  <div class="board-messages-title">⚠ ПОВІДОМЛЕННЯ БОРТА</div>
  <div id="boardMessagesList">Немає повідомлень</div>
</section>
```

- [ ] **Step 4: Implement severity styles**

Use four explicit classes:

```css
.board-msg-error{border-left:3px solid #ef4444;color:#fecaca}
.board-msg-warning{border-left:3px solid #f59e0b;color:#fde68a}
.board-msg-info{border-left:3px solid #38bdf8;color:#e0f2fe}
.board-msg-recovery{border-left:3px solid #22c55e;color:#bbf7d0}
```

- [ ] **Step 5: Implement bounded time synchronization**

```javascript
function renderBoardMessagesAtTime(timeMs){
  const box=document.getElementById('boardMessagesList');
  if(!box)return;
  const all=graphViewerState.result?.board_messages||[];
  const rows=all
    .filter(m=>Number.isFinite(Number(m.time_ms))&&Math.abs(Number(m.time_ms)-timeMs)<=5000)
    .sort((a,b)=>Math.abs(Number(a.time_ms)-timeMs)-Math.abs(Number(b.time_ms)-timeMs)||Number(a.time_ms)-Number(b.time_ms))
    .slice(0,12);
  if(!rows.length){box.textContent='Немає повідомлень';return;}
  box.innerHTML=rows.map(m=>`<div class="board-msg board-msg-${m.level||'info'}"><b>${formatGraphTime(Number(m.time_ms))}</b><span>${escapeHtml(String(m.text||''))}</span></div>`).join('');
}
```

Call `renderBoardMessagesAtTime(timeMs)` from `updateAttitudeAtTime(timeMs)` or from the single shared selected-time update function, so graph cursor, attitude, mode, telemetry cards, and board messages always move together.

- [ ] **Step 6: Verify panel and regressions**

```bash
python -m unittest tests.test_board_messages_panel -v
python -m unittest tests.test_attitude_dashboard_v22_contract -v
python -m unittest tests.test_dynamic_mavlink_plot_ui -v
```

Run inline JavaScript syntax check.

- [ ] **Step 7: Commit**

```bash
git add index.html tests/test_board_messages_panel.py
git commit -m "feat: add synchronized board messages panel"
```

---

### Task 7: Add GitHub Actions verification and deploy safely

**Files:**
- Create: `.github/workflows/dynamic-mavlink-viewer.yml`
- Modify if needed: `tools/apply_dynamic_mavlink_plot.py`

**Interfaces:**
- Workflow validates backend collector, frontend contracts, board messages, legacy attitude/TX16 contracts, Python syntax, and every inline JavaScript block.

- [ ] **Step 1: Create workflow**

Use this structure:

```yaml
name: Dynamic MAVLink viewer contract

on:
  push:
    branches: [main]
    paths:
      - 'backend/main.py'
      - 'backend/mavlink_plot.py'
      - 'index.html'
      - 'tests/test_dynamic_mavlink_plot_backend.py'
      - 'tests/test_dynamic_mavlink_plot_ui.py'
      - 'tests/test_board_messages_panel.py'
      - '.github/workflows/dynamic-mavlink-viewer.yml'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python -m unittest tests.test_dynamic_mavlink_plot_backend -v
      - run: python -m unittest tests.test_dynamic_mavlink_plot_ui -v
      - run: python -m unittest tests.test_board_messages_panel -v
      - run: python -m unittest tests.test_attitude_dashboard_v22_contract -v
      - run: python -m unittest tests.test_tx16_ui_contract -v
      - run: python -m py_compile backend/main.py backend/mavlink_plot.py
      - name: Check inline JavaScript syntax
        run: |
          python - <<'PY'
          from pathlib import Path
          import re, subprocess
          s=Path('index.html').read_text(encoding='utf-8')
          for i,b in enumerate(re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',s,re.S|re.I)):
              if not b.strip():
                  continue
              p=Path(f'/tmp/dynamic-mavlink-{i}.js')
              p.write_text(b,encoding='utf-8')
              subprocess.run(['node','--check',str(p)],check=True)
          PY
```

- [ ] **Step 2: Run all relevant tests locally/through Actions**

Expected: every new feature contract is green; any unrelated pre-existing failing contract must be reported accurately rather than hidden.

- [ ] **Step 3: Commit workflow**

```bash
git add .github/workflows/dynamic-mavlink-viewer.yml
git commit -m "ci: verify dynamic MAVLink viewer"
```

- [ ] **Step 4: Verify final `main` state**

Confirm the latest commit contains:

- `backend/mavlink_plot.py`;
- `mavlink_plot` in API response;
- `board_messages` in API response;
- dynamic checkbox panel under graph;
- multi-series lines with distinct deterministic colors;
- unit-aware axis grouping and visible axis-limit warning;
- board message panel under attitude dashboard;
- existing flight-mode badge and attitude synchronization.

- [ ] **Step 5: Verify GitHub Pages deployment**

Wait for the Pages run associated with the final frontend commit and verify both `build` and `deploy` conclude `success` before claiming completion.

---

## Self-review

- Spec coverage: dynamic discovery, numeric-only filtering, shared time base, deterministic downsampling, search/groups/checkboxes, distinct colors, compatible-unit axes, presets, board messages, ±5 s window, severity colors, fallback behavior, regressions, rollback, and Pages verification are each mapped to a task.
- Placeholder scan: no `TBD`, `TODO`, or undefined implementation step remains.
- Type consistency: `MavlinkPlotCollector.build()` produces `mavlink_plot.groups`; frontend consumes the same shape. `build_board_messages()` produces `time_ms/level/text/event_type`; frontend consumes those exact keys.
