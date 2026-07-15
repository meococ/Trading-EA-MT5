# Offline probes — Greenfield calendar/liquidity

Receipt SHA256: `93ADBDC420A196C70D8A6340C16106FC71C70C3916616911D508BC51F2655273`
Generated: 2026-07-15T01:45:29.488170Z
A priori cost: +$12 (x1/x1.5/x2); cost freeze GAP.

## HYP-FX3-H4-TURNMONTH-LIQ-BOOK-001

- verdict: **KILLED_AT_OFFLINE_PROBE** (pf_fail, stress_fail)
- N=599 PF=0.6998 tpw=2.2975
- x1.5 PF=0.6466 x2 PF=0.6299
- detail: `{"by_reason": {"eod": 2, "sl": 279, "time": 271, "tp": 47}, "by_sym": {"EURUSD": 227, "GBPUSD": 230, "USDJPY": 142}, "n_signals": 599}`

## HYP-FX3-H1-WEEKEND-GAP-FADE-001

- verdict: **KILLED_AT_OFFLINE_PROBE** (n_fail, cadence_fail)
- N=47 PF=4.7834 tpw=0.1803
- x1.5 PF=4.4948 x2 PF=4.4031
- detail: `{"by_reason": {"sl": 11, "tp": 36}, "by_sym": {"EURUSD": 18, "GBPUSD": 14, "USDJPY": 15}, "median_gap_atr": 0.5219, "n_kept": 47, "n_raw": 49}`

