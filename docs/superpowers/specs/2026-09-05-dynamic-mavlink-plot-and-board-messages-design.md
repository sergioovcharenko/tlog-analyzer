# Dynamic MAVLink Plot Viewer + Board Messages — Design

Date: 2026-09-05
Repository: `sergioovcharenko/tlog-analyzer`

## Goal

Extend the existing TLOG graph/attitude viewer into a dynamic MAVLink plot viewer inspired by ArduPilot Plot, while preserving the current dark UI, synchronized time cursor, artificial horizon, flight-mode badge, and existing analysis behavior.

The new viewer must let the user discover and select numeric MAVLink fields that actually exist in the uploaded TLOG, plot several selected series at once, and show board messages/errors synchronized to the selected time.

## Scope

This feature has two coordinated parts:

1. Dynamic MAVLink field catalog + multi-series plotting.
2. Time-synchronized board messages/errors panel below the attitude panel.

The existing analysis calculations, Timeline semantics, TX16S UI, map logic, and current graph_data series remain intact unless explicitly reused as inputs.

## User experience

### Dynamic MAVLink panel

A new panel appears under the main graph in the horizontal area currently unused below the chart.

It contains:

- search/filter input;
- collapsible groups by MAVLink message type;
- one checkbox per plottable numeric field;
- a color marker per selected series;
- short unit label when it can be inferred safely;
- optional current value at the selected graph time;
- clear-all action.

Examples of generated groups/fields, only when present in the TLOG:

- `ATTITUDE.roll`, `ATTITUDE.pitch`, `ATTITUDE.yaw`, angular rates;
- `VFR_HUD.airspeed`, `groundspeed`, `alt`, `climb`, `throttle`;
- `SYS_STATUS.voltage_battery`, `current_battery`, load;
- `BATTERY_STATUS.*`;
- `EFI_STATUS.*`;
- `GPS_RAW_INT.*`, `GLOBAL_POSITION_INT.*`;
- `RADIO_STATUS.*`;
- `RC_CHANNELS.*`;
- `SERVO_OUTPUT_RAW.*`;
- ESC telemetry messages;
- AHRS/EKF/IMU fields and any other numeric scalar fields found in that TLOG.

The catalog is not a hard-coded allowlist. It is generated from decoded MAVLink messages actually encountered during analysis.

### Plottable values

Only finite numeric scalar fields are plotted.

Excluded from plotting:

- strings;
- byte arrays/payload blobs;
- non-numeric arrays;
- nested structures that cannot be represented as one scalar series;
- MAVLink transport metadata that does not provide useful telemetry.

If a numeric array is important later, it can be exposed as indexed scalar fields in a separate follow-up feature, but it is out of scope for this first implementation.

### Multi-series chart

The current chart becomes a multi-series chart while preserving:

- zoom;
- pan;
- hover/click cursor;
- tooltip;
- synchronization with attitude, flight mode, and right-side telemetry cards.

Selected series are drawn with distinct deterministic colors.

Fields with the same or compatible unit may share a Y scale. Fields with different units should use separate logical Y scales so values such as volts, amps, percent, degrees, RPM, and temperature are not forced onto one numeric range.

Initial implementation should cap the number of simultaneously visible Y-axis groups to a practical limit and degrade gracefully if many incompatible units are selected. The UI must not silently misrepresent values.

### Presets

The existing single `Показник` selector can remain as a convenience preset selector for common views such as:

- Altitude;
- Power;
- Radio;
- Attitude;
- ESC;
- Custom.

Selecting a preset checks the corresponding dynamic fields when available. Manual checkbox changes switch the viewer to Custom.

## Dynamic data model

Backend returns an additional top-level structure, tentatively `mavlink_plot`, containing metadata and time series.

Conceptual shape:

```json
{
  "groups": {
    "ATTITUDE": {
      "roll": {
        "label": "ATTITUDE.roll",
        "unit": "deg",
        "time_ms": [0, 20, 40],
        "values": [0.1, 0.2, 0.15]
      }
    }
  }
}
```

The exact serialized format may be optimized for payload size, but it must preserve:

- message type;
- field name;
- time array;
- numeric values;
- unit metadata when safely inferable;
- stable identity for frontend selection.

## Time base

All dynamic series must use the same elapsed-time basis already used by the graph viewer.

For each MAVLink message sample, convert its receive/log timestamp to milliseconds relative to the same analysis base timestamp used by `graph_data`.

The frontend must therefore be able to use one shared selected time for:

