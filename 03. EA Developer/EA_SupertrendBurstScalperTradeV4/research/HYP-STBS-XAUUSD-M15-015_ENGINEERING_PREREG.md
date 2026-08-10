# HYP-STBS-XAUUSD-M15-015 - outer-only current-spread invocation revision

Status: FROZEN BEFORE ANY HYP015 ALPHA, MT5 OR SOURCE-DATA ACCESS

## Failure radius and lineage

- Parent: terminal `HYP-STBS-XAUUSD-M15-014`, raw row SHA256 `72B25C6BEC0E562D255020F3E11B8B86BDE8B8995BFBC639A3988BE395CAA862`.
- Parent failure: literal `-Spread current` was rejected before compile, MT5 and run creation. HYP014 opened no report, source data, orders, deals, returns or economics.
- HYP015 is a harness-only child. No MQL source, EX5, signal, Supertrend, ATR, margin, stop, target, hold, risk or acceptance gate changes.

## Dual identity contract

- Outer authority/task/receipt/run-manifest hypothesis: `HYP-STBS-XAUUSD-M15-015`.
- Outer attempt: `STBS015-MODEL0-AUDIT-001`, limit one, no retry.
- EA/source: unchanged `EA_SupertrendBurstScalperTradeV4`, SHA256 `028D0AADB49856F58B167390E93300CD12AD90993F13FE7D5012DE6FFB8FC726`.
- Inner MQL override/journal identity: `HYP-STBS-XAUUSD-M15-014`, magic `5604114`.
- Exact overrides remain `InpAuditOnly=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-014;InpMagic=5604114;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpStopoutHeadroomFactor=1.25;InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_FSM_V4_MARGIN_SAFE`.

## Sole invocation revision

Run XAUUSD M15, 2005.01.01 through 2023.01.01, Model 0, execution mode 0, fixed delay 0, timeout 900, deposit 10000, leverage 100, control, telemetry profile none/off. The Alpha CLI must omit `-Spread` entirely. Task/receipt/manifest semantic spread remains `current`.

All HYP014 zero-trade gates remain exact: history quality >97, base data fingerprint `077437E0038B40FEDB8AC611CAFE410B2FF8D0A90A742F0C52336F728D8C0BF4`, raw 690, executable 683, gaps 7, LONG 339, SHORT 344, ATR/geometry/margin-ready 683, zero margin rejects/emergencies/forced stop-outs/runtime failure, zero orders, exactly the tester funding balance deal, zero completed trades/returns/PF, and no lifecycle/RunMeta sidecar.

Evidence must use the inherited claim-first/static/archive/captured-byte/failure-inventory contract. This attempt authorizes correctness/data acquisition only. It does not authorize performance analysis, economics, optimization, validation, holdout, paper or live trading.
