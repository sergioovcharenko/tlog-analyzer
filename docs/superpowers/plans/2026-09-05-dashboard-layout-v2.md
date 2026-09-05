# TLOG Analyzer Dashboard Layout v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the existing graph workspace into the approved second dashboard layout with a tabbed right dock, responsive desktop/tablet/phone behavior, preserved current artificial horizon, reorganized MAVLink controls, and a persistent `● Темна / ○ Світла` theme switcher.

**Architecture:** Keep the existing backend and telemetry contracts unchanged. Refactor only `index.html` presentation/state around the current graph viewer, attitude renderer, board-message data and TX16 renderer. Because `index.html` is a large generated/single-file frontend, apply the UI refactor through an idempotent patcher and protect it with static contract tests plus the existing regression suites.

**Tech Stack:** HTML, CSS Grid/Flexbox, vanilla JavaScript, Python unittest contract tests, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-05-dashboard-layout-v2-design.md`

## Global Constraints

- Work only on `feature/dashboard-layout-v2` until verification is green.
- Preserve `backup-before-dashboard-layout-v2` unchanged as rollback.
- Do not change backend API contracts or TLOG parsing.
- Do not change dynamic MAVLink loading/prefetch behavior.
- Do not rewrite artificial-horizon math or rendering.
- Do not change TX16 interpretation or graph data values.
- Dark theme is the default when no preference exists.
- Persist theme in `localStorage` key `tlog-theme` with values `dark` or `light`.
- Theme labels are exactly `● Темна` and `○ Світла`.
- Desktop breakpoint: `>=1200px`; tablet: `768–1199px`; phone: `<768px`.
- No page-level horizontal scrolling at 360, 390, 430, 768, 1024, 1366, 1440, or 1920 px.

---

### Task 1: Add dashboard layout/theme contract tests

**Files:**
- Create: `tests/test_dashboard_layout_v2_contract.py`
- Create: `.github/workflows/dashboard-layout-v2.yml`

**Interfaces:**
- Consumes: generated `index.html` source.
- Produces: a regression contract requiring the new layout markers, right-dock tabs, theme persistence, responsive breakpoints and preserved horizon hooks.

- [ ] **Step 1: Write the failing contract test**

```python
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


class DashboardLayoutV2Contract(unittest.TestCase):
    def test_layout_wrappers_exist(self):
        for marker in (
            'id="graphDashboardV2"',
            'class="graph-dashboard-summary"',
            'class="graph-dashboard-workspace"',
            'class="graph-dashboard-main"',
            'class="graph-dashboard-dock"',
            'id="mavlinkSelectorShell"',
        ):
            self.assertIn(marker, HTML)

    def test_right_dock_tabs_exist(self):
        for tab in ("Авіагоризонт", "Повідомлення", "TX16", "Дані"):
            self.assertIn(f">{tab}<", HTML)
        self.assertIn("setGraphDockTab", HTML)

    def test_theme_control_is_exact_and_persistent(self):
        self.assertIn("● Темна", HTML)
        self.assertIn("○ Світла", HTML)
        self.assertIn("localStorage.getItem('tlog-theme')", HTML)
        self.assertIn("localStorage.setItem('tlog-theme'", HTML)
        self.assertIn("data-tlog-theme", HTML)

    def test_responsive_breakpoints_exist(self):
        self.assertRegex(HTML, r"@media\s*\(max-width:\s*1199px\)")
        self.assertRegex(HTML, r"@media\s*\(max-width:\s*767px\)")
        self.assertIn("overflow-x:hidden", HTML.replace(" ", ""))

    def test_current_horizon_hooks_are_not_replaced(self):
        self.assertIn("graphAttitudeHorizon", HTML)
        self.assertIn("graphAttitudeRoll", HTML)
        self.assertIn("graphAttitudePitch", HTML)
        self.assertIn("graphAttitudeYaw", HTML)

    def test_tab_and_theme_switches_are_frontend_only(self):
        tab_body = re.search(r"function setGraphDockTab\([^)]*\)\{.*?\n\}", HTML, re.S)
        self.assertIsNotNone(tab_body)
        self.assertNotIn("fetch(", tab_body.group(0))
        theme_body = re.search(r"function setTlogTheme\([^)]*\)\{.*?\n\}", HTML, re.S)
        self.assertIsNotNone(theme_body)
        self.assertNotIn("fetch(", theme_body.group(0))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and verify RED**

