# HYP-PORTFOLIO-COMPOSE-001 Exact-Universe Preregistration Draft

Date: 2026-07-11  
Status: `DRAFT / NOT FROZEN / OUTCOME ACCESS FORBIDDEN`  
Current authorization: `PHASE 0 EXACT-UNIVERSE AND ARTIFACT SUFFICIENCY ONLY`  
Phase 1+: `BLOCKED`

This is a non-outcome Phase 0 draft. It defines how an exact, hash-bound input
universe must be created before any portfolio result is read. It does not
authorize sleeve selection, return aggregation, correlation/overlap analysis,
an outcome screen, an EA change, a compile, an MT5 backtest, or a portfolio
verdict.

## Identity

- Hypothesis ID: `HYP-PORTFOLIO-COMPOSE-001`
- Parent candidate: none; future components must retain their own hypothesis
  and run identities.
- Feature family: fixed-universe portfolio composition.
- Artifact root under review: `02. AlphaFactory/runs/`.
- Registry state on creation: `idea/pending` routing metadata only, with empty
  run IDs and null outcome metrics; no probe or execution state is asserted.
- Exact-universe status: `NOT ENUMERATED / NOT HASHED / NOT FROZEN`.
- Source provenance: the reachability question recorded in
  `../20260711_CODEX_EXECUTION_PLAN_V1.md`, narrowed by
  `../20260711_CODEX_EXECUTION_PLAN_V2.md`, the research doctrine, and the
  portfolio-sleeve gates.

## Thesis — Not Yet Frozen

Prospective question: can a fixed set of structurally valid, independently
identified sleeves form a book that meets the Owner's economics, elapsed-week
cadence, exposure, cost-stress, and drawdown requirements without one component
dominating the result?

Phase 0 does not answer that question. It asks only whether the exact universe
and required synchronized evidence can be fixed without reading outcomes.

## Evidence-Class Limitation

V1 inherited a portfolio audit that had already inspected outcomes and proposed
selecting “PF > 1.30” and the “per-EA best run.” Those are outcome-based
selection rules. V2 withdraws them as prospective eligibility rules.

Any later analysis that intentionally inherits an outcome-selected list must be
labeled exploratory reachability evidence and cannot confirm a sleeve, validate
a portfolio, or provide an untouched holdout. A clean test would require an
independently fixed universe and untouched evidence window.

## Exact-Universe Contract

Before this draft can be frozen, one canonical inventory must enumerate every
input member. The inventory is part of the preregistration evidence and must
contain exactly these non-outcome fields:

| Field | Requirement |
|---|---|
| `universe_member_id` | Stable `<ea_name>/<run_id>` identifier |
| `run_root` | Exact repo-relative active run path |
| `ea_name`, `run_id` | Directory identity plus manifest/config identity check |
| `canonical_main_file` | Exact active repo-local `.mq5` entrypoint |
| `source_sha256`, `compiled_sha256`, `config_sha256`, `report_sha256` | Identity hashes; missing remains explicit |
| `trade_series_path_sha256` | Raw closed-position/lifecycle series path and hash, without row values in the inventory |
| `equity_series_path_sha256` | Common-calendar equity/return series path and hash, without row values in the inventory |
| `cost_artifact_path_sha256` | Verified cost artifact and raw provenance paths/hashes, or explicit missing state |
| `symbol`, `suffix`, `timeframe`, `model`, `from`, `to` | Declared configuration identity only |
| `broker_server_account_currency_fingerprint` | Hash/fingerprint only; no private raw account identifier |
| `duplicate_group` | Structural duplicate/collision group derived from identity hashes |
| `structural_status` | `eligible`, `alias`, or `invalid`, with a non-performance reason |

The inventory must be sorted bytewise by normalized
`(ea_name, run_id, run_root)`, serialized in one canonical form, and assigned an
`universe_sha256`. The freeze record must include the inventory cutoff in UTC
and Git/worktree snapshot. New or changed run directories after that cutoff are
outside the hypothesis and require a new draft or amendment before outcome
access.

The exact member list and `universe_sha256` are currently unset. Therefore the
hypothesis is not frozen and no result reader may be run.

## Outcome-Blind Structural Rules

Phase 0 may classify a run using identity and provenance only:

1. Include only an active `02. AlphaFactory/runs/<EA>/<run_id>` directory with
   one internally consistent EA/run identity and required file identities.
2. Exclude archive/progress/control namespaces from membership, while recording
   them as excluded roots.
3. Mark a cross-EA source/config/report identity mismatch `invalid`; never
   repair it by relabeling performance output.
4. Group byte-identical config/report/trade evidence as duplicates. Select the
   canonical alias by lexicographically smallest `(ea_name, run_id)` unless a
   different outcome-independent rule is frozen before access.
5. Do not choose a member because it has higher PF, net, cadence, lower
   drawdown, a preferred year, or a favorable validation label.
6. If multiple nonduplicate variants remain in one EA/family, either keep all
   as a declared tried family or choose one using a prospectively frozen,
   non-outcome identity rule. “Best run” is forbidden.
