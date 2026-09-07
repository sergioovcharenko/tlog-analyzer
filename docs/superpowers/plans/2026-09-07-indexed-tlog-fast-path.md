# Indexed TLOG Fast Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce backend MAVLink decode time by removing most EFI_STATUS frames from the main pymavlink decode pass while preserving critical analyzer behavior and engine-load visibility.

**Architecture:** Add a small indexed TLOG sampler that reuses pymavlink `mavmmaplog.offsets` to choose at most one EFI_STATUS frame per 200 ms bucket and decode only those selected frames. The main analyzer uses the sampled time series only when indexing succeeds; otherwise it automatically keeps the current full EFI_STATUS `recv_match` behavior.

**Tech Stack:** Python 3.11, FastAPI, pymavlink, unittest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-07-indexed-tlog-fast-path-design.md`

## Global Constraints

- Rollback branch: `backup-before-raw-tlog-scanner`.
- Optimize only EFI_STATUS in this experiment.
- 200 ms sampling interval (5 Hz maximum decoded EFI_STATUS rate).
- HEARTBEAT, STATUSTEXT, RADIO/RADIO_STATUS, ESC, SYS_STATUS, RC_CHANNELS and position messages remain on the existing full path.
- Fallback to the existing full EFI_STATUS path when mmap indexing or sampling is unavailable.
- Keep current performance profiling and expose indexed input/decoded counts.
- Runtime benchmark uses the same 19.88 MB TLOG; baseline backend total is 55.47 s and recv_match/decode is 41.83 s.

---

### Task 1: Indexed EFI selector

**Files:**
- Create: `backend/indexed_tlog.py`
- Create: `tests/test_indexed_tlog.py`

**Interfaces:**
- Produces: `select_last_offsets_per_bucket(data_map, offsets, interval_s=0.2) -> list[int]`
- Produces: `build_indexed_numeric_series(filename, message_name, value_attr, interval_s=0.2) -> dict | None`

- [ ] **Step 1: Write the failing unit tests**

Test that synthetic big-endian TLOG timestamps select the last offset in each 200 ms bucket and that invalid/empty index input returns an empty selection.

- [ ] **Step 2: Run test to verify RED**

Run: `python -m unittest tests.test_indexed_tlog -v`
Expected: FAIL because `backend.indexed_tlog` does not exist.

- [ ] **Step 3: Implement the indexed selector and sampled numeric-series builder**

The builder must use a separate read-only pymavlink connection, require `offsets`, `name_to_id`, and `data_map`, seek directly to selected offsets, decode only selected frames, collect `(timestamp, numeric_value)` pairs, and always close the temporary connection.

- [ ] **Step 4: Run unit tests and compile**

Run: `python -m unittest tests.test_indexed_tlog -v && python -m py_compile backend/indexed_tlog.py`
Expected: PASS.

### Task 2: Analyzer integration with fallback

**Files:**
- Modify: `backend/main.py`
- Create: `tests/test_indexed_tlog_integration_contract.py`

**Interfaces:**
- Consumes: `build_indexed_numeric_series(...)`
- Produces: existing `/analyze` response plus `performance.efi_indexed_input_count`, `performance.efi_indexed_decoded_count`, and `performance.efi_indexed_enabled`.

- [ ] **Step 1: Write the failing integration contract**

Require the main analyzer to call `build_indexed_numeric_series(temp.name, "EFI_STATUS", "engine_load", interval_s=0.2)`, exclude EFI_STATUS from `needed_messages` only when indexed data is available, and retain fallback inclusion otherwise.

- [ ] **Step 2: Run contract to verify RED**

Run: `python -m unittest tests.test_indexed_tlog_integration_contract -v`
Expected: FAIL because integration markers are absent.

- [ ] **Step 3: Integrate sampled EFI series**

Build the series after opening the main MAVLink connection. Before each timeline snapshot/update, advance the series through timestamps `<= current_timestamp` and clamp engine load to `0..100`. If the builder returns `None`, append `EFI_STATUS` to `needed_messages` and keep the original handler active.

- [ ] **Step 4: Add performance counters**

Expose whether indexed mode was enabled plus raw input count and decoded sampled count. Add a short `⚡ EFI_STATUS індекс:` diagnostic line to the existing technical findings block.

- [ ] **Step 5: Run regression checks**

Run unit tests, integration contract, backend compile, existing AI reconstruction tests, graph contract, LAND summary contract, board-message contract, and performance-profile contract.
Expected: all PASS.

### Task 3: Production benchmark and accept/revert decision

**Files:**
- No additional production files unless a bug is found.

- [ ] **Step 1: Open PR after CI is green**

Document the rollback branch and baseline timing.

- [ ] **Step 2: Merge only after repository CI is green**

Render must deploy the resulting main commit.

- [ ] **Step 3: Re-run the same 19.88 MB TLOG**

Compare `recv_match/decode`, `MAVLink/правила`, `backend разом`, and the new EFI indexed input/decoded counts.

- [ ] **Step 4: Accept or revert**

Keep the optimization only if critical findings remain correct and backend time improves meaningfully. Otherwise restore from `backup-before-raw-tlog-scanner`.