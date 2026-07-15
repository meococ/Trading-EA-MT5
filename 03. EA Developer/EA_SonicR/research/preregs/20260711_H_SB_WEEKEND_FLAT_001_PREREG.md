# HYP-SB-WEEKEND-FLAT-001 Preregistration Draft

Date: 2026-07-11  
Status: `DRAFT / NOT FROZEN / OUTCOME ACCESS FORBIDDEN`  
Current authorization: `PHASE 0 ARTIFACT SUFFICIENCY ONLY`  
Phase 1+: `BLOCKED`

This draft reserves an identifier and defines the evidence needed to freeze a
weekend-flat-only hypothesis. Its canonical registry row is metadata-only at
`state=idea`, `verdict=pending`, with empty run IDs and null outcome metrics.
Neither the row nor this draft authorizes an outcome read, replay, EA edit,
compile, MT5 backtest, or strategy conclusion.

## Identity

- Hypothesis ID: `HYP-SB-WEEKEND-FLAT-001`
- Parent candidate: none; this is A1, a single management intervention.
- EA family: `EA_SilverBullet`
- Canonical main-file contract expected from the runner:
  `03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5`
- Nominated artifact root for sufficiency inspection only:
  `02. AlphaFactory/runs/EA_SilverBullet/20260628_131343`
- Registry state on creation: `idea/pending` routing metadata only; not a frozen
  prereg, probe, execution state, or evidence claim.
- Source provenance: the governance problem and proposed intervention recorded
  in `../20260711_CODEX_EXECUTION_PLAN_V1.md`, narrowed by
  `../20260711_CODEX_EXECUTION_PLAN_V2.md`.

## Scope Separation

A1 contains exactly one prospective change: force eligible open positions flat
before the broker-defined weekend closure according to a frozen, side-aware
time and execution contract.

A1 explicitly excludes:

- a maximum holding time;
- a rollover-flat or zero-overnight rule;
- any entry, signal, session-entry, sizing, stop, target, trailing, break-even,
  or position-count change;
- any parameter scan or alternate Friday cutoff; and
- any inference about a combined weekend-flat plus max-hold intervention.

The V1 identifier `HYP-SB-WEEKEND-FLAT-MAXHOLD-001` is retired and must not be
registered or used on an artifact.

## A2 Boundary

Maximum hold is A2, a separate future child. A2 currently has no hypothesis ID,
registry row, or preregistration. It remains unregistered until a side-aware
price path, historical timezone/session calendar, holding-age definition,
verified cost contract, partial-fill rule, and suppressed-entry counterfactual
contract exist. An A1 pass or failure cannot be treated as an A2 result.

If a combined A1-plus-A2 intervention is ever proposed, it requires a third
preregistration and an interaction-aware matched-control design. It cannot be
constructed by joining the separate readouts after the fact.

## Thesis — Not Yet Frozen

Prospective thesis: a weekend-flat-only rule may satisfy the zero-weekend-cross
exposure requirement without destroying the economics or elapsed-calendar
cadence of an otherwise unchanged matched control.

This thesis is deliberately qualitative at draft stage. No donor outcome,
previously reported subgroup, or result from V1 may be used to choose the
cutoff, tolerance, or split gates. Exact thresholds remain unset until the data
contract is proven sufficient and the draft is reviewed for freezing.

## Locked Design Status

Nothing in this section is frozen yet.

| Design item | Draft requirement | Current state |
|---|---|---|
| Intervention | Weekend-flat only | Defined in scope; implementation forbidden |
| Symbol/timeframe/window/model | Must be copied from an exact matched-control contract, not inferred from a report title | `UNSET` |
| Time authority | Server timezone ID plus historical server-to-UTC conversion and DST rule | `UNPROVEN` |
| Weekend boundary | Exact Friday cutoff and next eligible market-open boundary from the broker session calendar | `UNSET` |
| Decision time | Must be ex ante and must not use a bar close that is unavailable at the decision instant | `UNSET` |
| Long close side | First executable bid under the frozen close protocol | `UNPROVEN` |
| Short close side | First executable ask under the frozen close protocol | `UNPROVEN` |
| Fill/slippage | Independently referenced, side-aware close request and fill contract | `UNPROVEN` |
| Cost | Spread through bid/ask path; commission, swap, fee, and account conversion separately provenance-bound | `UNPROVEN` |
| Missing data | Whole affected split fails; no episode deletion, fill-forward, zero-cost substitution, or synthetic ask | Draft rule, not frozen |
| Counterfactual | Must distinguish truncation-only replay from entries newly eligible after a forced close | `UNPROVEN` |
| Parameter budget | One frozen weekend rule; zero scanned cutoffs | Draft rule, not frozen |

