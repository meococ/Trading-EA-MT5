# Codex Execution Plan V2 — Phase 0 Contracts And Evidence Sufficiency

Date: 2026-07-11  
Coordinator: Codex  
Executor: Codex  
Approval state: `OWNER APPROVED — PHASE 0 ONLY`  
Execution state: `PHASE 0 IMPLEMENTED / CLEARANCE BLOCKED / PHASE 1+ BLOCKED`

This document supersedes `20260711_CODEX_EXECUTION_PLAN_V1.md` in full. V1 is
retained as historical rationale, but no task, identifier, gate, or permission
in V1 remains executable unless V2 restates it. In particular, the V1 combined
weekend-flat/max-hold hypothesis and its proposed Phase 1 outcome probes are not
authorized.

## Decision

The only legal work is Phase 0 governance and evidence-contract work:

1. harden the AlphaFactory runner's EA source-entrypoint contract without
   editing any EA source;
2. inspect artifact identity, paths, hashes, headers, and provenance only, to
   decide whether future preregistrations can be frozen;
3. maintain the two preregistration drafts named by this plan.

Phase 0 does **not** authorize reading outcome rows or derived performance
metrics. It also does not authorize an EA source edit, a compile, an MT5
backtest, an offline outcome replay, a registry transition beyond the two
approved `idea/pending` metadata rows, or a claim that a candidate has been
tested.

## Authority And Local Evidence

This revision applies the following repository evidence:

- `20260711_CODEX_EXECUTION_PLAN_V1.md`: records the runner/source ambiguity,
  the unsupported Sonic telemetry assumptions for SilverBullet, and the two
  proposed research families. V2 narrows its permissions and corrects its
  sequencing.
- `04. Project Control/ai/research_doctrine.md`: requires one preregistered
  hypothesis, a registry row before meaningful experimental evidence, an
  offline probe before EA entry-rule work, matched controls, closed-bar
  decisions, and no post-result rescue edits.
- `04. Project Control/ai/sonic_validation_gates.md`: gives an `idea` no
  backtest decision power, requires exact source/artifact identity, makes Model
  0 mandatory for any later strict control/challenger, and reserves portfolio
  review for independently confirmed components with correlation, overlap,
  drawdown, and cost artifacts.
- `20260711_BROKER_COST_PROVENANCE_AUDIT.md`: establishes that missing or zero
  cost fields are not free execution and that the current broker evidence does
  not support an outcome probe requiring promotion-grade bid/ask, commission,
  or side-referenced slippage.

When these documents conflict on live permission, V2 is the narrower execution
contract. The canonical doctrine and validation gates still control research
quality; V2 cannot waive them.

## Corrections To V1

| V1 position | V2 correction |
|---|---|
| Runner/source-contract engineering followed an offline outcome probe. | Runner/source-contract hardening is Phase 0 because no legal run can precede exact source resolution and receipt/manifest binding. |
| `HYP-SB-WEEKEND-FLAT-MAXHOLD-001` combined weekend-flat with a 30-hour maximum hold. | The combined identifier is retired and must not be registered. A1 weekend-flat and A2 max-hold are separate causal interventions. |
| The old SilverBullet donor schema was described as sufficient for replay. | That sufficiency claim is withdrawn. File/header inspection does not establish side-aware executable prices, timezone/session provenance, counterfactual entry eligibility, or verified costs. |
| A portfolio screen could select a per-EA best run and ask whether any combination passes. | Outcome-selected representatives and an unrestricted “any combination” search are not a prospective test. Phase 0 may create only an exact, hash-bound, outcome-blind universe and an artifact-sufficiency matrix. |
| The SilverBullet index source could be quarantined out of the EA directory. | No EA file may be moved, quarantined, renamed, or edited in Phase 0. The runner must resolve an explicit source contract and fail closed on ambiguity or a missing pinned source. |
| Two registry rows could be treated as evidence before the draft contracts were sufficient. | Phase 0 records exactly two metadata-only rows at `state=idea`, `verdict=pending`, with empty run IDs and null outcome metrics. They grant no outcome access, freeze, probe, or execution authority. |

## Hypothesis Separation

### A1 — Weekend-flat only

- Reserved draft ID: `HYP-SB-WEEKEND-FLAT-001`.
- Intervention: a weekend-flat rule only.
- No maximum-hold rule, holding-age threshold, entry filter, position-sizing
  change, or other management change belongs to A1.
