# TLOG Analyzer — PDF/HTML report export design

Date: 2026-09-09
Status: Proposed for user review

## Goal

Add a user-facing report export flow to TLOG Analyzer so a completed analysis can be saved as a standalone HTML report, exported/printed to PDF, or shared through the operating system/browser share sheet when supported.

The report is a compact summary of the analyzed flight. It does not embed the original `.tlog` file.

## User flow

After analysis completes, a new `ЗВІТ` button appears with these actions:

1. `Зберегти PDF`
2. `Зберегти HTML`
3. `Поділитися`
4. `Друк`

The report is generated from the analysis result already present in the frontend. Re-analysis is not required.

## Recommended architecture

Use HTML as the canonical report representation.

- The frontend builds a standalone report document from the current analysis result.
- `Зберегти HTML` downloads that document as a `.html` file.
- `Зберегти PDF` opens the report in a print-optimized context and invokes the browser print dialog so the user can choose `Save as PDF`.
- `Друк` uses the same print-optimized report.
- `Поділитися` uses `navigator.share()` when available. If file sharing is supported, share the generated HTML file; otherwise fall back to downloading HTML with a clear message that the browser does not support direct sharing.

This keeps the first version browser-native and avoids a new backend PDF dependency or server-side file storage.

## Report contents

### 1. Header

- `AI — TLOG Analyzer`
- `Звіт аналізу польоту`
- original TLOG filename when available
- report generation date/time
- analyzed flight duration

### 2. Flight overview

Include available values only. Missing values are shown as `—`, never invented.

- ARM time / DISARM time
- flight modes used
- maximum altitude
- total distance when available
- maximum distance from home when available
- maximum current
- start voltage
- minimum voltage
- voltage sag
- FC temperature
- ESC temperature
- Engine Load average when available

### 3. Radio / link quality

- minimum RSSI
- average dBm
- worst dBm
- number of `-128 dBm` samples when present
- short quality note derived from the existing thresholds/rules, without claiming causal failure from dBm alone

### 4. VTX summary

Preserve the analyzer's current matrix/order:

| K | 5.2 GHz | 5.5 GHz | 5.8 GHz |
|---|---|---|---|
| K1 | 5180 | 5520 | 5700 |
| K2 | 5240 | 5580 | 5765 |
| K3 | 5300 | 5640 | 5825 |

For each frequency include, when available:

- frequency
- number of transitions/selections as currently defined by the analyzer
- AVG dBm calculated by the existing backend/frontend data path

Also identify current best and worst average dBm using the same logic as the live analyzer. The report must not recalculate with different thresholds or filters.

### 5. Critical events and board messages

Create a chronological table with:

- time
- severity
- message
- short analyzer explanation when one already exists

Examples that may appear include:

- `Gyros inconsistent`
- EKF / position warnings
- PreArm warnings
- `Potential Thrust Loss`
- failsafe
- SmartRTL messages
- Crash messages
- communication loss/restored events

Do not manufacture events that are absent from the analysis result.

### 6. AI conclusion

Include the existing AI reconstruction fields when available:

- what happened
- likely sequence
- pilot actions
- possible alternatives
- confidence
- evidence
- dominant scenario

The report uses the analyzer's existing conclusion; report generation must not run a second AI analysis.

### 7. Charts

First version includes compact static snapshots of the most useful charts when the source data exists:

- altitude
- battery voltage/current
- RSSI/dBm
- vibrations
- Engine Load when available

Charts must use the same analyzed telemetry arrays already loaded in the browser. If a chart cannot be rendered for a log because its data is absent, omit that chart instead of showing a broken placeholder.

For PDF/print, charts must be printable on a white background or otherwise remain legible in print. The interactive graph itself is not embedded; the report uses report-specific static chart rendering.

## Visual design

The report should visually match the analyzer but remain readable when printed:

- clean header
- compact metric cards
- restrained status colors
- red for critical items
- yellow/orange for warnings
- green for normal/best values where meaningful
- print CSS removes buttons/navigation and prevents cards/tables from splitting badly across pages

Dark-screen styling can be used for HTML viewing, but print/PDF must use a high-contrast print layout suitable for A4/Letter.