Run:
```bash
python -m unittest tests.test_dashboard_layout_v2_contract -v
```
Expected: FAIL because `graphDashboardV2`, dock tabs and theme functions do not yet exist.

- [ ] **Step 3: Add the dedicated workflow**

```yaml
name: Dashboard layout v2

on:
  push:
    branches: [feature/dashboard-layout-v2, main]
    paths:
      - index.html
      - tools/apply_dashboard_layout_v2.py
      - tests/test_dashboard_layout_v2_contract.py
      - .github/workflows/dashboard-layout-v2.yml
  pull_request:
    paths:
      - index.html
      - tools/apply_dashboard_layout_v2.py
      - tests/test_dashboard_layout_v2_contract.py

jobs:
  contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m unittest tests.test_dashboard_layout_v2_contract -v
      - run: python -m unittest tests.test_dynamic_mavlink_plot_ui -v
      - run: python -m unittest tests.test_attitude_dashboard_v22_contract -v
      - run: python -m unittest tests.test_tx16_ui_contract -v
      - name: Inline JavaScript syntax
        run: |
          python - <<'PY'
          from pathlib import Path
          import re, subprocess, tempfile
          html = Path('index.html').read_text(encoding='utf-8')
          scripts = re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', html, re.S | re.I)
          with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
              f.write('\n'.join(scripts))
              path = f.name
          subprocess.run(['node', '--check', path], check=True)
          PY
```

- [ ] **Step 4: Commit the RED contract**

```bash
git add tests/test_dashboard_layout_v2_contract.py .github/workflows/dashboard-layout-v2.yml
git commit -m "test: define dashboard layout v2 contract"
```

---

### Task 2: Add theme tokens and persistent theme switcher

**Files:**
- Create: `tools/apply_dashboard_layout_v2.py`
- Modify through patcher: `index.html` root variables/header controls/graph-viewer JavaScript.
- Test: `tests/test_dashboard_layout_v2_contract.py`

**Interfaces:**
- Consumes: existing CSS custom properties and graph viewer DOM.
- Produces:
  - `setTlogTheme(theme: 'dark'|'light') -> void`
  - `initTlogTheme() -> void`
  - root attribute `data-tlog-theme="dark|light"`
  - persistent key `tlog-theme`.

- [ ] **Step 1: Extend the failing theme assertions**

Add these assertions to `test_theme_control_is_exact_and_persistent`:

```python
self.assertIn("--graph-bg", HTML)
self.assertIn("--graph-grid", HTML)
self.assertIn("--input-bg", HTML)
self.assertIn("[data-tlog-theme=\"light\"]", HTML)
```

- [ ] **Step 2: Run only the theme test and verify RED**

```bash
python -m unittest tests.test_dashboard_layout_v2_contract.DashboardLayoutV2Contract.test_theme_control_is_exact_and_persistent -v
```
Expected: FAIL on the new theme tokens.

- [ ] **Step 3: Implement an idempotent patcher marker and theme CSS**

`tools/apply_dashboard_layout_v2.py` must:
- exit with code 0 and no change if `/* DASHBOARD_LAYOUT_V2 */` already exists;
- insert these extra dark defaults into `:root`:

```css
--panel-bg:#121820;
--panel-bg-2:#0f141c;
--input-bg:#0d131a;
--graph-bg:#0b1017;
--graph-grid:rgba(148,163,184,.14);
--shadow-color:rgba(0,0,0,.28);
```

- append a light override:

```css
[data-tlog-theme="light"]{
  --bg-main:#eef3f8;
  --bg-card:#ffffff;
  --bg-header:#f8fafc;
  --panel-bg:#ffffff;
  --panel-bg-2:#f1f5f9;
  --input-bg:#ffffff;
  --border-color:#cbd5e1;
  --border-highlight:#94a3b8;
  --text-main:#0f172a;
  --text-muted:#475569;
  --graph-bg:#ffffff;
  --graph-grid:rgba(51,65,85,.16);
  --shadow-color:rgba(15,23,42,.10);
}
```

- [ ] **Step 4: Implement theme control and persistence**

The generated frontend must include:

