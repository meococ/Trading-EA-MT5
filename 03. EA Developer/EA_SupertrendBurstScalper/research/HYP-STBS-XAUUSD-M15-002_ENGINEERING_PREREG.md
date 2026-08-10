# HYP-STBS-XAUUSD-M15-002 — Governance-correct engineering audit preregistration

Frozen at system UTC `2026-08-09T02:38:28Z`, before any HYP002 packet or MT5 attempt.

## Scope and ancestry

- Governance hypothesis: `HYP-STBS-XAUUSD-M15-002`.
- Parent market/indicator evidence: terminal `HYP-ST-XAUUSD-H1-012`.
- Informed failure: `HYP-STBS-XAUUSD-M15-001` packet chronology only. HYP001 never opened AlphaFactory/MT5/economics and is not retried.
- Frozen implementation identity: the unchanged hard-audit MQL5 source whose internal journal hypothesis remains `HYP-STBS-XAUUSD-M15-001`, SHA `B7D0092655A602C6619DD277848168F2B926C4F5ADB1311F4DB303AAC771757D`.

The dual identity is intentional and must be explicit everywhere: HYP002 is the fresh outer authority/run identity; HYP001 is only the already-reviewed inner implementation/journal identity. No source, formula, signal, ATR or geometry logic changes are authorized by this revision.

## Frozen engineering mapping

Use native XAUUSD M15, Model 0, preload `2005.01.01` through `2023.01.01`; score and emit only 2018–2022 design events. The source reconstructs the exact H1 standard Supertrend10x3 state from inception, consumes closed H1 flips only when the immediate H1 successor and native M15 decision open are exact, reads ATR14 from the prior completed decision-time M15 bar, and performs a pure no-send geometry readiness check. Expected parent population is raw 690, executable 683, gaps 7, LONG 339, SHORT 344, ATR-ready 683 and geometry-ready 683.

The only Alpha override is `InpAuditOnly=true`. Telemetry profile is `none` and tier `off`. Any order/deal/trade request, fatal journal record, population drift, wrong-side geometry, missing ATR, malformed zero-trade report, run-snapshot mismatch, HQ `<=97`, or incomplete series proof fails.

## Temporal and one-shot authority

- Availability-as-of is frozen to `2026-08-09T02:38:00Z`, which is not later than preregistration.
- Packet attempt: exactly one `STBS002-PACKET-BUILD-001`, durable claim before bound reads, success/failure terminal, no retry.
- MT5 attempt: exactly one `STBS002-MT5-AUDIT-001`, durable claim before receipt/oracle reads and before AlphaFactory, success/failure terminal, no retry.
- The first fresh probe row may authorize packet build only. A second independently reviewed screened row is required to authorize MT5.

This hypothesis is engineering correctness only. Performance metrics, outcome prices, post-event OHLC, economics, optimization, validation, holdout, promotion, paper and live trading remain false. A PASS may authorize a separately preregistered economic child; it cannot claim edge or PF.
