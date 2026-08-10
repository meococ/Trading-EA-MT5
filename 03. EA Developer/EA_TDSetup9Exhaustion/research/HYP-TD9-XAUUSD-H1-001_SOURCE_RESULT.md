# HYP-TD9-XAUUSD-H1-001 - Source Result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_TD9_PERFECTED_SETUP`

The sole deterministic outcome-blind source attempt completed. Exact perfected TD Setup 9 on native XAUUSD H1 meets the frozen event-count, cadence, direction-balance and concentration envelope, but fails the exact-next execution-coverage gate.

- source/design/usable rows: 107,679 / 29,461 / 29,461 (`100%`, PASS)
- raw/executable/gap events: 555 / 528 / 27
- exact-next coverage: `95.135135%` (FAIL; required at least `97%`)
- LONG / SHORT: 233 / 295 (PASS)
- pooled cadence: `2.024096/week` (PASS)
- annual cadence: `1.7596-2.3973/week` (all PASS)
- max-year share: `23.6742%` (PASS)
- conflicts: 0 (PASS)

Only raw-event exact-next coverage failed. No post-event OHLC, returns, simulated trades, PnL, PF, validation or holdout value was read. This is not an economic no-edge conclusion.

The exact ID is terminal. No relaxed next-bar rule, queued execution, delayed perfection, Countdown 13, TDST, timeframe change or filter rescue is authorized.
