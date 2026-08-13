# HYP-QPF-EURUSD-M1-001 — frozen quote-path fidelity preflight

Status: `FROZEN_SOURCE_ONLY_NO_OUTCOME` on 2026-08-12.

## Purpose and identity

- EA: `EA_QuotePathFidelityProbe`; symbol/timeframe: `EURUSD` M1.
- Tester: MT5 Strategy Tester Model 0 / every tick based on real ticks through
  `02. AlphaFactory/alpha.ps1`.
- Window: 2018-01-01 through the latest complete day available. This probe may
  inspect source fidelity across the full window because it records no future
  return, trade, PnL, balance, equity, MFE or MAE.
- It is a capability check, not a trading hypothesis. Passing it authorizes only
  a new preregistered economic child with a fresh ID.

## Frozen observable set

For each causal `MqlTick`, the probe records five-minute aggregates of Bid/Ask
validity, millisecond clock order, exact duplicate quotes, Bid-only/Ask-only/both
side changes, mid-price direction, spread changes, inter-arrival buckets, long
duplicate/constant-spread runs, flags and volume diagnostics. A bucket is written
only after a later bucket begins. No price after the bucket is consumed.

This is distinct from the killed XAU spread-dislocation and TickFlow CVD objects:
it does not define a signal, direction, absorption threshold or economic outcome.
It asks only whether historical EURUSD real ticks preserve enough independent
quote-path information to support a future microstructure hypothesis.

## Simultaneous source gates

All gates are evaluated without returns:

1. Report History Quality is at least 97%, the report/model is real-tick Model 0,
   and every calendar year from 2018 to the latest complete year is represented.
2. Source, EX5, config and report are hash-bound by the AlphaFactory run snapshot;
   compile receipt is fresh with 0 errors and 0 warnings.
3. Zero orders/deals/positions and no trading API call in source or telemetry.
4. Invalid/crossed quote share is at most 0.10%; reverse millisecond clock count
   is zero; positive timestamp coverage is 100%.
5. At least 95% of active five-minute buckets contain 20 valid quote changes.
6. Exact duplicate quote share is below 5% of valid quotes.
7. Independent one-sided quote updates `(bid_only + ask_only) / quote_changes`
   are at least 5%, and spread changes are at least 1% of valid transitions.
   These gates prevent a mid-price-only synthetic stream from masquerading as
   Bid/Ask microstructure.
8. No single year fails gates 4-7. A pooled pass cannot hide a bad year.
9. Telemetry contains no outcome or economic field and the final open bucket is
   omitted.

Verdicts:

- `PASS_QUOTE_PATH_FIDELITY_MAY_RESEARCH_CHILD`
- `KILL_QUOTE_PATH_FIDELITY_EXACT_EURUSD_METATICKS`

There is no threshold relaxation, alternate symbol, shorter-history rescue or
economic test under this ID after the verdict.
