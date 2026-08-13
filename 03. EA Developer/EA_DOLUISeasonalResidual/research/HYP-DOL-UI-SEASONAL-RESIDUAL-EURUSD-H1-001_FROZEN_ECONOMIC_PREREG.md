# FROZEN ECONOMIC PREREGISTRATION - HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001

Frozen on 2026-08-13 after source attempt `DOLUI001-SOURCE-002` passed and
before any EURUSD target price, return, trade, report, chart or economic metric
for this information object was opened. Grok `/deep-research-trading-meta5`
returned `ECONOMIC_PREREG_PASS`; that answer is advisory. This local contract
is the executable authority and deliberately removes Grok's arbitrary spread
filter, incorrect commission fallback and selected-year gate.

## Hypothesis, source and population

- Symbol/broker: FivePercent `EURUSD`; Strategy Tester period `H1`, Model 0
  every tick; USD 100,000 deposit and 1:100 leverage.
- Source: the official DOL seasonal residual, defined before target outcomes as
  `unadjusted_actual_weekly_change - seasonal_factors_expected_weekly_change`.
- Direction: positive residual `BUY_EURUSD`; negative residual `SELL_EURUSD`;
  zero or unavailable residual `FLAT`.
- Source receipt SHA-256:
  `58AF5CC103F8CFC2CD8D906818736C562E090EC3D3CD361C13903E01E06DB65C`.
- Static CSV SHA-256:
  `3CD5D03DC85309724C5E3E616223657ACBA8DF86D4722F4A7EDAAB068C9009BA`.
- TRAIN is exactly `[2018-01-01, 2023-01-01)`: 260 source releases, 258 usable
  signals, 101 BUY, 157 SELL and the two frozen 2020 unavailable rows FLAT.
- Internal validation `[2023-01-01, 2025-01-01)` (104 source rows) and sealed
  holdout `[2025-01-01, 2026-08-07)` (77 source rows) remain target-price
  inaccessible until their gates are opened in order.

The causal thesis is delayed continuation after the market has had one complete
post-release H1 bar to digest whether unadjusted claims were stronger or weaker
than the contemporaneously published official seasonal expectation. The fixed
four-hour holding horizon tests persistence rather than the immediate 08:30 ET
spread shock.

## Immutable decision and execution contract

1. Convert the official UTC release once to the measured FivePercent server
   clock using the canonical UTC+2 winter / UTC+3 summer EU-DST mapping.
2. Let `decision_open` be the first whole-hour H1 open strictly after the
   release clock. Since every frozen release is at `:30`, this is the next top
   of hour. The decision bar is `[decision_open, decision_open+1h)`.
3. At the first tick at or after `decision_open+1h`, require the just-closed H1
   bar open to equal `decision_open`; enter at market. This is the open of the
   H1 bar after the decision bar. Entry more than five minutes late is a missed
   event and is never retried. No price from the decision bar enters the signal.
4. Exit at the first tick at or after four hours from the scheduled entry open.
   No SL, TP, trailing, partial exit or alternate horizon exists.
5. One position maximum. An entry request or exit request is issued once; a
   reject is logged and never retried. No pyramiding, martingale or netting with
   another symbol is allowed.
6. Fixed exposure sizing only: `equity * 0.25% / (40 pips * pip value per lot)`,
   floored to the broker volume step and hard-capped at 1.00 lot. The 40-pip
   denominator is an exposure convention, not a stop or observed volatility.
7. There is no residual-magnitude threshold, spread gate, session filter,
   direction filter, price confirmation, volatility/regime filter, event subset,
   optimization or parameter grid.
8. Missing/duplicate source identity, missing decision H1 bar, invalid symbol
   geometry, non-finite quote, unexpected position, Friday/weekend entry, or
   table/hash mismatch fails closed. The frozen corpus contains only Wednesday
   and Thursday release dates, so a weekend guard is operational safety rather
   than a selected event filter.
9. The exact sign-reversed comparator changes only direction. It is a negative
   control, can never be promoted and cannot rescue a failed primary.

## Source binding and engineering gates

An outcome-blind generator must reproduce a compile-time TRAIN table from the
exact source CSV and canonical FivePercent clock module. The EA must validate
the source/table hashes, 260 identities, 101/157/2 direction counts, strict
clock ordering, +2/+3 offsets, H1 clock geometry and Wednesday/Thursday release
days in `OnInit`; any mismatch returns `INIT_FAILED`.

Economic interpretation is forbidden if any of these occurs:

- the EA source/contract/table/prereg hash chain is not frozen before the run;
- a signal is evaluated before the official release or before the decision H1
  bar closes, or an entry/exit uses a future bar;
- the run does not account for all 260 source identities, exactly two source
  FLATs, and at least 250 completed trades;
- more than one owned position, wrong symbol/timeframe/hypothesis, unexpected
  disappearance or unclosed position;
- tester bounds differ from `[2018-01-01, 2023-01-01)`, History Quality is
  `<=97%`, or required audit sidecars/journal proof are missing;
- any 2023-present EURUSD price is accessed before TRAIN is terminal.

## Cost and stress contract

For every completed event the audit records entry/exit Bid, Ask, fill, spread,
lots and pip value. The economic ledger reconstructs:

- raw mid-to-mid PnL;
- observed executable spread/fill cost = max(0, raw mid PnL minus executable
  PnL), so price improvement can reduce this component to zero but never create
  a cost credit;
- commission = USD 4.00 per standard lot round trip;
- adverse dynamic slippage = `0.30 * (entry spread + exit spread) * pip value *
  lots`;
- base net = raw PnL minus observed spread/fill, commission and dynamic
  slippage;
- 1.5x and 2x nets multiply the same complete per-trade cost by 1.5 and 2.0.

No spread observation rejects a trade. The tester-native report is engineering
evidence; the hash-bound event ledger is economic authority for cost gates.

## TRAIN acceptance and terminal rule

Primary passes only if every condition holds:

- all 260 source events accounted, exactly two source-FLAT rows and at least
  250 completed trades;
- completed cadence at least 48 trades per full calendar year and at least
  three of five TRAIN years have positive base net PnL;
- base cost PF `>=1.30` and base expectancy `>0`;
- 1.5x cost PF `>=1.25`;
- 2x cost PF `>=1.00` and 2x expectancy `>=0`;
- native equity max drawdown `<=8%`;
- exact reversed-sign comparator has lower base PF and lower base expectancy;
- top 5% of completed trades contribute `<=30%` of gross positive base profit.

Any primary failure economically KILLs this exact mapping. No threshold,
direction, holding-time, stop/target, session, sizing, source subset or same-ID
rerun may rescue it.

If TRAIN passes, a new hash-bound successor may open only 2023-2024 internal
validation with identical logic and minimum 100 completed trades, base PF
`>=1.20`, positive expectancy, 1.5x PF `>=1.05`, lower comparator PF and
expectancy, and max DD `<=8%`. Only if that also passes may a final successor
open the sealed 2025-present holdout; DONE still requires the goal-level PF,
cost-stress, robustness, Monte Carlo, execution and promotion gates. No paper,
live or funded authority is granted here.