```javascript
function setTlogTheme(theme){
  const next=theme==='light'?'light':'dark';
  document.documentElement.setAttribute('data-tlog-theme',next);
  localStorage.setItem('tlog-theme',next);
  document.querySelectorAll('[data-theme-choice]').forEach(btn=>{
    btn.classList.toggle('active',btn.dataset.themeChoice===next);
    btn.setAttribute('aria-pressed',btn.dataset.themeChoice===next?'true':'false');
  });
  if(typeof redrawGraphViewer==='function'){
    try{redrawGraphViewer();}catch(_e){}
  }
}
function initTlogTheme(){
  setTlogTheme(localStorage.getItem('tlog-theme')||'dark');
}
```

Theme buttons:

```html
<div class="tlog-theme-switch" role="group" aria-label="Тема">
  <button type="button" data-theme-choice="dark" onclick="setTlogTheme('dark')">● Темна</button>
  <button type="button" data-theme-choice="light" onclick="setTlogTheme('light')">○ Світла</button>
</div>
```

Initialize once after DOM creation with `initTlogTheme();`.

- [ ] **Step 5: Apply patch and run theme contract**

```bash
python tools/apply_dashboard_layout_v2.py
python -m unittest tests.test_dashboard_layout_v2_contract.DashboardLayoutV2Contract.test_theme_control_is_exact_and_persistent -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/apply_dashboard_layout_v2.py index.html tests/test_dashboard_layout_v2_contract.py
git commit -m "feat: add persistent light and dark dashboard themes"
```

---

### Task 3: Build the desktop dashboard shell and top summary zone

**Files:**
- Modify: `tools/apply_dashboard_layout_v2.py`
- Generated modify: `index.html`
- Test: `tests/test_dashboard_layout_v2_contract.py`

**Interfaces:**
- Consumes: the existing graph viewer result object and existing telemetry readouts.
- Produces DOM containers:
  - `#graphDashboardV2`
  - `.graph-dashboard-summary`
  - `.graph-dashboard-workspace`
  - `.graph-dashboard-main`
  - `.graph-dashboard-dock`.

- [ ] **Step 1: Add failing assertions for summary labels**

```python
for label in ("ЧАС", "РЕЖИМ", "ВИСОТА", "ДАЛЬНІСТЬ", "АЗИМУТ", "НАПРУГА", "СТРУМ", "RSSI", "dBm"):
    self.assertIn(label, HTML)
```

- [ ] **Step 2: Verify RED**

```bash
python -m unittest tests.test_dashboard_layout_v2_contract.DashboardLayoutV2Contract.test_layout_wrappers_exist -v
```

- [ ] **Step 3: Wrap existing graph viewer content instead of duplicating it**

The patcher must generate this structural shell around the existing graph/attitude content:

```html
<section id="graphDashboardV2" class="graph-dashboard-v2">
  <div class="graph-dashboard-summary" id="graphDashboardSummary"></div>
  <div class="graph-dashboard-workspace">
    <div class="graph-dashboard-main" id="graphDashboardMain"></div>
    <aside class="graph-dashboard-dock" id="graphDashboardDock"></aside>
  </div>
  <section id="mavlinkSelectorShell" class="mavlink-selector-shell"></section>
</section>
```

Existing graph DOM nodes are moved into `#graphDashboardMain`; existing horizon/message/TX16 DOM nodes are moved into dock panels. Do not clone IDs.

- [ ] **Step 4: Add summary rendering helper**

Generate:

```javascript
function renderGraphDashboardSummary(snapshot){
  const host=document.getElementById('graphDashboardSummary');
  if(!host)return;
  const items=[
    ['ЧАС',snapshot.time??'—'],
    ['РЕЖИМ',snapshot.mode??'—'],
    ['ВИСОТА',snapshot.altitude??'—'],
    ['ДАЛЬНІСТЬ',snapshot.distance??'—'],
    ['АЗИМУТ',snapshot.heading??'—'],
    ['НАПРУГА',snapshot.voltage??'—'],
    ['СТРУМ',snapshot.current??'—'],
    ['RSSI',snapshot.rssi??'—'],
    ['dBm',snapshot.dbm??'—'],
    ['TEMP',snapshot.temperature??'—'],
  ];
  host.innerHTML=items.map(([k,v])=>`<div class="graph-summary-item"><span>${k}</span><strong>${v}</strong></div>`).join('');
}
```

