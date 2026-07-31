# EA_VRAS_PathConfirmedTrend

Diagnostic-only matched-pair implementation for `HYP-VRAS-EURUSD-M5-004`.

Terminal verdict: `KILL_PATH_CONFIRMATION_NO_INDEPENDENT_EDGE`. The only
authorized pair has been consumed; this package has no rerun, rescue,
optimization, promotion, paper, or live authority.

## Frozen change

The Range branch remains immediate. The Trend branch is the sole treatment:

- `CONTROL_IMMEDIATE_TREND`: opens an eligible raw Trend setup immediately.
- `CHALLENGER_PATH_CONFIRM`: arms the raw setup, then requires the exactly next
  closed M5 bar to break the setup extreme while remaining on the correct side
  of session VWAP, the frozen-anchor AVWAP, and the last-closed M15 session VWAP.
- Any failed or late confirmation is discarded permanently.
- The raw setup stop is frozen. A confirmed order recalculates its 1.8R target
  from the actual delayed entry quote to that frozen stop.

The run window is `2023-01-03` through `2026-06-30` on `EURUSD M5`, Model 0.
Both arms disable the static news guard because the bundled calendar ends in
2022; therefore all economics remain diagnostic and promotion-ineligible.

## Evidence boundary

- Preregistered contract and probe plan live in `research/`.
- Python and source-contract tests live in `tests/`.
- Runtime telemetry uses AlphaFactory `lifecycle-v3` plus path counters in
  `RunMeta` and explicit arm/pass/reject events in decision telemetry.
- This package cannot be used for optimization, promotion, or live trading.

## Terminal result

- Control `20260722_155551`: 261 trades, PF 0.8927, net -$3,429.27.
- Challenger `20260722_155635`: 252 trades, PF 0.8996, net -$2,677.24,
  1.385 trades per elapsed week, max DD 4.49%.
- Relative lift: PF +0.0069, mean realized R +0.0065R, stop-share -8.58pp;
  all three frozen relative gates failed.
- Delivery packet passes evidence validation with verdict `KILLED`.

Canonical readout: `research/HYP-VRAS-EURUSD-M5-004_READOUT.md`.
