# Frozen preregistration - HYP-FIXCLK-EURUSD-M5-001

Authority: `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE`. No trades or economic metrics.

Run EURUSD M5 Model 0 from 2018-01-01 to 2019-01-01. Detect each gap of at least 30 hours. For the three weekly opens following Sundays where US and UK daylight-saving regimes differ in 2018, classify the broker convention:

- all three open Monday 00:00-00:10 server: `PASS / US_DST_NY_CLOSE`;
- all three open Sunday 23:00-23:10 server: `PASS / EU_DST`;
- any mixed/other result or fewer than three observations: `DATA_FRONTIER_BLOCKED_TIMEZONE`.

This result may freeze the V11 fix-hour calendar only. It cannot authorize trading performance.

