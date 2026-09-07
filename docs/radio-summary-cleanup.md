# Radio summary cleanup

- Dashboard card `RC RSSI` is renamed to `MIN RSSI`; the existing backend value is already the minimum observed RSSI over the TLOG.
- `RADIO dBm` shows the worst observed dBm as the primary value and the arithmetic mean of all valid RADIO/RADIO_STATUS dBm samples as secondary text.
- `-128 dBm` is intentionally included in that average; absent/zero values are not counted.
- Redundant VTX summary cards for band, channel, CH7 PWM and CH8 PWM are removed. The underlying telemetry remains available in RC/TX16 and Timeline data.
- Backup branch: `backup-before-radio-summary-cleanup`.
