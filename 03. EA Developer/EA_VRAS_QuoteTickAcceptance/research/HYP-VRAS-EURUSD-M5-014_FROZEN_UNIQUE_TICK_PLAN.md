# HYP-VRAS-EURUSD-M5-014 — Frozen normalized-tick uniqueness successor

## Identity and failure radius

- Fresh administrative ID: `HYP-VRAS-EURUSD-M5-014`.
- Parent HYP-013 is parked after its sole 120-second read-only feed smoke.
- HYP-013 proved UTC normalization (+10,800-second broker offset) but exposed a
  coordinate bug in the Python collector: raw broker milliseconds were compared
  with the prior normalized UTC milliseconds, so an unchanged quote was emitted
  again on every poll.
- The parent opened no EA arm, acceptance, trade, PnL, return or economic metric.
- All HYP-012/HYP-013 arm and acceptance thresholds remain byte-for-byte in
  meaning. No filter, signal, spread, imbalance, age or outcome rule changes.

## Sole implementation delta

For each current broker quote:

1. normalize `raw_time_msc` to `utc_time_msc` first;
2. compare only `utc_time_msc > last_seen_utc_msc`;
3. write the quote and update `last_seen_utc_msc` only after that comparison;
4. copied range ticks use the same normalized coordinate;
5. the bundle validator rejects equality as well as time reversal;
6. account history remains skipped and every order surface remains absent.

## Frozen engineering gates

1. Regression fixture proves a repeated raw quote produces exactly one row.
2. Duplicate `time_msc` rows fail bundle validation as not strictly monotonic.
3. HYP-014 source/reference identity tests, all frozen FSM tests, compile 0/0,
   exact-source non-repaint, zero trade APIs and zero `FILE_COMMON` matches pass.
4. Exactly one fresh 120-second EURUSD quote-only smoke is authorized on exact
   `FivePercentOnline-Real`; no cron, continuation or account-history access.
5. That smoke must reconcile manifest hashes/row counts, report broker offset,
   have strictly increasing unique normalized quote timestamps, no future-clock
   blocker, zero orders, zero positions and `live_trading_authorized=false`.

## Outcome boundary

The smoke validates only feed plumbing. It cannot establish entry quality,
profit factor, win rate, expectancy, stop geometry or R:R. HYP-014 remains
`promotion_eligible=false` and `performance_metrics_authorized=false`.
Historical 2018-present OHLC/tick reconstruction is forbidden because it does
not contain the original chronological bid/ask update stream required by this
causal confirmation mechanism. A later economic matched pair requires a fresh
preregistration after a sufficiently long forward corpus exists.
