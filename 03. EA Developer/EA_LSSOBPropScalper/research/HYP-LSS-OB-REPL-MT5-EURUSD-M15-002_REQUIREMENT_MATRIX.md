# Requirement Matrix - HYP-LSS-OB-REPL-MT5-EURUSD-M15-002

Status: FROZEN before source creation and MT5 Strategy Tester outcome.

This Owner-mandated diagnostic child keeps the exact signal surface of
`HYP-LSS-OB-REPL-EURUSD-M15-001`. It changes delivery routing only: a canonical
EA must be compiled and exercised by MT5 Model 0 even though the parent cadence
probe was terminal. No rule may be loosened to manufacture trades.

| Requirement | Frozen rule | Planned MQL5 surface | Verification |
|---|---|---|---|
| Decision clock | New closed M15 bar; signal reads shift >=1 only | `OnTick`, `ProcessClosedM15Bar` | static audit + tests |
| UTC conversion | FivePercent +2/+3 EU-DST through 2023 | `ServerToUtc` | boundary tests |
| Sessions | `[07:00,10:00)` and `[13:00,16:00)` UTC | `EligibleSession` | contract tests |
| H1 BOS | latest confirmed strength-2 pivot break, persistent direction | `ClosedH1Bias` | closed-bar audit |
| H4 dealing range | latest confirmed strength-2 high/low bracketing price | `ClosedH4Range` | closed-bar audit |
| Premium/discount | long <= midpoint; short >= midpoint | `ContextAligned` | contract tests |
| Sweep | latest confirmed M15 pivot within 20 bars; wick through, close inside | `DetectSweep` | FSM tests |
| Displacement | next 3 bars; directional body >=1.8 x closed `iATR(14)` | `AdvanceDisplacement` | FSM tests |
| Strict FVG | bull `low[i] > high[i-2]`; bear inverse | `StrictFvg` | unit contract |
| Order block | last opposite candle; body overlaps FVG | `FindOrderBlock`, `OverlapZone` | unit contract |
| Control arm | enter first quote after displacement close | `AdvanceDisplacement` | tester variant 0 |
| Challenger | first overlap retest <=12 bars, same session, confirmation required | `AdvanceRetest` | tester variant 1 |
| Confirmation | engulfing OR body/range >=0.60 and close in outer 25% | `IsConfirmation` | unit contract |
| ADX | closed M15 `iADX(14) >25` | `ClosedAdx` | handle/shift audit |
| News | bound EUR/USD high-impact calendar, inclusive +/-30 minutes | `NewsBlocked` | boundary tests |
| Stop | farther adverse sweep/OB wick +1.5 pip; reject outside 8-12 pip | `BuildStop`, `TryOpenTrade` | geometry tests |
| Target | fixed 2R, no partial/BE/trail | `TryOpenTrade` | source audit |
| Risk | 0.25% equity; one position; <=2 trades/day | `CanOpenNow`, `RiskSizedVolume` | source/tests |
| Account guards | day -1.5%, peak DD -8%, 120m cooldown after 2 losses | risk state functions | restart/tests |
| Spread/flatten | <=1.8 pip; flatten 21:45 UTC | `CanOpenNow`, `ManageOwnedPosition` | source/tests |
| Ownership | symbol + magic, fail-closed position/order scans | ownership functions | source/tests |
| Telemetry | lifecycle-v3 RunMeta and LifecycleTrades | telemetry functions | reconciliation |
| Variants | exactly `CONTROL=0`, `LSS_OB_CHALLENGER=1` | `InpSignalMode` | two fixed MT5 runs |
| Window/model | EURUSD M15, 2019.01.03-2022.12.31, Model 0 | AlphaFactory command | run manifest |
| Holdout | 2023+ forbidden | task/registry/run config | manifest audit |
| Economics boundary | current/unverified tester cost is diagnostic only | readout | no promotion claim |

Engineering completion requires 100% implemented rows, tests PASS, compile
0/0, exact-source non-repaint PASS, and actual MT5 report artifacts for both
variants. Economic gates remain unchanged but cannot be called promotion-grade
while spread/commission/slippage provenance is failed.