Bind the helper to the same current cursor/state values already used for graph/horizon readouts; where a value is unavailable, render `—`.

- [ ] **Step 5: Add desktop grid CSS**

```css
.graph-dashboard-workspace{
  display:grid;
  grid-template-columns:minmax(0,3fr) minmax(320px,1fr);
  gap:14px;
  align-items:start;
}
.graph-dashboard-main{min-width:0}
.graph-dashboard-dock{min-width:0}
.graph-dashboard-summary{
  display:grid;
  grid-template-columns:repeat(10,minmax(86px,1fr));
  gap:8px;
  margin-bottom:12px;
}
```

- [ ] **Step 6: Run layout contract**

```bash
python -m unittest tests.test_dashboard_layout_v2_contract -v
```
Expected: layout wrapper checks PASS; dock/theme tests may remain pending until later tasks.

- [ ] **Step 7: Commit**

```bash
git add tools/apply_dashboard_layout_v2.py index.html tests/test_dashboard_layout_v2_contract.py
git commit -m "feat: add dashboard v2 workspace shell"
```

---

### Task 4: Add right dock tabs while preserving the current artificial horizon

**Files:**
- Modify: `tools/apply_dashboard_layout_v2.py`
- Generated modify: `index.html`
- Test: `tests/test_dashboard_layout_v2_contract.py`

**Interfaces:**
- Consumes: current horizon DOM IDs, board messages block, TX16 block, auxiliary readouts.
- Produces `setGraphDockTab(name: 'attitude'|'messages'|'tx16'|'data') -> void`.

- [ ] **Step 1: Verify right-dock test is RED**

```bash
python -m unittest tests.test_dashboard_layout_v2_contract.DashboardLayoutV2Contract.test_right_dock_tabs_exist -v
```

- [ ] **Step 2: Generate dock tab bar**

```html
<div class="graph-dock-tabs" role="tablist">
  <button data-dock-tab="attitude" onclick="setGraphDockTab('attitude')">Авіагоризонт</button>
  <button data-dock-tab="messages" onclick="setGraphDockTab('messages')">Повідомлення</button>
  <button data-dock-tab="tx16" onclick="setGraphDockTab('tx16')">TX16</button>
  <button data-dock-tab="data" onclick="setGraphDockTab('data')">Дані</button>
</div>
```

Panels use `data-dock-panel` with corresponding values.

- [ ] **Step 3: Implement frontend-only tab state**

```javascript
function setGraphDockTab(name){
  const allowed=new Set(['attitude','messages','tx16','data']);
  const next=allowed.has(name)?name:'attitude';
  document.querySelectorAll('[data-dock-tab]').forEach(btn=>{
    const active=btn.dataset.dockTab===next;
    btn.classList.toggle('active',active);
    btn.setAttribute('aria-selected',active?'true':'false');
  });
  document.querySelectorAll('[data-dock-panel]').forEach(panel=>{
    panel.hidden=panel.dataset.dockPanel!==next;
  });
}
```

No `fetch`, upload, or graph parser calls are permitted here.

- [ ] **Step 4: Move, do not recreate, the horizon DOM**

The patcher must relocate the existing container containing:
- `#graphAttitudeHorizon`
- `#graphAttitudeRoll`
- `#graphAttitudePitch`
- `#graphAttitudeYaw`

into `data-dock-panel="attitude"` without renaming those IDs or altering their draw/update functions.

- [ ] **Step 5: Move existing board messages/TX16 blocks into their panels**

Preserve their existing event handlers and data sources. If either block is currently created dynamically, append that existing node into the panel after creation rather than duplicating its markup.

- [ ] **Step 6: Run contracts**

```bash
python -m unittest tests.test_dashboard_layout_v2_contract -v
python -m unittest tests.test_attitude_dashboard_v22_contract -v
python -m unittest tests.test_tx16_ui_contract -v
```
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add tools/apply_dashboard_layout_v2.py index.html
git commit -m "feat: organize horizon messages and tx16 into dock tabs"
```

---

### Task 5: Reorganize selected series and MAVLink selector

**Files:**
- Modify: `tools/apply_dashboard_layout_v2.py`
- Generated modify: `index.html`
- Test: `tests/test_dashboard_layout_v2_contract.py`
- Existing regression: `tests/test_dynamic_mavlink_plot_ui.py`

**Interfaces:**
- Consumes: current selected dynamic MAVLink series state and current field browser.
- Produces:
  - `#graphSelectedSeriesChips`
  - `#mavlinkSelectorShell`
  - collapse control preserving selected-series chips.