- The governing draft is
  `preregs/20260711_H_SB_WEEKEND_FLAT_001_PREREG.md`.

### A2 — Future max-hold child

- A2 is a separate future child and has no assigned hypothesis ID, registry
  row, or preregistration.
- Do not use the retired V1 combined ID as an A2 identifier.
- A2 remains unregistered until a side-aware price path, explicit timezone and
  session calendar, holding-age semantics, cost treatment, and suppressed-entry
  counterfactual contract exist.
- An A1 result could not be reused as evidence for A2. A later combined
  A1-plus-A2 intervention would itself require a separate preregistration and
  interaction-aware matched control.

### Portfolio composition

- Reserved draft ID: `HYP-PORTFOLIO-COMPOSE-001`.
- Phase 0 question: can an exact input universe be enumerated and proven
  artifact-sufficient without reading outcomes?
- The governing draft is
  `preregs/20260711_H_PORTFOLIO_COMPOSE_001_PREREG.md`.
- No sleeve selection, weighting, correlation, overlap, combined P&L, or
  pass/fail computation is permitted now.

## Phase 0 — Authorized Work

### P0.1 Runner EA source contract

Allowed implementation surfaces are AlphaFactory framework and focused runner
contract tests only. The contract must:

1. resolve one exact repo-local active `.mq5` entrypoint for an EA;
2. pin SilverBullet to
   `03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5` without moving or
   editing either SilverBullet source file;
3. fail closed when the pinned file is missing, when a path escapes the active
   EA root, or when source evidence disagrees with the resolved entrypoint;
4. distinguish EAs that implement the Sonic telemetry input contract from EAs
   that do not, while rejecting unsupported non-off telemetry tiers;
5. bind the resolved source to pre-run receipt checks and any future run
   manifest; and
6. prove the behavior with static/unit contract tests that do not invoke
   MetaEditor, a terminal, or the Strategy Tester.

This work repairs execution governance only. Passing runner tests is not compile
proof, EA equivalence proof, or strategy evidence.

### P0.2 A1 artifact-sufficiency audit

The audit may inspect file existence, byte size, SHA-256, manifest/config
identity fields, and CSV/JSON schema headers. It may not read trade-result rows
or performance summaries.

The audit must decide whether the nominated SilverBullet donor can support all
of the following before the A1 draft is frozen:

- authoritative server timezone and historical UTC conversion, including DST
  behavior where applicable;
- an exact, ex-ante Friday cutoff and broker trading-session/holiday calendar;
- chronological executable bid and ask paths at every forced-exit decision;
- side-correct close pricing, independently referenced slippage, commission,
  swap, fee, and account-currency conversion;
- unambiguous position lifecycle, partial-fill, and close-failure semantics;
- sufficient pre-entry eligibility/state evidence to distinguish a
  truncation-only estimate from the full counterfactual strategy after an early
  close frees a position slot; and
- complete split coverage with a fail-closed missing-data rule.

A missing required field is a valid Phase 0 blocker. It must not be imputed and
must not trigger an outcome read to “see whether it matters.”

### P0.3 Portfolio exact-universe and sufficiency audit

The portfolio draft must remain outcome-blind while Phase 0 creates:

1. an exact list of `<EA>/<run_id>` members and a universe cutoff timestamp;
2. hashes for the identity, config, source, report, trade-series, equity-series,
   and cost artifacts required by the future design;
3. structural duplicate/collision groups derived without performance ranking;
4. a member-by-artifact presence/provenance matrix; and
5. one SHA-256 over the canonical sorted universe inventory.

The inventory must not contain PF, net profit, win rate, drawdown, trade
outcomes, cadence, cost-stressed results, correlations, overlap results, or a
rank. V1's “per-EA best run” rule is not allowed because “best” requires outcome
access. If a representative is needed, its rule must be outcome-independent and
frozen before any result is opened.

### P0.4 Draft governance

The two preregistrations must retain the exact banner:

`DRAFT / NOT FROZEN / OUTCOME ACCESS FORBIDDEN`

Owner approval includes exactly two canonical Phase 0 registry rows:
`HYP-SB-WEEKEND-FLAT-001` and `HYP-PORTFOLIO-COMPOSE-001`. Both must remain
`state=idea`, `verdict=pending`, with empty `run_ids`, null outcome metrics, and
draft prereg paths. These rows are routing metadata only; they do not start a
probe or grant decision power. Any later transition or execution row must be
separately authorized, point to a frozen prereg, and pass the registry
validator before meaningful experimental work.

