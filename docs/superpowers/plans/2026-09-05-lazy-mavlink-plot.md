# Lazy MAVLink Plot Loading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore fast initial TLOG analysis by moving the expensive dynamic MAVLink catalog to a separate request that runs only when the graph viewer is opened.

**Architecture:** `/analyze` keeps all existing flight analysis, Timeline, legacy graph data, board messages, TX16, map, battery and diagnostics, but no longer calls `msg.to_dict()` for every packet just to build the dynamic MAVLink catalog. A new `/mavlink-plot` endpoint reparses the same uploaded TLOG on demand and returns only `mavlink_plot`. The frontend posts the already-selected file to that endpoint when the user clicks the graph button, merges the result into the existing analysis object, and then opens the existing viewer.

**Tech Stack:** FastAPI, pymavlink, vanilla JavaScript, GitHub Actions, Python unittest.

**Spec:** User-approved design in chat: initial analysis first; full dynamic MAVLink catalog only when `Переглянути графік` is pressed.

## Global Constraints

- Preserve existing analysis calculations and result fields except removing `mavlink_plot` from the initial `/analyze` response.
- Keep legacy `graph_data` and board messages in `/analyze` so the normal results remain immediately usable.
- Keep the selected TLOG in browser memory and reuse it for the on-demand request; do not upload anything before the graph button is clicked.
- Dynamic plot endpoint must still cap series to the existing collector limits.
- On-demand load failure must show a useful UI error and leave the main analysis results intact.

---

### Task 1: Contract tests

**Files:**
- Create: `tests/test_lazy_mavlink_plot.py`

**Interfaces:**
- Consumes: current `backend/main.py` and `index.html`
- Produces: static contracts for endpoint separation and lazy frontend loading

- [ ] Write tests that require `/mavlink-plot`, forbid `mavlink_plot_collector` inside the `/analyze` body, and require `ensureDynamicMavlinkPlot()` plus graph-button lazy loading in `index.html`.
- [ ] Run the test and confirm RED on current code.

### Task 2: Backend separation

**Files:**
- Modify generated: `backend/main.py`
- Create: `tools/apply_lazy_mavlink_plot.py`

**Interfaces:**
- Produces: `POST /mavlink-plot` returning `{success, mavlink_plot}`

- [ ] Remove dynamic collector initialization, `.add(msg.to_dict())`, and `mavlink_plot` build/response field from `/analyze`.
- [ ] Append an isolated endpoint that copies the upload to a temp file, reads MAVLink packets, collects numeric scalar series, returns the catalog, and cleans up.

### Task 3: Frontend lazy load

**Files:**
- Modify generated: `index.html`
- Modify: `tools/apply_lazy_mavlink_plot.py`

**Interfaces:**
- Produces: `ensureDynamicMavlinkPlot(result)` and async graph-button handler

- [ ] Add a helper that posts `selectedFile` to `/mavlink-plot` only if `result.mavlink_plot` is missing.
- [ ] Show `Завантаження графіків...` on the graph button while loading and restore its label afterwards.
- [ ] Merge the returned catalog into the current result and open the existing viewer.

### Task 4: Verification and integration

**Files:**
- Create/modify: `.github/workflows/lazy-mavlink-plot.yml`

- [ ] Apply the patcher in CI.
- [ ] Run lazy contracts, existing dynamic MAVLink backend/UI tests, attitude regression, TX16 regression, Python syntax, and inline JavaScript syntax.
- [ ] Commit generated `backend/main.py` and `index.html` on the feature branch.
- [ ] Fast-forward `main` only after the full workflow is green and verify Pages deployment.