- [ ] **Step 1: Add failing contract for chips and selector controls**

```python
for marker in (
    'id="graphSelectedSeriesChips"',
    'id="mavlinkSelectorToggle"',
    'data-mavlink-preset="Altitude"',
    'data-mavlink-preset="Power"',
    'data-mavlink-preset="Radio"',
    'data-mavlink-preset="Attitude"',
    'data-mavlink-preset="ESC"',
):
    self.assertIn(marker, HTML)
```

- [ ] **Step 2: Verify RED**

```bash
python -m unittest tests.test_dashboard_layout_v2_contract -v
```

- [ ] **Step 3: Add selected-series chip host next to graph controls**

```html
<div id="graphSelectedSeriesChips" class="graph-series-chips" aria-label="Активні серії"></div>
```

Render chips from the existing selected-series collection. Chip removal must call the same existing unselect/remove path used by checkbox interaction; do not create a second graph state store.

- [ ] **Step 4: Add collapsible selector shell and preset controls**

```html
<div class="mavlink-selector-head">
  <button id="mavlinkSelectorToggle" type="button" aria-expanded="true">MAVLink параметри</button>
  <input id="mavlinkSelectorSearchV2" type="search" placeholder="Пошук параметрів...">
  <div class="mavlink-presets">
    <button data-mavlink-preset="Altitude">Altitude</button>
    <button data-mavlink-preset="Power">Power</button>
    <button data-mavlink-preset="Radio">Radio</button>
    <button data-mavlink-preset="Attitude">Attitude</button>
    <button data-mavlink-preset="ESC">ESC</button>
  </div>
</div>
```

The existing dynamic field groups/checkboxes are mounted inside the collapsible body. Search filters only rendered field rows and does not request new data.

- [ ] **Step 5: Ensure chips remain visible while selector body is collapsed**

Only the checkbox-browser body is hidden; `#graphSelectedSeriesChips` stays outside the collapsed body.

- [ ] **Step 6: Run graph UI regressions**

```bash
python -m unittest tests.test_dashboard_layout_v2_contract -v
python -m unittest tests.test_dynamic_mavlink_plot_ui -v
```
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tools/apply_dashboard_layout_v2.py index.html tests/test_dashboard_layout_v2_contract.py
git commit -m "feat: reorganize dynamic mavlink graph controls"
```

---

### Task 6: Add tablet and phone responsive behavior

**Files:**
- Modify: `tools/apply_dashboard_layout_v2.py`
- Generated modify: `index.html`
- Test: `tests/test_dashboard_layout_v2_contract.py`

**Interfaces:**
- Consumes: dashboard wrappers from Tasks 3–5.
- Produces responsive CSS and phone workspace tabs without altering data/rendering functions.

- [ ] **Step 1: Add failing mobile contract**

```python
for label in ("Огляд", "Графік", "Авіагоризонт", "Повідомлення"):
    self.assertIn(f'data-mobile-dashboard-tab="{label}"', HTML)
self.assertIn("min-height:44px", HTML.replace(" ", ""))
```

- [ ] **Step 2: Verify RED**

```bash
python -m unittest tests.test_dashboard_layout_v2_contract -v
```

- [ ] **Step 3: Add tablet CSS at 1199 px**

```css
@media (max-width:1199px){
  .graph-dashboard-workspace{grid-template-columns:1fr}
  .graph-dashboard-summary{grid-template-columns:repeat(5,minmax(0,1fr))}
  .graph-dashboard-dock{width:100%}
}
```

- [ ] **Step 4: Add phone CSS at 767 px**

```css
@media (max-width:767px){
  html,body{max-width:100%;overflow-x:hidden}
  .graph-dashboard-summary{grid-template-columns:repeat(2,minmax(0,1fr))}
  .graph-dashboard-v2{width:100%;min-width:0}
  .graph-dashboard-main,.graph-dashboard-dock,.mavlink-selector-shell{min-width:0;width:100%}
  .graph-dock-tabs button,.tlog-theme-switch button,.mobile-dashboard-tabs button{min-height:44px}
  .graph-series-chips{overflow-x:auto;max-width:100%}
}
```

- [ ] **Step 5: Add phone navigation labels**

```html
<nav class="mobile-dashboard-tabs" aria-label="Розділи графіка">
  <button data-mobile-dashboard-tab="Огляд">Огляд</button>
  <button data-mobile-dashboard-tab="Графік">Графік</button>
  <button data-mobile-dashboard-tab="Авіагоризонт">Авіагоризонт</button>
  <button data-mobile-dashboard-tab="Повідомлення">Повідомлення</button>