- plotted series;
- artificial horizon;
- flight mode;
- RSSI/dBm;
- battery/current/FC temperature/Engine Load cards;
- board message panel.

## Performance and response-size control

The analyzer must not return every raw packet without limits.

For each numeric field:

- retain true min/max shape for visualization as much as practical;
- limit plotted points to a configured maximum per series;
- use deterministic downsampling for chart-only data;
- do not change the values used by the analyzer's existing diagnostics or Timeline;
- omit empty/constant-noise transport fields if they provide no useful graph value only when the omission rule is explicit and tested.

The implementation should prefer a simple, deterministic downsampling strategy first; a more advanced LTTB/min-max envelope algorithm can be added later if needed.

## Unit inference

Unit inference should be conservative.

Known MAVLink fields may map to display units, e.g.:

- radians converted to degrees for attitude angles where that is already the UI convention;
- millivolts to volts when MAVLink defines the field that way;
- centiamps to amps when MAVLink defines the field that way;
- millimeters to meters where appropriate;
- percentages preserved as percentage values.

Unknown fields keep their native numeric value with a neutral unit label instead of guessing.

## Board messages panel

A new panel appears below the attitude/telemetry cards in the area indicated by the user.

Title: `ПОВІДОМЛЕННЯ БОРТА`.

It shows messages nearest to the currently selected graph time.

Sources include, when present:

- `STATUSTEXT`;
- failsafe messages/events;
- arming/pre-arm messages;
- EKF/GPS warnings;
- battery/power warnings;
- ESC/motor warnings;
- other analyzer timeline error/warning events derived directly from board telemetry.

The panel must distinguish message severity visually:

- critical/error — red;
- warning/attention — orange/yellow;
- info — blue/white;
- recovery/OK — green when appropriate.

Each row should show:

- elapsed time;
- severity;
- message text.

If there is no relevant message near the selected time, display `Немає повідомлень` rather than a stale message.

## Message synchronization window

Messages should be associated with the selected time using a bounded window, not an arbitrary global nearest message.

Recommended initial behavior:

- show messages within approximately ±5 seconds of the selected time;
- if none exist, show `Немає повідомлень`;
- sort by absolute time distance, then timestamp;
- cap visible rows, with scrolling for additional messages.

This avoids showing an unrelated error from minutes earlier as if it belongs to the selected graph point.

## Error handling

- If `mavlink_plot` is absent, current single-series graph continues to work.
- If no dynamic numeric fields are found, show `Немає доступних числових MAVLink параметрів`.
- If a selected series has no data in the visible interval, keep the checkbox selected but show no line and no fabricated values.
- Malformed/NaN/Inf samples are skipped.
- Missing message severity falls back to neutral/info styling.

## Compatibility

The feature must preserve:

- current graph viewer opening/closing;
- current altitude preset;
- horizon Roll/Pitch/Yaw synchronization;
- flight-mode badge;
- current right-side telemetry cards and their threshold colors;
- Timeline and TX16S behavior;
- GitHub Pages deployment.

## Testing strategy

Use TDD.

Tests should cover at least:

1. Backend dynamically discovers numeric MAVLink scalar fields.
2. Backend excludes strings/non-numeric payloads.
3. Dynamic fields have synchronized elapsed `time_ms` arrays.
4. Downsampling caps points without breaking field identity.
5. Frontend contains dynamic group/search/checkbox UI.
6. Selecting multiple fields creates multiple plotted series.
7. Distinct selected series receive distinct colors.
8. Compatible units can share a Y-axis group; incompatible units do not silently share one scale.
9. Existing attitude/horizon synchronization still works.
10. Board messages panel exists and uses the shared selected time.
11. Message panel applies a bounded time window.
12. Severity styles map to critical/warning/info/recovery classes.
13. Inline JavaScript syntax and backend Python syntax pass.
14. Existing graph/attitude/TX16 regression tests still pass.

## Rollback

Before implementation, preserve the current stable `main` head as a rollback branch or tag/reference.

Implementation should be committed in small steps so the dynamic plot subsystem and the board messages panel can be reverted independently if necessary.

## Out of scope for this version

- editing MAVLink values;
- exporting modified logs;
- plotting text fields as lines;
- arbitrary array/vector expansion;
- replacing the existing analyzer diagnostics;
- copying ArduPilot Plot/UAVLogViewer source code directly.

The implementation is inspired by the interaction model but remains an independent implementation inside this analyzer.
