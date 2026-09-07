# Indexed EFI benchmark gate

Reference TLOG: 19.88 MB.

Baseline before this experiment:
- recv_match/decode: 41.83 s
- message rules: 7.98 s
- other parse: 4.19 s
- MAVLink/rules total: 53.99 s
- backend total: 55.47 s
- EFI_STATUS messages: 46,133

Acceptance after Render deploy:
- critical analyzer findings remain present and consistent;
- EFI_STATUS indexed diagnostic reports enabled mode and a decoded count materially below 46,133;
- backend time improves meaningfully (target at least ~5 s faster for this first experiment).

Rollback if acceptance fails: restore `backup-before-raw-tlog-scanner`.
