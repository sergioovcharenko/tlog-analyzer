# Graph + Attitude Viewer — Design

Date: 2026-09-04
Repository: `sergioovcharenko/tlog-analyzer`

## Goal

Add a separate interactive telemetry-analysis mode to the existing TLOG Analyzer without disturbing the current main analysis flow.

The new mode is opened from the existing page through a button labeled **«📈 Переглянути графік»** and presents:

- a large interactive time-series graph;
- a telemetry metric selector;
- a synchronized artificial horizon (attitude indicator);
- graceful handling when a metric is not present in the uploaded TLOG.

The implementation should follow the general user experience of UAVLogViewer while using this repository's own code and existing parsed TLOG data.

## Safety / rollback

Before feature implementation starts, create a backup branch from the current stable `main` commit. The feature is implemented in small commits so it can be reverted cleanly if the result is unstable or undesirable.

Current stable baseline at design time: `b9953d0febe233580428c19cc2eb0f9bac7a1b04`.

## User experience

### Entry point

On the main analysis page, after a TLOG has been successfully analyzed, show a button:

**«📈 Переглянути графік»**

The button opens a dedicated fullscreen-style overlay/panel inside the same `index.html`. The existing analysis view remains unchanged behind it.

### Graph viewer layout

Desktop layout:

1. top toolbar with close button and metric selector;
2. large interactive graph occupying most of the width;
3. attitude indicator placed to the right of the graph;
4. compact current-value strip below or beside the attitude indicator.

Mobile layout:

- graph first;
- metric selector above graph;
- attitude indicator below graph;
- no horizontal page overflow.

### Metric selection

Initial supported metric groups should use only data already returned by the current analyzer or straightforward additions from the TLOG parser:

- Altitude
- Voltage
- Current
- Ground speed / airspeed when available
- Engine load / throttle
- dBm / radio signal values when available
- Roll
- Pitch
- Yaw / heading
- RC input channels when available
- ESC/RPM metrics when available

A missing metric must not break the viewer. It should be disabled or show **«Немає даних у цьому TLOG»**.

The first implementation should support one selected metric at a time. The code structure should allow multi-series graphs later without reworking the whole viewer.

## Graph behavior

The graph uses elapsed flight time on the X axis and the selected telemetry metric on the Y axis.

Required interactions:

- hover shows time and exact value;
- click selects/pins a moment in time;
- zoom/pan when supported by the chosen chart library;
- a visible vertical cursor marks the selected time;
- changing the selected metric preserves the current selected time when practical.

The first version does not need synchronization with the existing map, TX16S sticks, or Timeline. Those integrations are explicitly deferred to a later phase.

## Attitude indicator

The attitude indicator is synchronized to the graph's selected time.

Primary MAVLink source:

- `ATTITUDE.time_boot_ms`
- `ATTITUDE.roll`
- `ATTITUDE.pitch`

If the backend exposes alternate ArduPilot attitude fields, they may be used as fallback.

Roll and pitch are converted to degrees for display. The indicator should visually resemble a conventional artificial horizon but be implemented independently in this project rather than copying UAVLogViewer source code.

The attitude panel should also display numeric values:

- Roll, °
- Pitch, °
- Yaw/Heading, ° when available
- Altitude, m when available

## Architecture

### Frontend

Primary file: `index.html`.

Add a self-contained graph-viewer module within the existing page:

- overlay/panel markup;
- viewer-specific CSS classes;
- metric registry/configuration;
- graph initialization/update functions;
- attitude-rendering functions;
- time-selection synchronization.

Avoid unrelated refactoring of the current analysis page.

If the graph implementation requires a library, prefer a lightweight browser library compatible with the existing static GitHub Pages deployment. The library must not require Vue or another frontend framework solely for this feature.

### Backend

Primary file: `backend/main.py`.

The frontend should consume existing analyzer output wherever possible. Only add backend fields that are necessary for graphing and attitude playback.

Preferred response shape for time-series data:

```json
{
  "graph_data": {
    "time_ms": [],
    "altitude_m": [],
    "voltage_v": [],
    "current_a": [],
    "groundspeed_ms": [],
    "engine_load_pct": [],
    "radio_dbm": [],
    "roll_deg": [],
    "pitch_deg": [],
    "yaw_deg": []
  }
}
```

Arrays may be omitted when no valid source exists. The frontend must not assume every field is present.

If large raw streams create excessive response size, the backend may downsample for display while preserving important peaks/min/max and event timing. No downsampling is required in the first implementation unless response size or browser performance requires it.

### Offline version

After the online feature is stable, mirror the same behavior into `offline/index.html` and `offline/main.py`. This is not required for the first online proof unless implementation is trivial to share safely.

## Data flow

1. User uploads and analyzes a TLOG through the existing flow.
2. Backend parses normal analysis plus graph/attitude time-series data.
3. Frontend stores the analysis result as it does today.
4. User presses **«Переглянути графік»**.
5. Viewer builds the metric menu based on available series.
6. Graph renders the selected metric against elapsed time.
7. Hover/click chooses a timestamp.
8. Attitude viewer finds the closest attitude sample for that timestamp and updates roll/pitch/yaw/altitude values.
9. Closing the viewer returns to the existing analysis page without re-uploading or re-analyzing the TLOG.

## Error handling

- No analyzed TLOG: graph button remains hidden or disabled.
- Empty series: show a clear Ukrainian no-data message.
- ATTITUDE unavailable: graph remains usable; attitude panel shows **«Немає ATTITUDE у цьому TLOG»**.
- Invalid numeric values (`NaN`, infinity, null): filter them from plotting.
- Unequal series lengths: use each series' own time/value pairs or validate on the backend before returning.
- Graph library load failure: show a readable error instead of breaking the main page.

## Testing

Add focused regression/contract tests for:

1. the graph-viewer button and container exist;
2. graph mode does not alter the existing main-analysis rendering path;
3. metric registry handles missing data without exceptions;
4. `ATTITUDE` roll/pitch conversion is correct;
5. time selection chooses the nearest valid attitude sample;
6. graph viewer can open and close without triggering a new TLOG analysis;
7. JavaScript syntax remains valid;
8. existing TX16S / Timeline / map UI contract tests still pass.

Manual verification should include at least one TLOG containing ATTITUDE and one TLOG with partial/missing graph metrics.

## Out of scope for phase 1

- simultaneous overlay of multiple metrics;
- synchronized existing 2D/3D map cursor;
- synchronized TX16S stick animation;
- automatic graph annotations for all flight-mode changes;
- copying UAVLogViewer Vue components or source code;
- redesigning the current main analyzer UI.

## Phase 2 candidates

After phase 1 is stable:

- multi-series graph selection;
- flight-mode colored regions;
- synchronized map point;
- synchronized TX16S sticks and switch state;
- event markers / errors on graph;
- min/max/mean statistics;
- export graph as image or CSV.

## Acceptance criteria

Phase 1 is complete when:

- the current analyzer still works exactly as before;
- a user can open **«Переглянути графік»** after analysis;
- at least Altitude, Voltage, Current, Engine Load and available attitude fields can be selected when present;
- the graph is interactive;
- the attitude indicator follows the selected graph time using TLOG roll/pitch data;
- missing telemetry does not crash the viewer;
- the feature can be fully rolled back to the recorded stable baseline if necessary.