7. Freeze the exact candidate combinations and weight rule before any
   performance series is opened. An unrestricted search for “any combination”
   is forbidden unless the complete family and a multiple-testing correction
   are preregistered.

## Per-Member Artifact-Sufficiency Gate

Membership in the identity inventory is not evidence sufficiency. Before
freezing a future outcome plan, every proposed component must have:

- canonical hypothesis/prereg/run-role provenance and exact source, compiled,
  input, report, and run-manifest hashes;
- raw, timestamped closed-position returns in a common account/risk unit, with
  position/deal identities and no inferred duplicate trades;
- a common-calendar equity or mark-to-market return series sufficient to
  measure simultaneous exposure and drawdown, not only closed-trade totals;
- elapsed-calendar window identity and a deterministic alignment timezone;
- report-bound, same-venue cost evidence with spread, commission, swap, fee,
  slippage, and currency conversion provenance; missing or zero values are not
  free costs;
- overnight/weekend exposure fields under a common frozen definition;
- enough information to distinguish independent sleeves from the same source,
  configuration, trade stream, or duplicated run; and
- complete coverage for the intended common train and holdout windows.

The Phase 0 sufficiency matrix may record only `present`, `missing`,
`malformed`, `identity-mismatch`, or `not-applicable`, plus paths, hashes,
headers, and reasons. It must not include performance values.

## Outcome Fields Forbidden In Phase 0

Do not read, copy into the inventory, rank by, or compute:

- trade P&L/R, wins/losses, equity points, PF, expectancy, net, cadence,
  drawdown, recovery factor, concentration, or validation verdicts;
- daily P&L correlations, same-time/same-day trade overlap, concurrent margin,
  portfolio exposure, or portfolio Monte Carlo;
- cost-stressed results or any combined return;
- candidate weights, a winning subset, an efficient frontier, or a “best”
  combination; or
- subgroup, year, month, session, symbol, direction, or regime results.

Schema/header presence and artifact hashes are allowed. Row values and derived
metrics are forbidden. If a tool cannot enforce this separation, it must not be
used.

## Future Composition Design — Placeholder, Not Authorization

The following must be completed and frozen before a future Phase 1 outcome
screen:

- exact member IDs and `universe_sha256`: `UNSET`;
- exact allowed combination list and family size: `UNSET`;
- weight/risk normalization and rebalance rule: `UNSET`;
- common calendar, timezone, missing-return, and non-overlap rule: `UNSET`;
- daily P&L correlation and trade-overlap definitions: `UNSET`;
- train and untouched holdout windows: `UNSET`;
- cost aggregation and x1/x1.5/x2 rules: `UNSET`;
- combined exposure, cadence, concentration, and Monte Carlo risk gates:
  `UNSET`;
- multiple-testing correction for every tried combination: `UNSET`;
- run budget under current approval: `0` outcome screens, `0` compiles, `0`
  backtests.

The canonical gates already require at least two independently confirmed
component IDs, hash-bound correlation/exposure and overlap audits, portfolio
Monte Carlo within budget, cost PF x1.5 at least 1.25, and cost PF x2 at least
1.00 for `portfolio-sleeve` status. A research reachability screen over
unconfirmed shelf artifacts cannot satisfy that promotion boundary.

## Phase 0 Deliverables

Phase 0 may produce only:

1. one exact candidate list; the current legal list is explicitly empty and
   must block on `EXACT_UNIVERSE_NOT_FROZEN`; a non-empty canonical inventory
   and `universe_sha256` are future clearance requirements;
2. the outcome-blind duplicate/collision map;
3. the per-member artifact-sufficiency matrix;
4. a contamination note identifying any list inherited from earlier
   outcome-selected evidence; and
5. a blocker memo stating whether a future prereg can be completed without
   inventing data.

These deliverables contain no portfolio result and cannot transition the
hypothesis beyond draft.

## Phase 0 Failure And Exit Rules

Phase 0 fails closed if the exact universe cannot be enumerated, identity
collisions cannot be resolved structurally, required synchronized/cost artifacts
are missing, or an inventory step would require opening outcomes. That result is
an evidence blocker, not a portfolio kill.

The draft can be proposed for freezing only after:

1. the exact list, cutoff, canonical serialization, and `universe_sha256` are
   recorded;
2. the structural and artifact-sufficiency matrices are complete and contain no
   outcome fields;
3. the future combination family, weighting, alignment, cost, split,
   multiple-testing, and kill rules are complete prospectively;
4. the existing Phase 0 `idea/pending` row remains validator-clean, and any
   later execution row or transition is separately authorized; and
5. a clean independent freeze review avoids both the prior outcome-selected
   portfolio audit and the accidentally displayed donor `RunMeta` summary; and
6. the Owner explicitly authorizes Phase 1 after reviewing the Phase 0 exit
   packet.

Until all six conditions hold, the controlling status remains:

`DRAFT / NOT FROZEN / OUTCOME ACCESS FORBIDDEN`
