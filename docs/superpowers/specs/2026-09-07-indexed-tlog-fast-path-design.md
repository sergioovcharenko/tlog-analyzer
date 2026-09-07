# Indexed TLOG fast path design

## Goal
Reduce the dominant pymavlink decode time without changing critical flight-event analysis.

## Rollback
Stable pre-experiment state is preserved in branch `backup-before-raw-tlog-scanner` from the current stable `main` before this experiment.

## First scope
Optimize only `EFI_STATUS`. In the current analyzer it supplies the current `engine_load` value and does not generate ARM/DISARM, mode, radio, ESC, STATUSTEXT, LAND or crash events.

## Approach
Use pymavlink's existing mmap TLOG index (`mavmmaplog.offsets`) instead of writing a new raw parser. Build a 5 Hz sampled EFI_STATUS time series by selecting the last EFI_STATUS offset in each 200 ms bucket, decoding only those selected frames. Remove EFI_STATUS from the main `recv_match(type=...)` pass only when indexed sampling is available; otherwise fall back automatically to the existing full EFI_STATUS path.

During the normal chronological pass, advance through the prebuilt EFI series by timestamp and update `curr_engine_load` before timeline snapshots are created. All other MAVLink types and all existing rules remain unchanged.

## Safety constraints
- Critical messages are never sampled: HEARTBEAT, STATUSTEXT, RADIO/RADIO_STATUS, ESC telemetry, SYS_STATUS, RC_CHANNELS, GLOBAL/LOCAL position and LAND-related data stay on the existing path.
- Fallback to current behavior if mmap indexing is unavailable or sampling fails.
- Keep existing performance profiling and add counts for raw EFI_STATUS frames versus sampled/decoded frames.
- Runtime success is judged on the same 19.88 MB TLOG. Baseline: recv_match/decode 41.83 s, MAVLink/rules 53.99 s, backend 55.47 s.
- If output is wrong or runtime is not improved, revert to `backup-before-raw-tlog-scanner`.

## Success criterion
Meaningful improvement in backend decode time with unchanged critical findings and no missing engine-load series. Target for this first experiment: at least ~5 seconds faster backend on the 19.88 MB reference TLOG; larger gains are preferred.