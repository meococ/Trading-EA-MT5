# HYP-VRAS-EURUSD-M5-011 — Stage-0 Readout

Verdict: **`PARK_STAGE0_INDICATOR_PARITY_FAIL`**

The one authorized outcome-blind probe stopped before event counts. On the
first failing parity case (`2019-02-04 03:10:00` server), exact HYP008 telemetry
reported VWAP48 `1.14555`, while the frozen reconstruction correctly returned
non-finite under HYP011's own partial-bucket rule.

The recent observed history contains a three-minute Friday close bucket at
`2019-02-01 23:55` and a three-minute Monday open bucket at
`2019-02-04 00:00`. MT5 `CopyRates` treats these as actual M5 broker bars;
HYP011 required exactly five M1 offsets and poisoned VWAP48 after a partial
bucket. The two data contracts therefore do not match.

This is an engineering/data-contract failure, not evidence that the
first-passage mechanism wins or loses. However, parity was a necessary frozen
gate. No event count, cadence, Jaccard, economic outcome, MQL5 source, compile
or Model-0 run was opened. HYP011 is parked and may not be repaired/rerun after
the failed gate.

The VRAS historical successor remains closed under the current price-only
research budget. Reopening requires a materially new information/data contract
approved as a new lane, not another partial-bar or threshold rescue.
