# SCC MT5 replication — logic-to-code matrix

This matrix is frozen with
`HYP-SCC-MT5-REPLICATION-EURUSD-M5-002_FROZEN_PREREG.md` before source
implementation. Function names are the required implementation surface.

| Frozen requirement | Required code surface | Verification |
|---|---|---|
| Closed M5 decisions only | `OnTick`, `CopyRates(...,1,6,...)`, `ReadAtrClosed` | static audit + source test |
| Strict N=2 pivot known before BREAK | `RefreshConfirmedPivots` candidate shift 4 | synthetic/source test |
| Contiguous close BREAK | `DetectBreak` | source test + decision telemetry |
| First arm per UTC date | `UtcDateKey`, `g_attempted_day_key` | source test + funnel |
| Pivot consumed on arm | `ConsumeArmedPivot` | source test + telemetry |
| Control immediate next-bar entry | `ResolveControlBreak` | matched arm test |
| Immediate HOLD outside | `ResolveHold` | source test + funnel |
| 12-bar first passage and priority | `ResolveRetest` | source test + funnel |
| Complex-extreme + 0.25 ATR stop | `BuildTradeDecision` | source test + decision log |
| 2R target and 24-bar timeout | `TryOpenTrade`, `ManageOwnedPosition` | source test + lifecycle |
| Risk-sized order and broker preflight | `RiskSizedVolume`, `OrderCheck` | source test + tester log |
| One owned position | `AnySymbolExposure`, `OwnedPositionTicket` | source test + lifecycle |
| Lifecycle-v3 evidence | `OpenTelemetry`, `LogLifecycleDeal`, `WriteRunMeta` | capability contract + run validation |
| Diagnostic-only boundary | RunMeta `promotion_eligible=false` and cost/news status | source test + receipt |

