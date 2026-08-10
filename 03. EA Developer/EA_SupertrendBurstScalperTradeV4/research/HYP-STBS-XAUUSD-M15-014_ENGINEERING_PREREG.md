# HYP-STBS-XAUUSD-M15-014 — broker-aware margin and lifecycle revision

Status: FROZEN BEFORE ANY HYP014 MT5 OR OUTCOME ACCESS

Static syntax compilation was performed outcome-blind before this freeze and produced 0 errors / 0 warnings. It did not open MT5, source bars, trades, returns, PF, costs, validation or holdout.

## Lineage and failure radius

- Parent: terminal `HYP-STBS-XAUUSD-M15-013`, raw terminal-row SHA256 `52A5EBFDB9D82B65D6BA85F182C1E21C4D0015FB80C7CE78890CC4FA53E02AF6`.
- Parent verdict: `KILL_ENGINEERING_PRE_COST_DATA_IDENTITY_AND_BROKER_STOPOUT_NO_ECONOMIC_VERDICT`.
- HYP013 did not produce admissible economics. Its displayed `PF=0.00, N=1` is prohibited from informing this revision.
- HYP014 changes only broker-margin safety and lifecycle reconciliation. Signal timestamps, Supertrend 10x3, M15 ATR14, 1.00 ATR stop, 1.50R target, eight-bar hold, Friday rules and maximum requested risk 0.25% remain unchanged.

## Frozen identity

- Hypothesis: `HYP-STBS-XAUUSD-M15-014`
- EA: `EA_SupertrendBurstScalperTradeV4`
- Symbol/chart: `XAUUSD / M15`
- Source: `03. EA Developer/EA_SupertrendBurstScalperTradeV4/EA_SupertrendBurstScalperTradeV4.mq5`
- Source SHA256: `028D0AADB49856F58B167390E93300CD12AD90993F13FE7D5012DE6FFB8FC726`
- Magic: `5604114`
- Variant: `STBS_H1_FLIP_M15_BURST_TRADE_FSM_V4_MARGIN_SAFE`
- Actual data fingerprint inherited from the only HYP013 manifest: `077437E0038B40FEDB8AC611CAFE410B2FF8D0A90A742F0C52336F728D8C0BF4`.
- Preload: `2005.01.01` through `2023.01.01`, Model 0. Indicator recursion advances across full available H1 prehistory; signals/trades remain restricted to `[2018-01-01 02:00 server, 2023-01-01 02:00 server)`.

## Frozen margin contract

Risk-sized volume remains an upper bound. Starting at that volume, the EA descends by the native symbol volume step and never rounds upward. Every candidate must pass:

1. valid account equity/free/current margin and valid `ACCOUNT_MARGIN_SO_MODE`, `ACCOUNT_MARGIN_SO_CALL`, `ACCOUNT_MARGIN_SO_SO`;
2. `OrderCalcMargin` with positive finite required margin;
3. new-position required margin no greater than 5.00% of current equity and no greater than free margin;
4. `OrderCheck` success with finite positive projected equity, margin, free margin and margin level;
5. in percent stop-out mode, projected margin level at least `max(2000%, max(SO_CALL, SO_SO) * 1.25)`;
6. in money stop-out mode, projected free margin and projected equity-minus-margin each at least `max(SO_CALL, SO_SO) * 1.25`.

The first passing native-step volume is used. If minimum volume is unsafe, the event is rejected once. Missing/invalid broker properties or API failure is a runtime failure. Risk, stop or target may never be widened to obtain a pass.

After a fill becomes visible, the same percent/money threshold is checked against actual account margin state. Failure creates a persistent runtime-fault exit intent and emergency close. A `DEAL_REASON_SO` close is attributed by the owned position identifier/opening magic, registered idempotently before any row-context dependency, and sets `runtime_failed=true`. The lifecycle sidecar uses a stable hypothesis/magic identity across reinitialization, reloads already logged deal and position IDs, defers a closing callback until its position OPEN is logged, and replays history deterministically in two passes (OPEN then CLOSE). Deinitialization rejects a distinct-position OPEN/final-CLOSE imbalance; multiple partial entry/close deals do not create a false imbalance.

## Stage 1 — one audit-only correctness run

- Attempt: `STBS014-MODEL0-AUDIT-001`, limit 1, no retry.
- Audit packaging is exactly `telemetry_profile=none`, `TelemetryTier=off`, `InpEnableTelemetry=false`; the source hard-rejects `InpAuditOnly=false`. It emits journal diagnostics only and must create no lifecycle or RunMeta sidecar. A later trade-enabled child must restore and separately review lifecycle-v3.
- Alpha overrides omit `InpEnableTelemetry` because profile `none` forbids telemetry override tokens; the compiled default and OnInit guard both require false. Exact remaining overrides are `InpAuditOnly=true; InpHypothesisId=HYP-STBS-XAUUSD-M15-014; InpMagic=5604114; InpMaxNewPositionMarginPct=5.0; InpMinProjectedMarginLevelPct=2000.0; InpStopoutHeadroomFactor=1.25; InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_FSM_V4_MARGIN_SAFE`.
- No OrderSend gateway may execute.
- Expected parent signal identity: raw 690, executable 683, gaps 7, LONG 339, SHORT 344, ATR-ready 683, geometry-ready 683.
- Required: margin-ready 683, margin rejects 0, margin emergencies 0, forced stop-outs 0, runtime failure false, zero trade orders, zero market entry/exit deals, zero positions/trades/returns/PF. The tester-start balance funding row is expected and is not a market deal.
- Required data quality: history quality >97, no skip, exact tester journal bounds and series proof; manifest base data fingerprint must equal the frozen actual fingerprint above.
- Evidence integrity: after the durable attempt claim and before Alpha starts, read the reviewed static EX5, compile log and bound `quant_analyzer.py` once, verify their authority hashes, and write exclusive/fsynced attempt-local archives. The receipt binds those immutable archives. Immediately after Alpha returns, before accepting its return code, capture any canonical run-compile EX5/log and the exact created/deleted run-directory delta. A failed/nonzero attempt must bind the compile capture plus an immutable file inventory of every discovered new run directory. A successful attempt then captures the exact run manifest/source/config/report/journal bytes into a separate attempt-local archive, requires one `Result: 0 errors, 0 warnings`, reconciles run EX5 to both manifest EX5 hashes, and performs report/journal acceptance only on the captured bytes.

The zero-send audit proves signal/margin-candidate scheduling only; it cannot prove post-fill margin, transaction ordering, forced-close telemetry or lifecycle completeness. A clean audit plus compile 0E/0W, tests and independent review may authorize only one engineering-first baseline attempt. That later report becomes economic evidence only if the same attempt completes the full horizon with `runtime_failed=false`, zero forced stop-outs and exact OPEN-position/final-CLOSE-position reconciliation. Otherwise it is another engineering failure and PF remains inadmissible. This prereg does not authorize that baseline, optimization, OOS, holdout, paper or live.

## Future baseline gates (not yet authorized)

If engineering passes, the unchanged baseline must satisfy after frozen research-proxy cost: PF >1.30, 2–5 completed trades/week using the inclusive day-count convention, positive x1 mean net R and every calendar year positive x1 net R, at least 500 complete trades, both directions >=30%, max-year share <=30%, x1.5 PF >=1.25, x2 PF >=1.00, and max drawdown <=8%. Optimization/WFA/OOS remain locked until that baseline passes.

Prohibited rescue: session/direction filters, alternate indicator periods, ATR, RR, stop, target, hold time, risk increase, cooldown, smoothing, optimization cell or threshold derived from HYP013/HYP014 outcomes.
