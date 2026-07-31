# HYP-TRILAG-EURJPY-M1-002 — Frozen DESIGN Structural-Feasibility Plan

- Parent: `HYP-TRILAG-EURJPY-M1-001`
- Status: `FROZEN_DESIGN_EXPORT_AND_EVALUATOR_BUILD_ONLY`
- Frozen at: `2026-07-29T14:38:00Z`
- Economic status: `NOT_AUTHORIZED`
- MQL5 / Model 0 / optimization: `NOT_AUTHORIZED`
- Validation / holdout / paper / live: `NOT_AUTHORIZED`

## Question

Does a completed-bar, exact triangular-identity translation produce a
source-valid population with enough natural cadence and enough decision-time
displacement to justify one later economic falsification?

This child may read DESIGN close prices but may not read any post-entry path,
simulate a trade, compute a return after the decision, or report PF/PnL.

## Parent binding

The parent one-shot inventory passed all 8 structural gates without decoding
HCC semantics:

- attempt terminal SHA-256:
  `208E89558566E477EFA350A912EEDD41880DF5F5CD0EA7AD1C60B604AA96263B`
- source inventory SHA-256:
  `899B874074A3DFAAE477CDD66E135420059FF0D220FED5BB68E25A87ED753541`
- exact source set: `EURUSD`, `USDJPY`, `EURJPY`, annual HCC 2016–2024.

## Split and access boundary

- DESIGN source export/evaluation: `2016-01-01 00:00:00 UTC` through
  `2020-12-31 23:59:59 UTC` only.
- Internal validation: `2021-01-01` through `2024-12-31`, sealed.
- Research holdout: every `2025+` payload, sealed and forbidden.
- One export attempt: `TRILAG002-DESIGN-EXPORT-001`.
- One structural evaluation attempt, only after the export is independently
  reviewed and hash-bound: `TRILAG002-DESIGN-STRUCTURE-001`.

No request may include a bar timestamp in 2021 or later. The exporter must
record exact requested bounds and zero later bars requested/exported.

## Outcome-blind export contract

Use the configured D-portable FivePercent terminal and the standard
MetaTrader5 Python bridge only for a read-only `copy_rates_range` export.
Export exactly these fields:

- `symbol`
- `time_utc` — M1 bar-open UTC timestamp
- `close` — observed broker Bid close of that completed M1 bar

Forbidden export fields: `open`, `high`, `low`, future bar, target, stop,
spread-based outcome, trade return, label, signal, PF or PnL.

Requirements:

- exact symbols only, exact M1 timeframe, exact DESIGN bounds;
- timestamps strictly increasing and unique within symbol;
- close finite and positive;
- no forward fill, interpolation or synthetic bar;
- D-side parquet plus canonical manifest, both create-new and SHA-bound;
- terminal/company/server/build, requested range, observed first/last timestamp,
  per-symbol rows and pip size recorded;
- `2021+` bars requested/exported = 0;
- MT5 launches = 1 for the one export; orders submitted = 0.

## Frozen decision-time construction

All calculations use an inner join on the exact same observed M1 `time_utc`.
No nearest-time match and no forward fill are allowed.

For each common completed bar `t`:

1. `r_eu(t) = log(EURUSD_close(t) / EURUSD_close(t-1))`
2. `r_uj(t) = log(USDJPY_close(t) / USDJPY_close(t-1))`
3. `r_ej(t) = log(EURJPY_close(t) / EURJPY_close(t-1))`
4. `u(t) = r_eu(t) + r_uj(t)` — the two-leg implied EURJPY change.
5. `sigma_u(t)` = sample standard deviation of `u` over the strictly prior
   1,440 common returns, shifted by one bar; minimum 1,400 finite observations.
6. `z(t) = abs(u(t)) / sigma_u(t)`.
7. `gap(t) = u(t) - r_ej(t)`.
8. `gap_pips(t) = abs(expm1(gap(t))) * EURJPY_close(t) / 0.01`.

A raw event exists only when all conditions hold:

- `z(t) >= 3.00`;
- `r_eu(t)` and `r_uj(t)` are nonzero and have the same sign;
- each lead contribution is at least 25% of `abs(u(t))`;
- `abs(r_ej(t)) <= 0.25 * abs(u(t))`;
- `sign(gap(t)) == sign(u(t))`.

Direction reserved for a later child is `sign(u(t))` on EURJPY. This source
stage records the direction but does not enter or evaluate it.

## De-clustering

Sort raw events by completed-bar decision time `time_utc + 60 seconds`.
Accept the first event. A later event is accepted only when its decision time
is at least 60 elapsed minutes after the last accepted event. Equality is
allowed. Cooldown is global because the execution leg is always EURJPY.

No hour/session/day/month/year filter, news veto or threshold refit is allowed.

## Frozen structural gates

All gates must pass together:

1. Manifest/data SHA chain, exact schema and one authorized export reconcile.
2. Per-symbol timestamp uniqueness and positivity pass with no repaired bars.
3. Common timestamp count divided by each symbol count is at least `0.990`.
4. Accepted-event cadence is `2.0–5.0` per elapsed calendar week across the
   exact DESIGN span.
5. LONG and SHORT each contain at least 100 accepted events and each represents
   at least 25% of accepted events.
6. No single calendar year contains more than 30% of accepted events.
7. Median accepted-event `gap_pips >= 5.0` and 25th percentile
   `gap_pips >= 2.5`.
8. Both residual signs occur; every event is exactly reproducible and the
   event ledger SHA is stable under independent replay.
9. Post-decision bar reads, future-path labels, trade simulations, costs, PF,
   expectancy, drawdown and economics remain zero/false.
10. Validation/holdout access, MQL5, Model 0, network and paid requests remain
    zero/false.

Elapsed weeks are `(last common time - first common time) / 7 days`; active
weeks are forbidden as the denominator.

## Decisions

- PASS: `PASS_DESIGN_STRUCTURE_FUTURE_ECONOMICS_PREREG_ONLY`.
- Any source/integrity failure:
  `ENGINEERING_INVALID_NO_MARKET_VERDICT`.
- Any cadence/balance/concentration/displacement failure with valid source:
  `KILL_DESIGN_STRUCTURE_NO_ECONOMICS_AUTHORITY`.

A source PASS authorizes only a fresh economic child plan. It does not
authorize MQL5, Strategy Tester, optimization, validation, holdout, promotion,
paper or live execution.

## De-dup and later control burden

This exact M1 triangular identity is distinct from prior H1/H4 same-bar
consensus and USD-majority lag-follow objects, but it remains in the broader
lead-lag family. A later economic child must compare against the locked prior
peer-accept / USD-consensus / laggard-catch-up controls on the same eligible
population. It must not use the post-event toxic/non-toxic label from the
literature, flip direction after a loss, delete years/sessions, or retune
`3.00`, `25%`, `1,440` or `60 minutes` under this ID.

