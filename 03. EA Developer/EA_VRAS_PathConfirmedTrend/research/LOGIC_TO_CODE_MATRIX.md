# Logic-to-code matrix — HYP-VRAS-EURUSD-M5-004

HYP-004 inherits the complete HYP-003 signal/risk/execution surface and adds one
TREND-only one-bar continuation state. RANGE behavior is unchanged.

| ID | Requirement | Frozen implementation | Information set | Evidence |
|---|---|---|---|---|
| P01 | Raw setup | Existing HYP-003 `EvaluateSignal` TREND result | closed M5 + closed M15 | raw event telemetry |
| P02 | One pending only | Store one raw `DecisionState`; replace only after prior resolves | in-memory causal state | arm/reject counters |
| P03 | Exact horizon | Confirmation only when current bar = setup decision + 300s | adjacent closed M5 | timestamp test |
| P04 | Extreme break | long close > setup high; short close < setup low | confirmation shift 1 | mirror unit tests |
| P05 | Regime continuity | current state remains TREND | current closed ADX update | reject reason |
| P06 | Mean-stack continuity | close remains beyond current session VWAP and AVWAP from setup anchor | closed M5 history | parity telemetry |
| P07 | HTF continuity | last fully closed M15 close remains beyond current M15 VWAP | closed M15 only | M15 fields/test |
| P08 | Frozen stop | retain raw setup stop; TP = 1.80R from actual delayed entry | raw setup + quote | lifecycle geometry |
| P09 | No resurrection | failed/expired candidate clears immediately | one-bar state | expiry/reject counters |
| P10 | Control identity | path flag false executes inherited immediate logic | same source | matched control receipt |
| P11 | Range invariant | RANGE entry remains immediate under both arms | closed M5 | source/static test |
| P12 | Guard observability | preserve guard behavior but emit distinct rejection status | current account/quote | decision telemetry |
| P13 | Non-repaint | all decisions use `CopyRates(...,1,...)` / indicator shift 1 | closed bars | exact-source audit |
| P14 | Fail-closed identity | exact HYP-004 ID/magic and flag↔variant pairing | OnInit inputs | all-occurrence tests |

State sequence for the challenger:

`NEW BAR -> evaluate current closed snapshot/regime -> resolve prior pending ->
possibly enter -> evaluate current raw setup -> arm at most one new pending`.

Restart discards pending state. Data/clock/indicator/anchor failure clears or
rejects the candidate; it never falls back to immediate TREND entry.
