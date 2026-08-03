# HYP-LASR-EURUSD-M5-001 - Logic Matrix

Authority scope: the second ordered atomic falsification cell from
`HYP-LOMX-DESIGN-M5-002`: EURUSD M5 Asian-range sweep/reclaim only. The generic
compression arm and parked dual-engine combiner are disabled. No threshold,
session, geometry, direction, or exit rule changed after the invalid XAUUSD
tester-population run.

| Layer | Frozen rule | Fail-closed behavior |
|---|---|---|
| Clock | FivePercent server-to-UTC; EU DST through 2023, US DST from 2024 | Missing exact clock/history rejects the bar |
| Timeframe | M5 only; all signal inputs are closed bars starting at shift 1 | Any other chart period rejects initialization |
| Asian range | Exactly 72 bars from 00:00 through 05:55 UTC of the same date | Any missing timestamp rejects that date |
| Trade window | 07:00 inclusive to 16:00 exclusive UTC; weekdays only | Outside window produces no entry |
| Long | `Low[1] < AsianLow - 0.30*ATR14`, `Close[1] > AsianLow`, prior-20 tick-volume z-score `>1.50` | Every conjunct is mandatory |
| Short | `High[1] > AsianHigh + 0.30*ATR14`, `Close[1] < AsianHigh`, prior-20 tick-volume z-score `>1.50` | Every conjunct is mandatory |
| Entry | First executable quote after the closed signal bar; Ask for long, Bid for short | Missing quote or excessive spread rejects entry |
| Stop | Long: signal low minus `0.20*ATR14`; short: signal high plus `0.20*ATR14` | Tick/stop/freeze geometry must be valid |
| TP1 | Asian midpoint; close exactly 50%, then move remaining stop to conservative tick-normalized entry | Unsplittable volume rejects entry before order send |
| TP2 | Opposite Asian boundary | Entry rejected unless TP2 offers at least `1.50R` |
| Risk | 0.25% current equity; `OrderCalcProfit` sizing; floor to volume step | Never round risk upward |
| Exposure | At most one `_Symbol + magic` exposure; maximum 3 new positions per UTC day | Unrelated account positions are untouched |
| Daily guard | Persistent 3.5% daily equity lock; daily flatten 20:00 UTC | Close/delete owned exposure and reject new entries |
| Drawdown guard | Persistent 8% peak-equity lock; live LOMX instances share account key, tester isolates hypothesis | Once hit, remains locked |
| Holding guard | No UTC date crossover, no weekend carry, maximum 96 M5 bars | Close owned position synchronously |
| Lot consistency | After exactly 10 same-magic entry fills, require proposed lot within 0.5-1.5 times AvgLot10; cap high values and reject low values | Never force a too-small risk lot upward |
| Telemetry | lifecycle-v3, one real deal row per MT5 entry/exit deal, exact `deal_*` economics and exactly one final close | Missing telemetry prevents economic authority |

The control remains synchronous. The owner plan's async kernel is excluded
because asynchronous order-state behavior is not part of this signal
hypothesis and would introduce a second experimental dimension.
