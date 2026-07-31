# Logic-to-Code Matrix — HYP-VRAS-EURUSD-M5-006

| Requirement | Frozen implementation surface |
|---|---|
| Closed-bar H1 bias | EMA handle read at shift 1 and `iClose(PERIOD_H1,1)` |
| Closed-bar M5 entry | `CopyRates(...,1,...)`; bars 1/2 only |
| Rolling VWAP | 48 completed M5 bars, typical price × tick volume |
| Shared raw structure | completed 10-bar `iLowest`/`iHighest` plus 1.5-pip buffer |
| Control stop | clamp raw distance to 4–15 pips |
| Challenger stop | ATR14 shift 1; reject >3 ATR; floor at 1 ATR; no inside-structure clamp |
| Shared TP/BE/hold | 1.5R TP; BE at 1R plus 0.5 pip; 24 M5 bars |
| Money risk | `OrderCalcProfit`, symbol min/max/step, `OrderCheck` |
| Guards | daily counter/loss, initial-equity DD latch, spread, symbol exposure |
| Lifecycle | `OnTradeTransaction` logs every own IN/OUT deal with all cost components and positive initial risk |
| No tester truncation | no `TesterStop` or `ExpertRemove`; risk guard blocks entries only |

## HYP007 diagnostic extension

| Requirement | Frozen implementation surface |
|---|---|
| Full-horizon identity | exact `HYP-VRAS-EURUSD-M5-007`, magic 5600757 and arm-specific full-horizon tags |
| Tester-only DD bypass | `InpDiagnosticDisableAccountDDEntryHalt` is rejected outside `MQL_TESTER`; HYP006/default must keep it false |
| DD remains observable | update initial-equity and peak-equity DD each tick; log threshold crossed, maxima and actual halt state in RunMeta |
| Tester survival | risk fixed at 0.05% only for HYP007; sizing algorithm, entry, stop, TP, BE and hold logic are unchanged |
| Claim boundary | `promotion_eligible=false`; full-window PF/R/regime statistics are diagnostic and cannot rescue HYP006 |

## HYP008 tester-survival identity extension

| Requirement | Frozen implementation surface |
|---|---|
| Preserve cash risk | tester deposit USD 500,000 × 0.01% risk ≈ USD 50 initial budget, matching HYP007's USD 100,000 × 0.05% |
| Source delta | HYP008/magic/variant validation and version text only; no signal, stop, target, management or telemetry delta |
| Stop-out boundary | broker/tester stop-out must be absent and the known 2019–2022 bar corpus must complete before economics are described |
