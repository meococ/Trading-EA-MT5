# HYP-PVPR-EURUSD-M15-002 — Frozen integer-boundary source revision

Status: frozen before HYP002 source access. Parent HYP001 opened no outcome but
its source PASS is invalid because one serialized equality-boundary row violated
the strict outside-open predicate.

## Exact inherited mechanism

HYP002 inherits the complete market mechanism, data source, profile/value-area
construction, Tue–Fri eligibility, `07:00–16:00 UTC` window, first-event state,
exact-next mapping, DESIGN window and source gates from:

- `HYP-PVPR-EURUSD-M15-001_FROZEN_SOURCE_PREREG.md`
  SHA256 `D90C770EF74F3D582B27FB5A16AE138BA710A8E4CD727988C4859983B6076342`.

The only semantic change is numeric representation of price-boundary tests:

- broker point is exactly `0.00001`;
- `price_points(x) = floor(x / 0.00001 + 0.5)` for positive prices;
- each 1-pip profile bin `b` maps to exactly `10*b` broker points;
- LONG iff `open_points < VAL_points` and
  `VAL_points <= close_points <= VAH_points`;
- SHORT iff `open_points > VAH_points` and
  `VAL_points <= close_points <= VAH_points`;
- exact equality never emits;
- the ledger persists all open/close/POC/VAL/VAH integer point fields so the
  strict predicate can be replayed without float inference.

Everything else is unchanged. No paid/external data, MQL5, MT5, post-event OHLC,
trade, return, cost, PF, optimization, validation or holdout is authorized.

## Frozen gates and verdicts

The exact eleven HYP001 source gates remain unchanged. One attempt only:
`PVPR002-SOURCE-001`.

- All pass: `SCREENED_SOURCE_PASS_MQL5_BUILD_AUTHORIZED`.
- Any fail: `PARK_SOURCE_FEASIBILITY_EXACT_PRIOR_DAY_VOLUME_PROFILE_REENTRY_INTEGER_POINTS`.

A pass permits one separately reviewed MQL5 correctness/parity implementation
and one untuned baseline. It does not establish economic edge.

## No rescue

HYP002 cannot change bin width, value-area percentage/expansion/ties, profile
completeness, weekday/session, event count, symbol, direction, clock or any
threshold. Another equality representation or same-ID retry is forbidden.
