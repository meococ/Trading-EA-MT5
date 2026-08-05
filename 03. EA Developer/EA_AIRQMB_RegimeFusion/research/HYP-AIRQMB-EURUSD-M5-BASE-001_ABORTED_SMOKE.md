# AIRQMB EURUSD BASE-001 — Aborted Engineering Smoke

- Launch start: `2026-08-05T18:07:35Z`
- Ordered cell: `EURUSD M5`, `2023.01.02–2024.12.31`, Model 0 real ticks
- Stop decision: after approximately 17 minutes, before report generation and before any performance outcome was read
- Artifacts: AlphaFactory stdout/stderr and the incomplete `AlphaTester/20260806_010735` launch directory
- Economic trials consumed: `0` (no report, no metrics, no selection)

## Engineering findings

1. MetaEditor rebuilt the same source as `0 errors, 0 warnings`, but the EX5 hash differed from the prior compile. EX5 is therefore retained in each run snapshot but removed as a long-lived prereg identity key; source, contract and indicator source/runtime hashes remain authoritative.
2. The EA performed UTC conversion, risk-lock refresh and position scans on every tick although all decisions are closed-bar M5 decisions. This created avoidable Model-0 overhead.
3. The successor moves those operations behind the new-M5-bar gate. Broker/tester SL and TP remain tick-accurate.
4. A Model-4 engineering screen is introduced before expensive Model-0 confirmation. Model 4 may reject a candidate but can never authorize economic-valid or promotion claims.

`HYP-AIRQMB-EURUSD-M5-BASE-001` is superseded without an economic verdict. The remaining unlaunched BASE-001 cells are also superseded before execution so all nine cells retain one consistent source and protocol.