## Phase 0 Artifact-Sufficiency Contract

Phase 0 may inspect only path identity, file size, hashes, manifest/config
identity fields, and schema/header names. No trade-result row, report metric,
equity point, or derived outcome may be opened.

The nominated artifact root is sufficient only if the following can be proven
without outcome access:

1. **Identity:** exact EA, canonical main source, source/config/report hashes,
   symbol suffix, timeframe, model, window, broker/server, and account-currency
   fingerprints are internally consistent.
2. **Time:** every event timestamp has a declared timezone and a reproducible
   conversion to UTC; the historical broker session and holiday calendar can
   identify the weekend boundary without inspecting results.
3. **Executable sides:** chronological bid and ask observations exist at every
   relevant decision/fill instant. A scalar spread or bid-only bar cannot
   synthesize the missing side.
4. **Lifecycle:** position IDs, order/deal IDs, side, volume, partial fills,
   entry time, close request time, fill time, and close status are unambiguous.
5. **Costs:** commission, swap, fee, spread, slippage reference, fill, and
   contemporaneous quote-to-account conversion are provenance-bound. Missing or
   zero fields are never assumed to mean free execution.
6. **Counterfactual eligibility:** pre-entry signal/eligibility and position
   occupancy state are sufficient to determine whether an early Friday close
   would permit later entries. Without this, only a clearly labeled
   truncation-only diagnostic could be contemplated; it could not be a full
   strategy replay.
7. **Coverage:** every affected episode in every future split is covered. Any
   gap fails the split before an outcome summary is created.

Header-only Phase 0 inspection of the existing SilverBullet trade/exec CSVs
does not establish independent bid/ask quotes, explicit timezone provenance,
fees, or a side-referenced pre-fill quote. Therefore this draft must remain
blocked unless a separate, hash-bound source supplies the missing contract.

## Outcome Fields Forbidden In Phase 0

Do not read or compute any of the following from the nominated donor or any
substitute donor:

- entry/exit result rows, `achievedr`, net/gross profit, swap or commission
  values, win/loss labels, or MAE/MFE;
- PF, expectancy, cadence, net, drawdown, equity, concentration, yearly/monthly
  attribution, or exposure-result counts;
- cutoff alternatives, holding-time subgroups, weekend cohorts, or any value
  used to tune the future design.

Schema/header presence may be recorded; row values may not.

## Future Test Plan — Placeholder, Not Authorization

- Baseline/control: exact source/config matched control; `UNSET`.
- Challenger: control plus weekend-flat only; `UNSET`.
- Model: any later strict control/challenger must use Model 0.
- Date windows and train/holdout rule: `UNSET`.
- Cost x1/x1.5/x2 contract: `UNSET`; must be side-aware and hash-bound.
- Weekend exposure invariant: challenger must have zero weekend crossing under
  the frozen definition.
- Economic/cadence gates: must be copied from the authoritative GOAL and
  `sonic_validation_gates.md` at freeze time and applied separately by split.
- Run budget under current approval: `0` outcome probes, `0` compiles, `0`
  backtests.

No value in this placeholder may be completed after an outcome is opened.

## Phase 0 Failure And Exit Rules

Phase 0 fails closed if any identity, time, quote-side, cost, lifecycle,
counterfactual, or coverage requirement cannot be proven without outcome
access. A failure leaves the hypothesis in draft; it is not a strategy kill.

The draft can be proposed for freezing only after:

1. the runner resolves and binds the exact SilverBullet main source without an
   EA source edit;
2. the artifact-sufficiency matrix proves or explicitly blocks every required
   field;
3. all locked-design placeholders, gates, missing-data rules, split windows,
   and run budget are completed prospectively;
4. the existing Phase 0 `idea/pending` row remains validator-clean, and any
   later execution row or transition is separately authorized; and
5. a clean independent freeze review repeats the contract review without using
   the accidentally displayed donor `RunMeta` summary; and
6. the Owner explicitly authorizes Phase 1 after reviewing the Phase 0 exit
   packet.

Until all six conditions hold, the controlling status remains:

`DRAFT / NOT FROZEN / OUTCOME ACCESS FORBIDDEN`
