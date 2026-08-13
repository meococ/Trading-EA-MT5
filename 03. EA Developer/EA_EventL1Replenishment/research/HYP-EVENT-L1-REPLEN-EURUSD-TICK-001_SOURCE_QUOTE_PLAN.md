# HYP-EVENT-L1-REPLEN-EURUSD-TICK-001 — frozen source quote plan

Frozen 2026-08-12 before any new `mbp-1` payload, book feature, EURUSD
outcome, or economic result was read.

## Decision

This is a source-capability probe, not an edge claim and not yet an executable
trading hypothesis. Grok `/deep-research-trading-meta5` returned
`NO_CANDIDATE`: extending trades alone from +15 s to +120 s would reuse the
terminal HYP013 signed-flow family. A materially new post-release
absorption/replenishment object requires continuous top-of-book size as well as
trade prints.

The minimum sufficient Databento schema is `mbp-1`. It contains every update
to the best bid/offer, the BBO price/size/order-count fields, and every trade,
so a separate `trades` request is unnecessary. Official schema references:

- https://databento.com/docs/schemas-and-data-formats/mbp-1
- https://databento.com/docs/api-reference-historical/metadata/metadata-get-dataset-condition

## Frozen population and quote contract

- Dataset/schema/symbol: `GLBX.MDP3` / `mbp-1` / `6E.v.0`.
- Input symbology: `continuous`.
- Clock: Databento `ts_recv`, UTC.
- Population: the canonical 329 high-impact USD/EUR DESIGN clocks in
  2019–2020 from `point_release_clocks_2019_2022.csv`.
- Window per clock: exact half-open `[T+0.000s,T+120.000s)`.
- The 301 clocks in 2021–2022 remain sealed and are not quoted.
- Allowed APIs: `metadata.get_cost(mode="historical-streaming")` and
  `metadata.get_billable_size` only.
- Forbidden: `timeseries`, batch, payload decode, feature construction,
  EURUSD prices/outcomes, economic metrics, MQL5, MT5, optimization, validation,
  paper, live, and promotion.
- One quote attempt, output-exclusive and hash-bound.

The quote records exact per-window cost/bytes and aggregate nonzero coverage.
Databento warns that cost estimates for intervals shorter than ten minutes can
over-report; actual paid bytes therefore remain unknown until a separately
authorized acquisition.

## Outcome-blind source frontier gates

The free quote passes only if all 329 identities return valid nonnegative cost
and size estimates, at least 95% have nonzero billable bytes, and the implied
nonzero population cadence is at least 2 events/week. These gates establish
only that a DESIGN source route exists.

If the quote passes, the cheapest lawful next step is one separately approved
120-second payload for the chronologically first DESIGN clock, `EVT0001`
(`2019-01-03T15:00:00.000Z`). That pilot may inspect only feed semantics:
monotone `ts_recv`, action/side enums, valid BBO price/size fields, trade
presence, and event-driven inter-arrival behavior. It may not read EURUSD
outcomes or select a profitable formula. Full DESIGN purchase remains closed
until a pilot plan and exact Owner cost ceiling are bound to a new identity.

## De-dup and immutable failure radius

- Not HYP013: no direction is inferred from `[0,+15s)` signed flow and no
  trades-only continuation is allowed.
- Not raw-BREAK BOOKSTATE-001/BOOKTRANSITION-002: no M5 break population,
  five-level alignment, or inherited entry/management exists.
- Not EVENT-CLOB-PERSIST-002: no PRE `[T-60,T-15)` or LATE `[T+45,T+60)`
  five-level persistence score is reused, and its one-second gap gate is not
  weakened.

After the quote, the schema, 329 clocks, `[0,+120s)` receive-time window,
minimum 95% nonzero coverage, 2/week cadence floor, and `EVT0001` pilot choice
cannot be changed under this ID. Failure returns `NO_SOURCE_FRONTIER`; it
cannot be rescued by another window, schema, population, threshold, or outcome.

