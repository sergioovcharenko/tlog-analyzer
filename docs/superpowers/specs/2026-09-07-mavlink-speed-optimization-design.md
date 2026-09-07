# MAVLink speed optimization design

## Goal
Reduce the dominant MAVLink parse/decode time without changing analyzer conclusions, timeline semantics, flight events, or AI facts.

## Rollback
Stable pre-optimization state is preserved at branch `backup-before-mavlink-speed-optimization`, commit `20a7c046dc46d911c3d198d81cb0c31c6492dabf`.

## First optimization
Replace `recv_match(type=needed_messages)` with direct `recv_msg()` and an O(1) local set filter. `recv_msg()` still performs normal pymavlink post-processing for every decoded frame, preserving flight-mode/state side effects. Only analyzer rule dispatch remains filtered to the same message types as before.

## Validation
A contract test requires the direct receive fast path and backend compilation. Existing repository CI remains responsible for broader regression coverage before merge. Runtime performance must be measured on the same ~19.88 MB TLOG after deployment; this change is not considered a performance success until the production timing confirms improvement.
