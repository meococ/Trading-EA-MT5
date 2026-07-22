# Logic-to-code matrix - HYP-VRAS-EURUSD-M5-001

This matrix is frozen before the first meaningful Model-0 result. Source line
locations are filled by named function so later line movement does not break
identity.

| ID | Requirement | Quantified implementation | Source function | Information set | Telemetry/test | Status |
|---|---|---|---|---|---|---|
| G01 | ADX whipsaw | 25/19 hysteresis, minimum dwell 6 | `UpdateRegime` | ADX14 shift 1 | regime switch counter + synthetic sequence | MAPPED |
| G02 | Correct bands | weighted Welford population variance | `ComputeSessionStats` | closed M5 since frozen anchor | VWAP/SD fields + hand fixture | MAPPED |
| G03 | Early-session safety | warmup 15 and SD >=0.30 ATR | `EvaluateSignal` | closed bar/ATR shift 1 | warmup/SD reject counters | MAPPED |
| G04 | Bias conflict | regime is root; bias only in TREND | `EvaluateSignal` | one immutable decision snapshot | branch/direction fields + four-case tests | MAPPED |
| G05 | Open trade plan | regime flip never retargets active SL/TP | `ManageOwnedPosition` | broker position snapshot | lifecycle reconciliation | MAPPED |
| G06 | DST/session | server->UTC, London EU DST, NY US DST | clock helpers / `SessionAllows` | decision bar server time | server/UTC/offset/session log + boundary tests | MAPPED |
| G07 | Parameterized anchor | London, UTC midnight, broker day enums | `SessionAnchorUtc` | predeclared arm only | anchor mode/time | MAPPED |
| G08 | AVWAP non-repaint | strict five-bar fractal first valid at shift 3 | `FindConfirmedAnchor` | shifts 1..65 only | anchor/confirmed time + mutation tests | MAPPED |
| G09 | AVWAP value | weighted typical price anchor through shift 1 | `ComputeAnchoredVwap` | closed M5 only | value + hand fixture | MAPPED |
| G10 | Tick-volume uncertainty | tick-volume primary; equal-weight shadow/arm | `BarWeight` / stats | same bars/anchor | both VWAP values + sensitivity run | MAPPED |
| G11 | Cost filter | target pips >=8*estimated round-trip pips | `CostDistanceAllows` | decision + pre-send quote | component and reject fields + boundary tests | MAPPED |
| G12 | Rejection | pinbar body<=0.40/wick>=0.50 OR engulfing | `BullishRejection` / `BearishRejection` | closed bars 1-2 | rejection flags + mirror tests | MAPPED |
| G13 | RANGE long/short | -2SD/RSI>25 and +2SD/RSI<75 | `EvaluateSignal` | closed bar | signal type + symmetric tests | MAPPED |
| G14 | TREND long/short | bias, pullback-reclaim, AVWAP, M15 bias | `EvaluateSignal` | closed M5 and last fully closed M15 | confluence fields + mirror tests | MAPPED |
| G15 | Execution timing | signal at close; entry next-bar quote | `OnTick` / `TryOpenTrade` | new-bar gate only at shift 0 | decision/entry timestamps | MAPPED |
| G16 | Risk/ownership | 0.25%, one position/order, OrderCheck | `RiskSizedVolume` / `TryOpenTrade` | current broker geometry | lifecycle risk + static tests | MAPPED |
| G17 | Safety | daily/account/trade-count/spread/news gates | `EntryGuardsAllow` | current account/quote/calendar | reject counters | MAPPED |
| G18 | Lifecycle | one lifecycle CSV + one RunMeta JSON | telemetry helpers | trade transactions | AlphaFactory reconciliation | MAPPED |

## State and sequencing

`NEW CLOSED M5 BAR -> rebuild/replay clock and session state -> update regime ->
evaluate exactly one RANGE or TREND branch -> freeze entry/SL/TP snapshot ->
guards -> OrderCheck -> synchronous market request -> lifecycle reconciliation`.

Every restart seeds the current M5 bucket, rebuilds Session VWAP and replays ADX
history before the next decision. Any clock/data/indicator/anchor/cost error
fails closed for entry. A new regime only affects future decisions.

## Known limitations before outcome

- Historical spread/commission/slippage provenance is diagnostic only.
- The news list is third-party and cannot authorize promotion.
- No second broker M5 tick-volume feed is currently bound.
- The Google technical supplement is a live document; its frozen export hash
  above, not later edits, defines this implementation.
