# HYP-TVER-XAUUSD-M5-001 — Independent Pre-run Review

Date: 2026-08-09  
Reviewer: read-only sub-agent `t2_campaign_audit`  
Scope: preregistration, analyzer, tests, package README and de-duplication against VCEX/ECRS/ASRS/ARUC/TFCVD. The reviewer did not open the Parquet, run the analyzer or modify files.

## First pass: FAIL

The first pass found two fatal pre-run blockers:

1. Rolling RV10/ATR14 means could remain finite after an invalid prior constituent because feature usability validated the current bar but did not require every exact lookback input to be valid. Null symbol/timeframe rows could also pass the `dropna().unique()` checks.
2. The unconsumed registry flag was not race-safe or crash-durable. Two processes could pass it concurrently and output writes could replace evidence.

## Repairs

- RV10 now requires all ten exact prior tick-volume inputs to be finite and positive.
- ATR14 now requires all fourteen exact prior TR inputs to be finite and positive; every TR input additionally requires valid geometry for its bar and its prior-close bar. The boundary tests cover `t-10`/`t-1` for volume and `t-15`/`t-1` for ATR inputs.
- Symbol and timeframe checks now use fail-closed `eq(...).all()` semantics.
- Execution creates an exclusive `attempt_started.json` with `open("xb")`, flush and `fsync` before Parquet hashing or reading. Any existing start/output artifact forbids the same-ID retry; a crash leaves the claim durable, and a successful attempt writes a terminal receipt.
- The reader uses PyArrow predicates so only `2018 <= time_utc < 2023` is materialized, followed by an explicit out-of-window rejection.
- The same authorized attempt runs a second in-memory analysis and requires byte-identical canonical report and ledger.

## Final pass: PASS

No fatal pre-run blocker remains.

- Analyzer SHA256: `DDF4EC4C9BBC93DFF461546BCE2A5817516560408D4246A4F23BCABBAE3B8D6C`
- Test SHA256: `E405358D6FC28F75A86E6D384B22C82D5761319D199068BD0E51C728C4F7E88A`
- Local main-agent tests: `14 passed`
- Reviewer test/data execution: none; static review only

Causality passes: RV10 and ATR14 exclude the event bar; only the next row's timestamp is consulted, never its prices. Calendar/year cadence arithmetic and inclusive gate boundaries are correct. Manifest, data, preregistration, registry authority and analyzer self-hash bindings are fail-closed.

De-duplication passes. The exact native-M5 RV10/high-effort, prior-ATR14/low-progress, single-bar wick-rejection decision surface is materially distinct from VCEX volume-clock exhaustion, ECRS compression breakout, ASRS pivot sweep/retest, ARUC signed same-slot activity-response continuation and TFCVD real-tick polarity.

Final authorization recommendation: exactly one outcome-blind source/cadence attempt; no economics, MT5/MQL5 build, validation, holdout or live authority.