## File names

Default naming:

- `TLOG_Report_YYYY-MM-DD_HH-mm.html`
- PDF output is suggested as `TLOG_Report_YYYY-MM-DD_HH-mm.pdf` in the report title/print instructions; the final PDF filename is controlled by the browser print dialog.

If the original TLOG filename is safely available, a sanitized base name may be appended, for example:

`TLOG_Report_2026-09-09_07-23_flight-01.html`

## Sharing behavior

### Supported browsers/devices

If `navigator.share` is available:

- prefer sharing the generated HTML file using Web Share Level 2 when `navigator.canShare({files:[...]})` succeeds;
- otherwise share the report title/text only and offer HTML download separately.

### Unsupported browsers

Show a concise message that direct system sharing is not supported in this browser, then provide the HTML download action.

No report is uploaded to a public server in v1, so there is no public share URL and no automatic exposure of flight data.

## Privacy and security

- Report generation is local in the browser from the already-loaded analysis result.
- Do not upload report contents to a third-party PDF service.
- Do not include secrets, API keys, backend tokens, request IDs, or internal debug objects.
- Do not embed the source `.tlog` bytes.
- Preserve only fields intentionally shown in the report.

## Data consistency rules

The report must reuse existing analyzer values and helper outputs rather than implementing parallel telemetry math.

Important examples:

- dBm average must match the analyzer's existing arithmetic-average logic.
- VTX best/worst must match the live VTX matrix logic.
- Engine Load must come from the analyzer's `EFI_STATUS.engine_load` path when available, not `VFR_HUD.throttle`.
- altitude must use the analyzer's normalized altitude values.
- board messages and AI conclusion must use the processed backend output currently displayed to the user.

## Error handling

- Report button is disabled until a successful analysis exists.
- If an optional section has no data, omit it or show `—` where the section remains useful.
- If browser print fails to open, show a readable error and keep HTML export available.
- If share API rejects/cancels, do not treat user cancellation as a report-generation error.
- Export must not clear the current analysis or graph state.

## Compatibility

Target the current supported browser usage first:

- desktop Chrome/Edge
- Android Chrome
- iOS Safari where browser APIs permit

HTML export should work broadly through Blob + object URL download. PDF remains browser-print based in v1 for portability.

## Implementation boundaries

Expected frontend work:

- report menu/button in `index.html`
- report data assembly helper using current analysis state
- standalone HTML template builder
- static report chart renderer
- download helper
- print/PDF helper
- Web Share capability/fallback helper
- print/report CSS

Backend changes are not required for v1 unless implementation discovers a missing value that cannot be obtained from the current analysis response. If that happens, stop and review the API change before expanding scope.

## Testing strategy

Use TDD for implementation.

Minimum automated contracts:

1. report controls only enable after successful analysis;
2. standalone HTML contains the expected header and core summary values;
3. missing telemetry does not produce `undefined`, `null`, or broken sections in output;
4. report reuses existing dBm/VTX/Engine Load values rather than recalculating incompatible values;
5. HTML export creates a valid downloadable Blob/document;
6. print helper opens/prints the generated report without mutating analyzer state;
7. Web Share path is used only when supported, with fallback otherwise;
8. report excludes source TLOG bytes and internal tokens/debug fields;
9. inline JavaScript syntax remains valid;
10. existing broad analyzer regression workflows remain unaffected.

## Acceptance criteria

The feature is acceptable when a user can finish an analysis and, without re-uploading the log:

- save a readable standalone HTML report;
- invoke a print/PDF flow and save a readable PDF;
- share through the system share sheet on supported devices or receive a clear fallback on unsupported browsers;
- print the same report;
- see summary metrics, radio/VTX, critical events, AI conclusion, and available charts;
- receive no fabricated telemetry for absent data;
- retain analyzer consistency for all calculations already implemented elsewhere.

## Deferred from v1

Not included in the first version:

- server-hosted public share links
- password-protected reports
- cloud report history
- editable report templates
- digital signatures
- automatic email/Telegram sending
- embedding the raw TLOG inside the report
- backend-generated PDF files
