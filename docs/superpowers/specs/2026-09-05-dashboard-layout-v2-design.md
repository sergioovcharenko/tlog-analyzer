# TLOG Analyzer Dashboard Layout v2 — Design Spec

Date: 2026-09-05
Branch: `feature/dashboard-layout-v2`

## Goal

Reorganize the existing graph/attitude/MAVLink screen into a clearer professional workstation layout based on the approved second visual concept, while preserving the current working artificial horizon implementation and all current analysis behavior.

## Core decision

Use the second mockup as the structural reference, but keep the current artificial horizon exactly as the source component. We are changing layout, grouping, responsive behavior, theme presentation, and discoverability — not changing telemetry calculations, backend output, flight analysis logic, or the horizon rendering logic.

## Desktop layout

### 1. Top summary zone
A compact horizontal summary row sits above the main workspace and shows the most important values already available in the current result:
- time
- flight mode
- altitude
- distance
- azimuth/heading
- battery voltage
- current
- RSSI
- dBm
- FC/ESC temperature when available

This row is compact and does not duplicate large detail cards from the right panel.

### 2. Main workspace
Use a two-column CSS grid on desktop:
- left: approximately 72–75% width for the graph workspace
- right: approximately 25–28% width for the docked detail panel

The graph remains the dominant element and keeps current zoom, cursor, selected metric, synchronization, and dynamic MAVLink series behavior.

### 3. Right docked panel
The right column becomes a tabbed panel with these tabs:
- `Авіагоризонт`
- `Повідомлення`
- `TX16`
- `Дані`

Only one tab is visible at a time to reduce clutter.

#### Авіагоризонт tab
Reuse the existing current artificial horizon and its current telemetry readouts. Do not replace the horizon drawing, styling logic, attitude math, current values, or synchronization behavior.

#### Повідомлення tab
Show board messages in a full-height scrollable panel with existing severity coloring. Add filter controls only if they can be derived from existing message data without changing backend contracts.

#### TX16 tab
Move the existing TX16/RC presentation into the right dock without changing its data or interpretation.

#### Дані tab
Show compact auxiliary values that are useful during graph inspection but do not need to be always visible.

## Graph workspace

Keep the current graph as the main visual. Improve organization around it:
- selected series appear as compact colored chips under or above the graph
- each chip can hide/remove that series using the current graph state
- graph controls stay near the graph header
- no duplicate graph parsing or backend behavior changes are part of this redesign

The graph must remain synchronized with the current horizon, cursor, mode, timeline and message behavior already implemented.

## MAVLink selector zone

Place the dynamic MAVLink selector below the graph/right-panel workspace.

Structure:
1. section title and collapse/expand control
2. search field
3. quick preset buttons such as `Altitude`, `Power`, `Radio`, `Attitude`, `ESC`
4. category groups/cards for message families
5. field checkboxes inside groups

The existing dynamic MAVLink field source remains unchanged. This is a presentation reorganization only.

On desktop, the section may be expanded by default if there is enough vertical space; the user can collapse it. The selected graph series remain visible as chips even when the full selector is collapsed.

## Theme switcher

Add a two-state theme control in the graph dashboard header using the approved labels:
- `● Темна`
- `○ Світла`

Requirements:
- dark remains the default when there is no saved preference;
- the active state is visually highlighted;
- the selected theme is persisted in `localStorage` under key `tlog-theme` with values `dark` or `light`;
- switching themes must not reload the page or trigger backend requests;
- the theme applies to the entire graph dashboard: page/background, cards, tabs, graph canvas/container, axes/grid/tooltip chrome where controlled by frontend styling, MAVLink selector, board messages, TX16 dock, buttons and inputs;
- status/series semantics remain consistent: red/yellow/green/cyan series/status meanings are preserved;
- the current artificial horizon drawing itself is not recolored or rewritten by the theme feature; only its surrounding panel chrome follows the selected theme.

## Responsive behavior

### Desktop: >= 1200 px
- two-column workspace
- graph left, tabbed detail dock right
- MAVLink selector below
- no whole-page horizontal scrolling

### Tablet: 768–1199 px
- graph becomes full width
- right dock moves below graph as a horizontal/tabbed section
- MAVLink selector remains below
- internal graph/tables may use local horizontal scrolling only where unavoidable

### Phone: < 768 px
Use one-column flow. The major work areas become touch-friendly sections/tabs:
- `Огляд`
- `Графік`
- `Авіагоризонт`
- `Повідомлення`

The current artificial horizon is scaled to available width but its implementation remains unchanged.

Touch targets should be approximately 44–48 px minimum where practical. The page itself must not require horizontal scrolling.

## Preserve existing behavior

The redesign must not alter:
- backend API contracts
- TLOG parsing logic
- AI conclusion logic
- timeline analysis
- map calculations
- RPM/ESC calculations
- TX16 interpretation
- graph data values
- dynamic MAVLink loading/prefetch logic
- current artificial horizon math/rendering

## Implementation strategy

Prefer a low-risk UI refactor:
- keep existing element IDs and data hooks wherever possible
- add layout wrapper classes around existing components
- add tab/theme state in frontend JavaScript only
- preserve existing event handlers and data objects
- avoid rewriting graph/horizon implementations

If a current block must move, relocate its DOM container rather than duplicate it.

## Tests / acceptance criteria

1. Existing backend and frontend regression workflows remain green.
2. Existing dynamic MAVLink graph tests remain green.
3. Existing attitude/horizon regression tests remain green.
4. Existing TX16 regression tests remain green.
5. Add responsive/layout/theme contract tests for the new wrappers/tabs.
6. Desktop at 1366/1440/1920 px: graph is visually dominant and no page-level horizontal scroll is introduced.
7. Tablet at 768/1024 px: graph and detail panel stack cleanly.
8. Phone at 360/390/430 px: one-column view with no page-level horizontal overflow.
9. Current artificial horizon visual/behavior remains functionally unchanged.
10. Switching right-side tabs must not trigger new backend requests.
11. Selected graph signals remain visible/controllable after the MAVLink selector is collapsed.
12. Theme control displays exactly `● Темна` and `○ Світла`, changes the frontend theme without reload/backend requests, and restores the saved choice after reload.

## Non-goals for this version

- draggable/dockable free-form panels
- user-saved custom desktop layouts
- backend changes
- new telemetry calculations
- replacement of the current artificial horizon
- redesign of the main analysis page outside this graph workspace

## Rollback

The current stable state is preserved on branch `backup-before-dashboard-layout-v2` before implementation begins.