</nav>
```

On phone only, these controls change visible frontend sections; they do not create/destroy graph or horizon components and must not trigger fetches.

- [ ] **Step 6: Run contract + JavaScript syntax**

```bash
python -m unittest tests.test_dashboard_layout_v2_contract -v
python - <<'PY'
from pathlib import Path
import re, subprocess, tempfile
html=Path('index.html').read_text(encoding='utf-8')
scripts=re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',html,re.S|re.I)
with tempfile.NamedTemporaryFile('w',suffix='.js',delete=False,encoding='utf-8') as f:
    f.write('\n'.join(scripts)); p=f.name
subprocess.run(['node','--check',p],check=True)
PY
```
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tools/apply_dashboard_layout_v2.py index.html tests/test_dashboard_layout_v2_contract.py
git commit -m "feat: make graph dashboard responsive"
```

---

### Task 7: Full regression verification, branch review and release to main

**Files:**
- Verify only; modify only if a regression test exposes a dashboard-v2 defect.

**Interfaces:**
- Consumes: completed feature branch.
- Produces: verified commit ready for fast-forward/PR merge to `main`.

- [ ] **Step 1: Verify patcher idempotency**

```bash
python tools/apply_dashboard_layout_v2.py
git diff --exit-code
```
Expected: no diff on the second application.

- [ ] **Step 2: Run all relevant frontend contracts**

```bash
python -m unittest tests.test_dashboard_layout_v2_contract -v
python -m unittest tests.test_dynamic_mavlink_plot_ui -v
python -m unittest tests.test_dynamic_mavlink_plot_backend -v
python -m unittest tests.test_attitude_dashboard_v22_contract -v
python -m unittest tests.test_tx16_ui_contract -v
```
Expected: all PASS.

- [ ] **Step 3: Compile backend to prove no accidental backend damage**

```bash
python -m py_compile backend/main.py backend/mavlink_plot.py
```
Expected: exit 0.

- [ ] **Step 4: Verify inline JavaScript syntax**

Use the Node extraction/check command from Task 6. Expected: PASS.

- [ ] **Step 5: Inspect diff scope**

Expected changed implementation paths only:
- `index.html`
- `tools/apply_dashboard_layout_v2.py`
- `tests/test_dashboard_layout_v2_contract.py`
- `.github/workflows/dashboard-layout-v2.yml`
- spec/plan docs

No backend behavior changes should appear.

- [ ] **Step 6: Check GitHub Actions on feature branch**

Required green workflows:
- Dashboard layout v2
- Dynamic MAVLink plot feature
- Attitude dashboard v2.2
- TX16 drop UI contract
- Frontend flow contract

- [ ] **Step 7: Merge only after green CI**

Fast-forward or merge the verified feature head into `main` without deleting `backup-before-dashboard-layout-v2`.

- [ ] **Step 8: Verify Pages deployment**

Confirm the Pages build for the new `main` commit completes with `success` before declaring the rollout complete.

- [ ] **Step 9: Manual acceptance check**

Open the deployed page and validate:
- desktop: graph dominant, right dock tabs switch locally;
- theme: `● Темна / ○ Світла` changes immediately and persists after refresh;
- current artificial horizon still behaves/synchronizes as before;
- MAVLink chips and selector work without extra backend requests;
- 360/390/430 px: no page-level horizontal overflow;
- 768/1024 px: workspace stacks cleanly.

- [ ] **Step 10: Final commit if verification fixes were needed**

```bash
git add index.html tools/apply_dashboard_layout_v2.py tests/test_dashboard_layout_v2_contract.py .github/workflows/dashboard-layout-v2.yml
git commit -m "fix: finalize dashboard layout v2 regressions"
```

If no fixes were needed, do not create an empty commit.
