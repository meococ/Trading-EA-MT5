# HYP-ARUC-EURUSD-M15-003 — Source Feasibility Plan

Status: `FROZEN_PRE_OUTCOME_ENGINEERING_CHILD`

## Identity and failure radius

- Hypothesis: `HYP-ARUC-EURUSD-M15-003`
- Parent candidate: `HYP-ARUC-EURUSD-M15-002`
- Attempt: `ARUC003-SOURCE-ATTEMPT-001`, limit exactly one.
- Family: `activity-response-underreaction-continuation`.
- Symbol/timeframe: FivePercent `EURUSD`, M15 decisions, H1 BID volatility.

The exact `-002` source-feasibility attempt exceeded 3,600 seconds with zero
report bytes and zero stderr bytes. It emitted no outcomes and did not evaluate
the market. Static inspection localized the failure to repeated construction of
full business-date and bar indexes inside each eligible decision-slot call.
The parent is terminal for that exact engineering attempt only.

This fresh child repairs computation only. No market mechanism, threshold,
date, symbol, timeframe, source, data hash, causal feature, control, horizon,
Stage-0 gate, permission or prohibition changes. This is not a post-hoc market
rescue and creates no economic authority.

## Unchanged public DESIGN and research contract

The allowed public DESIGN sequence remains `2016-01-04` through `2020-12-31`:
1,555 ordered manifest dates, 1,298 Monday-Friday decision dates and 257 Sunday
history dates, with no Saturdays. M1 remains exactly 1,859,820 DESIGN rows from
`splitvault_002`; H1 BID remains exactly 31,057 DESIGN rows backed by 71,785 raw
source rows from `h1_splitvault_002`. Every receipt, manifest, immutable-source,
schema, one-row-group, SHA, byte-count, timestamp, timezone and public-path
check is identical to `-002`.

PRIMARY, PRICE_ONLY and SHIFTED_TICKS retain their exact closed-bar causal
definitions. Timestamp-only horizons, elapsed-calendar-week cadence and outcome
blindness remain unchanged. Stage-0 still requires cadence 2-5 per week, at
least 25% each LONG and SHORT, no year over 30%, formation and executable
horizon ratios at least 0.99, median `1.50 pip / SL_pips <=0.25`, and at least
20 PRIMARY signals per side. Only PRIMARY feeds those gates.

## Frozen computation repair

Production scan must prepare exactly once per source scan:

1. one immutable, validated business-date tuple;
2. one immutable `date -> ordinal` lookup;
3. one validated `(date, UTC slot) -> complete M15 bar` lookup.

Every eligible decision then reuses those objects. Activity remains the current
slot divided by the median of exactly 20 prior business-date slots. SHIFTED_TICKS
still uses current price signs with volumes from exactly five business dates
earlier and its activity ratio remains evaluated on that shifted source date.
The repaired inner path performs bounded O(20) or O(1) lookups and never calls
`Sequence.index` or reconstructs the full bar index per signal.

Public helpers retain their synthetic-test behavior by validating and building
indexes for standalone calls, while production uses indexed internal helpers.
Duplicate/malformed dates, slots, bars and lookup inconsistencies remain
fail-closed. Randomized/synthetic parity must prove identical PRIMARY,
PRICE_ONLY, SHIFTED_TICKS ledgers and Stage-0 results against the frozen legacy
semantics.

## Canonical generic source-only authority

The exact latest canonical `-003` registry row is the sole frozen run packet;
there is no separate packet file. A future execution requires an explicit run
switch, exact non-`None` `REVIEWED_REGISTRY_ROW_SHA256`, disarmed builder-base
normalization, strict historical-format-tolerant registry parsing, exact latest
raw-row SHA and canonical selected row, and zero errors from the hash-bound
canonical validator/schema before any DESIGN receipt, manifest or shard opens.

- Validator: `04. Memory/research/validate_candidate_registry.py`, SHA256
  `B04B379E11F556A0CF3E6C3264768176310FF01CF360CC3B92464C51A2996DD0`
- Schema: `04. Memory/research/CANDIDATE_REGISTRY.schema.json`, SHA256
  `96C80D3C46A105A9754CA1325F3DD6C160D92A9D5800ECBC402DE0F40C612F5C`

The validation object keeps the exact generic source-only whitelist from
`-002`, with `source_run_authorized=true`, `source_feasibility_only=true`,
`source_build_authorized=false`, attempt limit one, exact attempt/evidence root,
review statuses and receipt/builder/test/clock/data/validator/schema bindings,
and every sealed/source-only capability literal false. Root metrics equal the
canonical zero-runtime contract before execution.

The parent-owned receipt path is
`03. EA Developer/EA_ActivityResponseContinuation/research/HYP-ARUC-EURUSD-M15-003_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json`
with schema `aruc_003_source_implementation_review_receipt.v1`.

## Disarm and prohibitions

The builder sentinel remains exactly `REVIEWED_REGISTRY_ROW_SHA256: str | None = None`.
This implementation task does not create a receipt, append registry authority,
arm the sentinel, open DESIGN data or write evidence. Validation/holdout/private/
sealed, outcomes/returns/PnL/PF/DSR, optimization/economics, network/paid,
MT5/MQL5, promotion/live and registry mutation remain forbidden.
