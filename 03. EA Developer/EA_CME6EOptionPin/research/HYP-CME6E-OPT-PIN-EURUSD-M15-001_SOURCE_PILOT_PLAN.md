# HYP-CME6E-OPT-PIN-EURUSD-M15-001 — source pilot plan

Status: frozen before any option definition/statistics payload or EURUSD outcome
is opened.

## Hypothesis boundary

The candidate information object is the last strictly lagged official CME Euro
FX option open-interest surface by strike before an option-expiration decision.
It is not signed option demand.  Calls and puts are added as unsigned open
interest at the same strike.  The proposed later trade points EURUSD toward the
unique maximum-open-interest strike during the final closed M15 interval before
the official option expiration/fixing clock.

This pilot is source semantics only.  It cannot calculate a target return, PnL,
profit factor, expectancy, drawdown, or any other economic result.  It cannot
authorize MQL5, MetaTrader, validation, holdout, optimization, paper, or live
trading.

## Primary-source clock contract

- CME SER-8206 changed the covered FX-option expiration time from 14:00 Chicago
  time to 09:00 Chicago time for option contracts expiring after 2019-06-09.
- The pilot is the Friday Week-2 EUR/USD option expiration on 2019-07-12.
- Parent smart symbol: `2EU.OPT`, `stype_in=parent`.
- Official expiration: 2019-07-12 09:00 America/Chicago =
  `2019-07-12T14:00:00Z`.
- Frozen decision: end of the fully closed target M15 interval at
  `2019-07-12T13:45:00Z`.
- Last completed CME trade date for the strict-lag OI gate: `2019-07-11`.

## Exact source requests

Dataset is `GLBX.MDP3`, DBN encoding, Databento SDK `0.55.1` and DBNv3 runtime.
The two requests use the same parent symbol and interval:

- `definition`: `2EU.OPT`, parent symbology,
  `[2019-07-11T00:00:00Z, 2019-07-12T13:45:00Z)`;
- `statistics`: `2EU.OPT`, parent symbology,
  `[2019-07-11T00:00:00Z, 2019-07-12T13:45:00Z)`.

Before either payload request, call `metadata.get_cost` and
`metadata.get_billable_size` once per schema.  Do not acquire if the combined
live quote is not finite, is negative, or is greater than or equal to USD 10.
The Owner standing authority covers this exact frozen in-scope campaign only
while the combined quote is strictly below USD 10.  There is no subscription,
auto-renewal, live-capital, or split-purchase authority.

## Deterministic point-in-time algorithm

1. Reconstruct point-in-time option definitions as of the decision.  Keep only
   outright call/put instruments belonging to `2EU.OPT` whose source-defined
   last-trade/expiration date is 2019-07-12, with finite positive strike.
   Strategies, user-defined instruments, duplicates, and instruments with
   missing class/strike/expiry are excluded and counted.
2. Keep only statistics records with `stat_type=9` (open interest), finite
   nonnegative `quantity`, `ts_event < 2019-07-12T13:45:00Z`, and
   `ts_ref <= 2019-07-11T00:00:00Z`.
3. Map by instrument identity and retain the latest admissible `ts_event` per
   option instrument.  A later record, even if more complete or final, is
   forbidden.
4. Sum call and put OI by exact strike.  A unique maximum defines the source-only
   pilot pin strike.  Empty surfaces and ties are fail-closed.  No target price
   is read by this pilot, so no trading direction is produced.

## Pilot gates

All gates must pass:

- the parent resolves to nonempty actual option instruments;
- decoded definitions contain at least one outright call and one outright put
  expiring on 2019-07-12, with finite strikes and stable instrument identity;
- decoded statistics contain at least one admissible option-level OI record for
  both calls and puts;
- every selected OI record satisfies the strict decision and reference-date
  inequalities above;
- the aggregated surface has a unique maximum-OI strike;
- no payload record after the decision is read;
- raw DBN payloads, request arguments, quote receipt, manifest, counters, and
  every artifact SHA-256 are persisted under `D:`.

Failure is `KILL_SOURCE_PILOT` for this exact mapping.  Do not rescue it by
changing expiry family, date, clock, OI lag, call/put treatment, strike tie rule,
or source after the readout.

## Later frozen candidate boundary (not authorized by this pilot)

- DESIGN: 2018-01-01 through 2022-12-31.
- Validation: 2023-01-01 through 2024-12-31, sealed.
- Holdout: 2025-01-01 through latest verified data, sealed.
- Covered option expirations at or before 2019-06-09 use the official 14:00 CT
  clock; later covered expirations use 09:00 CT.  Decision is the preceding
  fully closed M15 boundary and exit is the expiration boundary.
- Unique pin above target mid means BUY; below target mid means SELL; equality,
  tie, missing timely OI, or overlapping expiration means no trade.
- No proximity/OI/magnitude threshold, expiry-type/weekday filter, direction
  change, SL/TP, hold grid, session grid, or outcome-derived rescue.
- Later economic gates remain PF greater than 1.30 at base cost, PF at least
  1.25 at 1.5x cost, PF at least 1.00 with nonnegative expectancy at 2x cost,
  independently positive DESIGN/validation/holdout, reverse inferior, maximum
  drawdown at most 8%, top-5% profit concentration at most 30%, and the canonical
  DSR/PBO/WFA/Monte-Carlo/recovery gates.

