# 2026-09-12 - HYP-HD-XAU-M15-001 control screen: KILL

## Verdict

`HYP-HD-XAU-M15-001` (EA_HourDrift, XAUUSD M15, next-hour seasonal mean drift)
killed at Model 0, registry row updated (screened to killed, validator green).
Third hypothesis through the complete governed chain; first to PASS cadence.

Run `20260912_031529` (governed, portable isolate, MetaQuotes-Demo):

| Metric | Value |
|---|---|
| Window | all-available; history 2004.06.11 to 2026.09.10 |
| Trades | 34,127 (~11.5/week, in 10-40 band - PASS) |
| Report PF | 0.94; Net -7,246 USD; Max DD 82.5%; WR 40.2% |
| History Quality | 98% |
| Cost-bound PF | 0.52 @x1.0 / 0.40 @x1.5 / 0.31 @x2.0 |
| Monte Carlo p95 DD | 80.2% (limit 20) |
| Robustness pass rate | 14.3% |
| Overnight/weekend | FAIL - 14 overnight, 10 weekend-crossing |
| Unified verdict | REVIEW - 9 FAIL / 2 BLOCKED / 3 PASS of 14 gates |

Intraday seasonal drift has no exploitable edge on XAUUSD M15 at MQ-Demo
cost levels; the 0.10-ATR mean threshold does not clear ~4.2-pip spread +
slippage. No post-hoc rescue.

## Cell notes

- Cadence gate CAN pass on this fleet (11.5/wk) - the band is achievable.
- 10 weekend-crossing trades despite Friday flatten 20:00 - the EA holds
  positions that would cross weekend if Friday session-end exits slip;
  worth auditing ShouldFlatten vs actual close times if this mechanism is
  ever revived. Moot for a killed row.
- Same 2 structural BLOCKED gates (slippage_summary WARN, artifact freshness)
  - not strategy-material.
