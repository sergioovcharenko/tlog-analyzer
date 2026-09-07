# MAVLink speed optimization plan

1. Preserve stable main in a rollback branch.
2. Add a RED contract requiring direct `recv_msg()` + set filtering.
3. Implement only the receive/filter fast path; do not alter telemetry rules.
4. Run contract and Python compile checks.
5. Open PR and run existing regression workflows.
6. Merge only after relevant checks pass.
7. Benchmark the same ~19.88 MB TLOG on Render and compare `recv_msg/decode`, `MAVLink/правила`, and backend total against the baseline 41.83 s / 53.99 s / 55.47 s.
8. If there is no meaningful gain or output changes, revert to `backup-before-mavlink-speed-optimization` and investigate a raw TLOG frame scanner instead.
