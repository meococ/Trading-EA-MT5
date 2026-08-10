# HYP-TRIX-XAUUSD-M5-001 — Source Result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_TRIX18_ZERO_CROSS`

The sole outcome-blind source attempt completed with deterministic replay. The exact TRIX-18 M5 zero-line transition is too frequent for the frozen 2–5 events/week operating envelope.

## Reconciled funnel

- source rows: 1,233,571
- design rows: 351,303
- feature-usable rows: 351,303 (`100%`, PASS)
- raw events: 7,193
- executable events: 7,166
- exact-next gaps consumed: 27
- exact-next coverage: `99.624635%` (PASS)
- LONG / SHORT: 3,585 / 3,581 (PASS)
- pooled cadence: `27.470975/week` (FAIL)
- annual cadence: `26.2164–28.6694/week` (all FAIL)
- max-year share: `20.9182%` (PASS)
- direction conflicts: 0 (PASS)

Only pooled cadence and every-year cadence failed. Minimum rows, feature coverage, exact-next coverage, event count, direction balance, year concentration and zero-conflict gates passed.

This is source-feasibility evidence only. No post-event OHLC, return, simulated trade, PnL, profit factor, validation or holdout value was read or computed. It does not prove economic no-edge.

The exact ID is terminal. No TRIX threshold, signal line, cooldown, filter, alternate period/timeframe or native-iTriX parity rescue is authorized.

