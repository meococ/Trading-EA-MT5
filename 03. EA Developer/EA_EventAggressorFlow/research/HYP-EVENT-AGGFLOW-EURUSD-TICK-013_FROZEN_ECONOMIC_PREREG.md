# FROZEN ECONOMIC PREREGISTRATION — HYP-EVENT-AGGFLOW-EURUSD-TICK-013

Frozen on 2026-08-12 after HYP012 passed its outcome-blind source gate and
before any EURUSD DESIGN price, return, PnL, report, chart, or economic metric
for this mapping was opened. Grok `/deep-research-trading-meta5` returned
`PROCEED_WITH_FROZEN_ECONOMICS`; that response is advisory. This file and the
hash-bound local artifacts below are the executable authority.

## Hypothesis and population

- Parent: `HYP-EVENT-AGGFLOW-EURUSD-TICK-012`.
- Symbol/feed: FivePercentOnline-Real `EURUSD`, tester period `M1`, Model 0
  every tick. M1 is only the tester host; decisions use `MqlTick.time_msc`.
- DESIGN: the exact 329 frozen high-impact USD/EUR scheduled release clocks in
  2019-2020. Tester bounds are `[2019.01.01,2021.01.01)`.
- Validation: all 2021-2022 source and EURUSD outcomes remain sealed.
- Static source: HYP012 `event_signed_flow.csv`, SHA256
  `65AA6558629F6FF224E5DB6FD218B1DC9A4EC6A7B07DE886C3FE13E5922A106C`.
- Source state: 329 clocks, 326 nonzero flows, 156 BUY, 170 SELL, one tie and
  two explicit zero-source events. EVT0198 and EVT0270 remain in the primary
  population despite their predeclared provider-condition caveats.

The causal thesis is first-wave continuation: aggressive CME 6E trade flow in
the receive-time half-open interval `[event,+15s)` identifies the direction of
the initial institutional EUR repricing that may persist in EURUSD for the next
60 seconds. Positive flow maps to BUY EURUSD and negative flow maps to SELL.
Exact sign reversal is the sole comparator.

## Immutable signal and execution contract

1. `signed_flow = sum(B size) - sum(A size)` from the already-qualified HYP012
   source. `N` contributes zero; zero/tie/no-source means no trade.
2. Convert each UTC event clock once to the measured FivePercent server clock:
   UTC+2 winter / UTC+3 summer, EU last-Sunday DST convention through 2023.
   Store UTC and server millisecond clocks in the generated compile-time table.
3. Signal is complete at `event_server_msc + 15000`. Entry is the first
   `EURUSD` tick with `tick.time_msc >=` that boundary.
4. Exit is the first tick with `tick.time_msc >= event_server_msc + 75000`.
5. Primary direction is `sign(signed_flow)`; reverse comparator multiplies the
   same direction by -1. The comparator changes no other input or artifact.
6. One position maximum. If another owned position is open at a new entry
   boundary, skip the new event. A missing eligible tick before +75s is a hard
   event miss and is logged; a rejected market request is never retried.
7. Full-size market order or reject. No partial-fill reconstruction, SL, TP,
   trailing, session filter, spread filter, direction filter, event-name/type
   subset, magnitude threshold, PRE feature, price momentum, volatility gate,
   alternate horizon, optimization, or parameter grid exists.
8. Fixed sizing only: `equity * 0.25% / (15 pips * pip value per lot)`, floored
   to broker volume step and hard-capped at 1.00 lot. The 15-pip denominator is
   a sizing convention only; no stop is placed.

## Source binding and hard engineering gates

`generate_event_table.py` must reproduce the compile-time table from the exact
HYP012 CSV and canonical FivePercent clock model. The EA logs the source CSV
SHA256 and the generated canonical-table SHA256 at `OnInit`, verifies array
cardinality, strict clock ordering, UTC/server offsets, source counts and the
runtime SHA256 of the canonical array serialization, and returns `INIT_FAILED`
on any mismatch.

Economic interpretation is forbidden if any of these occurs:

- entry timestamp earlier than +15.000s or exit timestamp earlier than +75.000s;
- table/source hash or structural invariant failure;
- more than one owned position, wrong symbol, wrong hypothesis, or unexpected
  position disappearance;
- unaccounted event among the 329 identities or missing terminal ledger row;
- any validation clock/source/outcome access;
- tester History Quality <=97%, wrong tester bounds, or missing journal proof.

## Cost and stress contract

The official The5ers FX specification observed before outcome read states a
USD 4.00 per standard-lot round-trip commission. For every completed event the
EA audit records actual entry/exit bid, ask, spread, requested/fill price, lots,
and executable PnL. Analysis reconstructs:

- raw mid-to-mid PnL;
- observed executable spread/fill cost = raw mid PnL minus executable PnL;
- commission = USD 4.00 * lots;
- adverse dynamic slippage = `max(0, entry_spread_pips - trailing_median) *
  pip_value * lots`, where trailing median uses only the prior ten accepted
  event entry spreads (all available prior entries until ten exist; zero for
  the first accepted event);
- base net = raw PnL minus the complete observed spread/fill, commission and
  dynamic-slippage cost;
- 1.5x and 2x nets multiply that same complete per-trade cost by 1.5 and 2.0.

No cost component may be selected after seeing outcomes. The tester-native
report is engineering/execution evidence; the custom event ledger is the
authority for the frozen base/1.5x/2x economic gates.

## DESIGN acceptance and terminal rule

Primary passes only if every condition holds:

- at least 250 completed trades and 2.5–5.0 trades per week;
- base cost PF >=1.30 and base expectancy >0;
- 1.5x cost PF >=1.25;
- 2x cost PF >=1.00 and 2x expectancy >=0;
- 2019 and 2020 each have positive base net PnL;
- equity max drawdown <=8%;
- exact sign-reversal comparator has lower base PF;
- top 5% of events contribute <=30% of positive total base net profit;
- the two predeclared degraded cells are reported in a secondary exclusion
  sensitivity, but that sensitivity can never rescue a failed primary.

If primary fails any gate, this exact mapping is terminal and may not be rescued
with thresholds, filters, timing, SL/TP, sizing, event subsets, or reruns. If it
passes, only then may a fresh validation successor request authority to open the
sealed 2021-2022 source/outcomes. No promotion, paper, demo-forward, or live
authority is granted by this preregistration.

