# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-006 — frozen economic preregistration

Frozen after `HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-005` passed its outcome-blind
source census and before any EURUSD DESIGN return, PnL, report, chart, or metric for
this depth mapping was opened. Grok `/deep-research-trading-meta5` was advisory; this
local hash-bound contract is the executable authority.

## Hypothesis and population

- Source parent: HYP005 combined source ledger, SHA-256
  `4DE647CB8CC39F5CD26D10D844C11F1B5A493DAF7C69F2CB633AB361912326F0`.
- Compile table: 329 clocks, 318 non-FLAT directions (162 BUY, 156 SELL), one
  source-invalid FLAT, eight ambiguous FLAT and two unavailable FLAT. Canonical table
  SHA-256 `BD2D3F6CF9C048F606F822EF2BEDF0C6DCA4CE6C25673A5235D70F8AC096A3DD`.
- Broker/tester: FivePercentOnline-Real `EURUSD`, M1 host period, Model 0 every tick.
  Decisions and exits use `MqlTick.time_msc`.
- DESIGN: exact 329 clocks from 2019–2020; tester `[2019.01.01,2021.01.01)`.
- Validation/holdout and all later clocks remain sealed.

The thesis is post-wave liquidity transfer: after the first 15 seconds of scheduled
event repricing, asymmetric migration of resting CME 6E depth across levels 2–10
identifies whether the next minute continues the initial aggressive flow or reverses
it. The source direction was frozen without EURUSD target prices.

## Immutable signal and execution

1. Use the exact effective direction already stored in the source ledger. Zero is no
   trade. No score magnitude enters the EA.
2. Convert UTC clocks to the canonical FivePercent server clock using UTC+2 winter /
   UTC+3 summer under the existing EU last-Sunday DST model.
3. The source decision is complete at event T+60. Enter at the first valid EURUSD tick
   with `tick.time_msc >= event_server_msc + 60000`.
4. Exit at the first valid tick with `tick.time_msc >= event_server_msc + 120000`, a
   fixed 60-second holding period.
5. Primary follows source direction. The exact sign reverse changes only direction.
6. One position maximum. Missing the exit boundary means event miss; order rejection
   is never retried. Closely spaced events may be skipped only by the one-position rule.
7. Market orders, no SL/TP/trailing, spread/session/event/direction filter, magnitude
   threshold, price momentum, alternate hold, parameter grid, or optimization.
8. Fixed sizing: `equity * 0.25% / (15 pips * pip value per lot)`, floored to broker
   step and capped at 1.00 lot. The 15-pip denominator is sizing only; no stop exists.

## Engineering and cost gates

The EA must verify compile-table structure, source/table SHA, exact direction counts,
strict time order and server offsets. It logs all 329 events, exact tick boundaries,
bid/ask/fills, spreads and reconstructed costs. Economic interpretation is forbidden
for any table/hash mismatch, pre-boundary entry/exit, more than one owned position,
unaccounted event, wrong tester bounds, runtime failure, or History Quality <=97%.

Frozen costs are the broker's USD 4.00 per lot round-trip commission plus observed
entry/exit spread/fill cost and adverse dynamic slippage:

`max(0, entry_spread_pips - median(prior 10 accepted entry spreads)) * pip_value * lots`.

Base, 1.5x and 2x arms multiply the complete per-trade cost by 1.0, 1.5 and 2.0.
No cost component may be selected after outcomes.

Provider reduced-quality warnings were observed source-side before outcomes for
`EVT0006`, `EVT0027`, `EVT0031`, `EVT0198`, and `EVT0270`. A secondary exclusion
sensitivity must report them but can never rescue the primary verdict.

## DESIGN acceptance and terminal rule

Primary passes only if all gates hold:

- at least 300 completed trades and cadence 2.5–5.0 per week;
- base PF >=1.30 and expectancy >0;
- 1.5x PF >=1.25;
- 2x PF >=1.00 and expectancy >=0;
- both 2019 and 2020 positive;
- max equity drawdown <=8%;
- exact reverse comparator has lower base PF;
- top 5% of trades contribute at most 30% of positive base profit.

If any gate fails, this exact depth direction / T+60 entry / T+120 exit mapping is
terminal. It may not be rescued by score thresholds, event/session/direction filters,
timing, SL/TP, sizing, degraded-cell exclusion, or rerun. A pass authorizes only a
fresh validation successor; it does not authorize promotion, paper, demo-forward, or
live trading.

