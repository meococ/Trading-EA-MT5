# HYP-CME6E-OPT-PIN-EURUSD-M15-001 - DESIGN economic preregistration

Status: `RETIRED_NO_USE`. This document was created after the authoritative
`KILL_SOURCE_CONTRACT_INVALID` receipt. It never authorized a target capture,
economic readout, EA, or promotion decision. No historical EURUSD tick, price,
return, PnL, or MQL5 result was opened for this hypothesis.

The population and rules below are retained only as forensic evidence of the
aborted draft. They are not a valid preregistration and must not be executed or
reused by a child hypothesis.

## Population and clocks

- DESIGN is fixed to `2018-01-01T00:00:00Z` through
  `2023-01-01T00:00:00Z`; validation remains sealed.
- The population is the 508 events in
  `futures_reference_directions.csv`.  No event may be removed after reading a
  EURUSD price except by the mechanical missing/invalid tick rules below.
- For each event, entry clock is `decision_utc` and exit clock is the exact
  source-defined option `expiration_utc`, 15 minutes later.
- Broker is the configured AlphaFactory portable `FivePercentOnline-Real`
  demo lane and symbol is exact `EURUSD`.
- UTC is the target clock.  The Python MT5 API returns epoch seconds in UTC;
  `time_msc` is authoritative inside equal-second ticks.  No manual broker
  server offset is added to tick epochs.

## Minimal tick request and executable prices

For each event, request only `[entry_clock, entry_clock + 60 seconds]` and
`[exit_clock, exit_clock + 60 seconds]` with `COPY_TICKS_ALL`.  Select the first
tick at or after the relevant clock whose bid and ask are finite and positive
and `bid < ask`.

- BUY entry is entry ask; BUY exit is exit bid.
- SELL entry is entry bid; SELL exit is exit ask.
- If no valid tick exists inside either fixed 60-second window, the event is
  no-trade.  No earlier tick, wider window, bar interpolation, or another
  symbol is allowed.
- At least 95% of the frozen 508 events must have both executable ticks or the
  target gate fails before economics.

## Size and cost

The source/economic analyzer uses a constant `1.00` standard lot solely to
express dollars.  EURUSD contract size is frozen from `symbol_info` and must be
`100000`.  No risk sizing, compounding, stop, target, or intratrade management
is used; every completed event is held to the fixed exit clock.

Observed bid/ask prices already include entry and exit spread.  Commission is
separate and frozen at `$4.00 per lot per deal`, `$8.00 round-turn per 1.00
lot`, based on nonzero `FivePercentOnline-Real` EURUSD demo deal history observed
before opening this hypothesis's outcomes.

Dynamic adverse slippage is applied to both entry and exit.  For each trade,
one-leg slippage in price is `0.5 * entry_spread`; therefore the base
round-turn slippage is one full entry spread.  It is charged in the adverse
direction and never improves a fill.

Three friction arms are calculated from the same gross mid-to-mid move:

- base: observed round-turn spread + `$8/lot` commission + `1.0 * entry_spread`
  round-turn slippage;
- x1.5: exactly `1.5` times the full base friction;
- x2: exactly `2.0` times the full base friction.

This conservative offline cost model is not a claim about live fill quality.
The later native MT5 Model-0 run must independently include broker spread and
commission and be stressed through AlphaFactory.

## Primary and falsification comparator

- Primary uses the frozen `primary_direction`.
- Reverse uses the frozen exact `reverse_direction` on identical completed
  events and clocks.
- Both use the same executable ticks and cost model.  No threshold, distance,
  option family, weekday, session, side, or OI-size filter is permitted.

## Frozen DESIGN gates

All must pass for `ECONOMIC_DESIGN_PASS`:

1. target coverage at least 95% of 508 and at least 200 completed trades;
2. aggregate base PF strictly greater than `1.30` and expectancy strictly
   positive;
3. x1.5 PF at least `1.25` with positive expectancy;
4. x2 PF at least `1.00` with nonnegative expectancy;
5. every calendar year 2018, 2019, 2020, 2021, and 2022 has positive base net
   PnL and at least 30 completed events;
6. maximum fixed-lot closed-trade equity drawdown no more than 8% of the frozen
   `$100,000` reference balance;
7. top 5% profit concentration no more than 30% of gross positive base profit;
8. primary base PF and expectancy are both strictly better than exact reverse;
9. completed-event cadence averages at least 1.5 per calendar month and at
   least one event completes in at least 48 of the 60 DESIGN months.

Failure kills this exact mapping.  The result may be diagnosed but may not be
rescued by post-hoc filters or altered clocks/costs.

## Authorization boundary

This preregistration authorizes only read-only acquisition of the exact
FivePercent EURUSD DESIGN entry/exit tick windows and the frozen offline primary
and reverse calculation.  It does not authorize 2023-current option/futures
validation acquisition, MQL5, MT5 backtesting, optimization, paper deployment,
live deployment, or an edge claim.

`engineering-valid` here means source, futures and EURUSD tick/clock contracts
are mechanically satisfied.  `economic-valid` requires every frozen DESIGN
gate.  `promotion-ready` remains impossible until untouched validation,
MQL5/MT5 parity, robustness, risk, execution and live-operational gates pass.
