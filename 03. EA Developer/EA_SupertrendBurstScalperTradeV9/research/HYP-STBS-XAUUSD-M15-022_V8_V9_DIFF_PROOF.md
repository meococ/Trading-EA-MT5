# HYP-STBS-XAUUSD-M15-022 — V8 to V9 bounded diff proof

## Identities

- Parent V8 source SHA-256: `11E44FF9B51DA50F6DF25C54858BFF492C89A58EED04684C828A70740B37FED9`
- Child V9 source SHA-256: `9B82946CF17A876B547E7227F7FA131183C2383D38BF639574001CAB03DF8D82`
- Parent terminal raw-row SHA-256: `507905ED8C71C4E3DA60853F5A60E7CD44B0A2F56BC06E8EE045FA0102D05C59`

## Allowed executable changes

1. Fresh identity only: version `9.00`, EA name `EA_SupertrendBurstScalperTradeV9`, hypothesis `HYP-STBS-XAUUSD-M15-022`, variant `STBS_H1_FLIP_M15_BURST_TRADE_V9_SL_STRESSED_MARGIN`, magic `5604122`.
2. `EntryPlan` stores five post-check stress diagnostics.
3. `EvaluateMarginCandidate` moves the requested entry adversely by the full frozen 20-point deviation, computes `OrderCalcProfit` from that worst allowed fill to the already-frozen SL, and subtracts a frozen full round-turn commission reserve of `4.4` account-currency units per lot.
4. Required margin is evaluated at requested entry, worst allowed fill and SL; the greatest value drives both the existing 5%-equity position-margin ceiling and the stressed total-margin calculation.
5. The existing percent/money stop-out headroom rules are evaluated on that stressed state. Existing broker-step sizing remains downward-only; unsafe min lot remains a signal rejection.
6. Runtime `EvaluateActualMargin` and its permanent fail-closed backstop are unchanged; gaps beyond the frozen SL/deviation/charge envelope remain engineering-fatal rather than becoming an economic exit.

## Frozen behavior

`AdvanceSupertrend`, signal mapping, exact-next clock, completed M15 ATR14, `BuildEntryGeometry`, 1R stop, 1.5R target, eight-bar hold, Friday/weekend handling, request/order/deal FSM, lifecycle replay, restart state, three OrderSend gateways, risk percentage, cost contract and all acceptance thresholds are byte-identical by focused test.

No session, direction, hour, weekday or PF-derived filter is added. The six removed blank lines at four function boundaries are nonsemantic clone normalization.

## Harness-only companion

The shared `alpha.ps1` remains at its frozen historical SHA. A fresh HYP022 runner calls that canonical AlphaFactory for compile/backtest and creates a separate run-local non-repaint audit manifest after the original run manifest has passed packet reconciliation. The derivative adds only `nondecision_provenance_copytime_authorized=true`, bound to the reviewed static manifest, exact HYP022 source SHA and the single DQ first-date `CopyTime` proof. The runner freezes the auditor SHA, requires exact derivative-manifest identity, `collection_authority_verified=false`, one exact audited V9 source, zero findings and one exact CopyTime allowance, then rehashes auditor/derivative/audit before accepting them. The original Alpha run manifest is not modified.