## Phase 0 Data-Access Boundary

| Operation | Phase 0 status |
|---|---|
| Enumerate paths, sizes, hashes, and schema/header names | Allowed |
| Read source-contract/config identity needed to resolve the canonical main file | Allowed |
| Run focused static/unit runner contract tests with synthetic fixtures | Allowed |
| Edit AlphaFactory runner contract code and its focused tests | Allowed |
| Read any trade row, equity point, P&L, PF, win/loss, drawdown, cadence, cost result, correlation, or overlap result | Forbidden |
| Write or execute an outcome analyzer/replay | Forbidden |
| Edit, move, rename, or quarantine EA source/include files | Forbidden |
| Compile an EA or create/use an EX5 as evidence | Forbidden |
| Start or query MT5 for this lane, or run Strategy Tester | Forbidden |
| Append the two exact Phase 0 `idea/pending` rows with empty run IDs and null outcome metrics | Allowed; completed under Owner approval |
| Freeze either draft or transition/create an execution-state row | Not authorized by the current approval |
| Perform any Phase 1+ task | Blocked |

If a tool cannot guarantee that it will avoid outcome fields, do not run it.

## Phase 0 Exit Packet And Clearance

The authorized implementation slice is complete when the coordinator can
review all of the following:

- focused runner contract tests are green and show exact source resolution,
  fail-closed missing/ambiguous-source behavior, telemetry-profile enforcement,
  and source receipt/manifest binding;
- the worktree diff confirms no EA source/include file was changed;
- the artifact-sufficiency producer returns either a fail-closed blocker list
  or `READY_FOR_PREREG_FREEZE`, while whole-spec SHA pinning, exact-path
  containment, atomic header/hash snapshots, and focused tests prove it did not
  parse outcome rows;
- the portfolio spec contains an exact candidate list, including an explicit
  empty list when no clean universe has been frozen, and contains no outcome or
  rank field;
- the artifact-sufficiency report states all known coordination-session or
  inherited contamination explicitly;
- the two Phase 0 registry rows remain `idea/pending`, validator-clean, with
  empty run IDs and null outcome metrics;
- both preregistration documents still say `DRAFT / NOT FROZEN / OUTCOME ACCESS
  FORBIDDEN`; and
- the closeout states that no compile, backtest, MT5 execution, controlled
  outcome analysis, threshold change, or strategy verdict occurred, and it
  separately discloses any accidental display event.

Meeting these conditions completes the implementation slice but does not imply
clean clearance. `READY_FOR_PREREG_FREEZE` additionally requires every A1
provenance field and the exact portfolio universe/risk-binding contract to be
present, plus a clean independent review if any coordination-session
contamination was recorded. It still does not automatically open Phase 1.

### Coordination-session contamination record

During Phase 0 inventory work, one sub-agent accidentally displayed a
SilverBullet `RunMeta` metadata file that contained summary fields before the
access contract was finalized. No displayed value was copied into a contract,
threshold, registry metric, decision, or producer output, and the controlled
producer still reports `producer_semantic_outcome_accessed=false`. Nevertheless,
this is an
access-boundary contamination event. The machine report must record it and
keep clearance blocked; any future freeze review must use a clean independent
session and must not rely on the exposed file or this session's judgment about
outcomes.

The reviewed session/evidence binding is
`preflight/20260711_PHASE0_COORDINATION_CONTAMINATION_ATTESTATION_V1.json`.
The artifact-sufficiency spec pins its SHA-256; missing, changed, or unknown
attestation state must remain blocked. This V1 preflight cannot become clean by
rerun; a clean independent review requires a new versioned spec/attestation.

## Phase 1+ — Blocked

Every Phase 1 or later action requires a new explicit Owner approval after the
Phase 0 exit packet is reviewed. Before even an offline outcome probe, the
applicable hypothesis must also have:

1. one frozen preregistration with all data, side, timezone, cost, split,
   missing-data, gate, and run-budget fields complete;
2. a separately authorized schema-valid execution row or transition that
   points to that frozen prereg; the Phase 0 `idea/pending` row alone is not
   execution authority;
3. hash-bound analyzer code and input/cost manifests;
4. a documented outcome-access sequence, including train-first and one-time
   holdout rules where applicable; and
5. an explicit coordinator go/no-go record.

For avoidance of doubt, Phase 1 remains blocked even if runner contract tests
pass. No EA source edit, compile, Model 0 run, or portfolio result may occur
under the 2026-07-11 Phase 0 approval.
