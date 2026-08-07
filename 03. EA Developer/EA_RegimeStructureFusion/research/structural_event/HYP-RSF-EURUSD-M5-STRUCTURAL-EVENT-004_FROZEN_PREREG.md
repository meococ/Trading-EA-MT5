# HYP-RSF-EURUSD-M5-STRUCTURAL-EVENT-004 — frozen preregistration

## Research question

Can a closed-bar structural displacement event followed by a later retest and
reclaim produce positive EURUSD M5 expectancy, where the killed
`ROLE-AWARE-003` mechanism treated lagged indicator consensus as a forecast?

This is a fresh causal mechanism, not a parameter rescue. Design evidence is
limited to the eight preselected native MT5 best/worst route pairs documented
in `HYP-RSF-EURUSD-M5-ROLE-AWARE-VISUAL-004_RESULT.md`. The complete 2018-2022
development block is design-exposed. No 2023-current validation or holdout data
is authorized under this ID.

## Frozen causal engine

One setup may be armed at a time. `InpUseStructuralEventSequence=true` is
mutually exclusive with the same-bar, temporal and role-aware engines.

1. Read TB buffer 27 only from the most recently completed M5 candle.
2. A bullish/bearish BOS or MSS is eligible only when that exact candle also
   has same-direction TB displacement and the new TB bias agrees.
3. Store the broken level and the protected trail on the event bar. Return
   without entering; the event candle can never submit an order.
4. During the next eight completed M5 candles, require a later candle to touch
   within `0.15 ATR` of the broken level and close back on the event side.
5. Reject a reclaim extended more than `0.35 ATR` from the break, or a close
   beyond the MBB outer band by more than `0.35 ATR`.
6. Cancel after a `0.20 ATR` close-through failure, a protected-level breach,
   an opposite structural event, expiry, or a hostile veto.
7. Stop is beyond the stored protected level plus the unchanged `0.10 ATR`
   structure buffer, subject to the existing spread and `0.35-4.0 ATR` bounds.
8. Target is the nearer of fixed `1.50R` and an opposing live TB swing already
   known at decision time. A known swing must leave at least `1.25R`; when no
   opposing live swing exists, the event is treated as open air to `1.50R`.

The soft high/low visible after a winning exit is not available at entry and is
explicitly forbidden as an objective. Only closed buffers available on the
decision bar may affect geometry.

## Indicator roles

- **TB SMC:** sole source of direction, causal event, broken level, protected
  invalidation and any live opposing objective.
- **MBB:** location veto only; it cannot arm or trigger.
- **AIRD + VRC:** a trade is vetoed only when both independently indicate a
  strongly opposite directional state. This conjunctive veto avoids letting
  lagged regime labels suppress every fresh MSS.
- **QQE:** never triggers and never requires a zero cross. It cancels only when
  both lines exceed `3.0` in the opposite direction and accelerate farther
  against the setup on the reclaim candle.

## Frozen controls

- Symbol/timeframe/context: EURUSD M5 with M15 AIRD/VRC context.
- Development window/model: 2018-01-01 through 2022-12-31, Model 0.
- Sessions: London plus overlap; both directions; BOS and MSS routes. Range
  mode is disabled because this hypothesis contains no range event.
- Risk: 0.20%; high-vol risk scale 0.50; maximum daily/account loss, cooldown,
  holding limit, Friday flatten and spread controls unchanged.
- New mechanism parameters:
  - `InpStructuralExpiryBars=8`
  - `InpStructuralRetestToleranceAtr=0.15`
  - `InpStructuralInvalidationAtr=0.20`
  - `InpStructuralMaxExtensionAtr=0.35`
  - `InpStructuralMinObjectiveR=1.25`
  - `InpStructuralQqeVetoThreshold=3.0`
- Existing structural constants remain unchanged: TB swing 5, displacement
  `0.45 ATR`, structure buffer `0.10 ATR`, reward/risk `1.50`.
- Telemetry: lifecycle-v3 trade-only plus structural funnel counters.
- Exactly one development run. No parameter sweep, session deletion,
  direction deletion, BOS/MSS route deletion, year selection or timezone
  selection is authorized under this ID.

## Development gate

Raw PF below 1.00 or non-positive mean achieved R is an immediate kill before
cost/robustness work. Otherwise the registered project gates apply: PF > 1.30
after verified x1 cost, 2-5 executed trades per elapsed calendar week, DD <= 8%,
x1.5 cost PF >= 1.25, x2 PF >= 1.00, and Monte Carlo p95 DD within budget.
A development pass only authorizes a fresh cross-symbol and non-overlapping
validation campaign; it never authorizes promotion.

## Anti-overfit boundary

The paired charts authorize event order and role separation only. They do not
authorize selecting their dates, results, hours, weekdays, directions, years
or profitable route. Any logic/threshold change after the first economic
readout requires a new hypothesis ID and increments trial debt.
