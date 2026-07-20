# Requirement-to-Code Matrix - EA_ICTFVGReportFidelity

Evidence states: `planned_exact`, `implemented_exact`, `implemented_proxy`,
`unmet`. Signal/entry/risk rows are exact; the historical-news row is a
hash-bound source-C proxy and therefore keeps `promotion_eligible=false`.

| Report requirement | Frozen quantitative rule | State | Code/evidence |
|---|---|---|---|
| EURUSD M5 + M15 structure | M5 decisions, closed M15 MSS/ADX | `implemented_exact` | `ProcessClosedM5Bar`, `AdvanceM15Mss`, `ClosedM15Adx` |
| London/NY killzones | 07-11 and 13-17 UTC using broker DST conversion | `implemented_exact` | `EligibleSession`, `ServerToUtc` |
| Sweep/reclaim | Latest confirmed M5 pivot, wick through and close inside | `implemented_exact` | `FindLatestM5Pivots`, `DetectSweep` |
| Displacement | Body >1.5x mean body of prior 20 closed M5 bars | `implemented_exact` | `AdvanceDisplacement` |
| Strict FVG | Current closed M5 low > high two bars older, or inverse | `implemented_exact` | `DetectStrictFvg` |
| Ordered sequence | Explicit finite-state machine with expiry/invalidation | `implemented_exact` | `SETUP_SWEPT -> SETUP_DISPLACED -> SETUP_MSS_CONFIRMED` |
| M15 MSS | Post-displacement closed M15 break of pre-sweep pivot | `implemented_exact` | `FindLatestM15BreakLevel`, `AdvanceM15Mss` |
| Fresh OB | Last opposite candle before displacement; no pre-MSS mitigation | `implemented_exact` | `FindFreshOrderBlock`, `AdvanceM15Mss` |
| OB/FVG confluence | Non-empty intersection required | `implemented_exact` | `AdvanceDisplacement` overlap bounds |
| Retest entry | First 12-bar retest, 50-70% FVG depth, rejection close | `implemented_exact` | `AdvanceRetest` |
| Regime | Closed M15 iADX(14) >25 | `implemented_exact` | `ClosedM15Adx` |
| News | Historical high-impact +/-30 minutes | `implemented_proxy` | 209 weekly pages / 1,282 timed EUR/USD rows; `NewsCalendar2019_2022.mqh`; binary-search lookup; build audit `20260718_NEWS_CALENDAR_BUILD_AUDIT.json` |
| Spread | <=1.5 pips immediately before send | `implemented_exact` | `SpreadAllowed` |
| Stop/target | OB origin +/-1.5 pips; fixed 2R | `implemented_exact` | `TryOpenTrade` |
| Breakeven | At +1R lock +0.5R; never widen | `implemented_exact` | `ManageOwnedPosition` |
| Daily/prop risk | 0.25%, -1.5% daily stop, 2 actual entry lifecycles/day, 8% persistent peak-equity DD | `implemented_exact` | `CanOpenNow`, `RiskSizedVolume`, `CountActualEntryLifecyclesForUtcDay`, `SavePersistentRiskState` |
| Cool-off | Two losing lifecycles -> 120 minutes, preserved across UTC day/restart, including a close while offline | `implemented_exact` | `LifecycleStatsFromHistory`, `ApplyLifecycleClassification`, `RestoreOwnedPositionState` |
| No overnight | Force flat by 22:00 UTC | `implemented_exact` | `ManageOwnedPosition` |
| Execution safety | ownership, pending-order block, OrderCheck + server retcode, fill-aware risk reconciliation and retry latch | `implemented_exact` | `OwnedPendingOrderExists`, `TradeRetcodeAccepted`, `ReconcileActualFillRisk`, `ForceCloseOwnedPosition` |
| Telemetry | lifecycle-v3 + run metadata/funnel counters | `implemented_exact` | `OpenLifecycleTelemetry`, `WriteRunMeta`, `OnTradeTransaction` |
| Non-repaint | only closed bars and as-of pivots | `implemented_exact` | `research/evidence/20260718_NONREPAINT_AUDIT_V8/nonrepaint_audit.json` |

The unordered score in `EA_FVGConfluence` is not reused.

Compile receipt: `research/evidence/20260718_SOURCE_BINARY_RECEIPT_V6.json`.
