# HYP-XJRR-XAUUSD-M5-001 — source-evidence addendum

Status: `FROZEN_BEFORE_XJRR_SOURCE_ATTEMPT_002`

The first source scan produced a non-authoritative exploratory report because
its analyzer did not fail-close the `time_server` axis and its outputs were
overwriteable. The observed count does not authorize MQL5, economics or a
strategy change.

`XJRR-SOURCE-002` preserves every market rule from the original frozen prereg:
the two symbols, M5 timeframe, 288-return no-intercept beta, residual sigma,
two-sigma re-entry, first raw event per server date, 12-bar consumption lock,
exact-next rule, Friday 20:00 UTC availability boundary and every source gate.
Only the evidence contract changes:

- each source must have strictly increasing `source_epoch` and `time_server`;
- `time_server` must equal the naive timestamp represented by `source_epoch`;
- exact joined epochs must have identical XAUUSD and USDJPY server clocks;
- the attempt root is exclusive and claimed before source/input hashing;
- report and ledger are exclusive writes, replayed byte-identically in memory;
- source, prereg, addendum, analyzer and test hashes are rechecked after the
  scan and bound into a receipt and terminal.

The first report and ledger at the research-directory root remain disclosed as
non-authoritative diagnostics. Only a COMPLETE `XJRR-SOURCE-002` chain may
authorize an implementation review. The daily quota remains an opportunity
upper bound; completed-trade cadence must still be measured by the baseline.
