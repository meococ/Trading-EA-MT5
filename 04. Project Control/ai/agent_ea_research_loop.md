# Evidence-Gated EA Agent Loop

Updated: 2026-07-15

## Purpose

This is the coordinator/worker contract for EA research in this workspace. It
does not authorize live or demo deployment. Its purpose is to make every
experiment attributable, falsifiable, reproducible, and cheap to kill.

The design follows four externally supported patterns:

- simple, composable workflows before open-ended autonomy;
- one manager retaining final control while specialist workers handle bounded
  tasks;
- parallelism only for independent review or evidence gathering;
- deterministic tool feedback, tests, guardrails, traces, and explicit exit
  conditions around the agent loop.

References:

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic: Building a C compiler with parallel agents](https://www.anthropic.com/engineering/building-c-compiler)
- [Anthropic: Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://papers.neurips.cc/paper_files/paper/2024/file/5a7c947568c1b1328ccc5230172e1e7c-Paper-Conference.pdf)

## Operating Model

One coordinator owns the final truth. Workers are advisory or bounded
implementers; they do not promote candidates and do not reinterpret failed
gates.

```text
OBSERVE
  -> INVENTORY
  -> HYPOTHESIS
  -> PREREGISTER
  -> PREFLIGHT
  -> BUILD
  -> CONTROL
  -> CHALLENGER
  -> VALIDATE
  -> CRITIQUE
  -> DECIDE
  -> RECORD
```

The executable run state machine is stricter:

```text
PLANNED
  -> PREFLIGHT_OK
  -> COMPILED
  -> CONTROL_CLOSED
  -> CHALLENGER_CLOSED
  -> VALIDATED
  -> RECORDED
```

Any required-step error transitions to `FAILED`. `FAILED`, `KILLED`, and
`PARKED` are terminal for the current hypothesis version. There is no fallback
to the latest run folder, no reuse of a prior report, and no success summary
when a required artifact is missing.

## Roles

Session roster specs (model pin, I/O, spawn budget):
`04. Project Control/ai/agents/` and `multi_agent_roster.md`. The critic names
below remain the review lenses; map trader/quant critique largely to
`red-team` + `qc`, research ideation to `research`, bounded code to `impl`.

### Coordinator

- Loads doctrine, Git state, registry, prereg, run catalog, and current broker
  context.
- De-duplicates the proposed family against all killed and parked work.
- Creates one immutable task packet and assigns non-overlapping worker scopes.
- Re-hashes all worker receipts and runs deterministic closure checks.
- Owns the final `kill`, `park`, `confirmed`, or `portfolio-sleeve` decision.

### Trader critic

- Tests whether the market mechanism is coherent before indicator details.
- Identifies bad thesis, bad routing, and over-filtering as separate failures.
- Cannot authorize code from chart intuition; locked pre-entry labels are
  required for visual hypotheses.

### Quant critic

- Defines the denominator, holdout, costs, variant family, statistical gates,
  and stop rules before results.
- Counts every attempted threshold, filter, subgroup, and rescue as part of the
  multiple-testing family.
- Rejects active-week cadence, rounded trades/year thresholds, and post-hoc
  subgroup promotion.

### MQL5/MT5 systems critic

- Audits closed-bar behavior, broker geometry, risk state, restart behavior,
  calendar coverage, tester identity, cache isolation, telemetry, and hashes.
- Treats compile success and a generated report as necessary but insufficient.

### Runner worker

- Is the only worker allowed to own MT5 for a run.
- Executes the exact packet without tuning or interpretation.
- Returns artifacts and step receipts; it does not decide whether the EA is
  good.

## Immutable Task Packet

Every meaningful run packet must contain:

- `hypothesis_id`, `control|challenger` role, registry state, prereg path and
  hashes;
- canonical EA/source/include paths and hashes;
- Git commit and porcelain status;
- control and challenger relationship;
- symbol set, timeframe, from/to dates, model, deposit, leverage, spread,
  execution mode, fixed delay, and exact overrides;
- report-derived broker/server-build, account-contract, and tester-data
  fingerprints;
- telemetry tier and required sidecars;
- cost model and source;
- target metrics, validation stage, negative controls, retry budget, and stop
  rules;
- the exact-run-marker contract and permitted artifact roots. The runner assigns
  one unique run identity, then binds it into the immutable execution receipt
  and run-local manifest; result discovery never uses `latest`.

A worker may not silently fill a missing packet field with a default if that
field can change economics or identity.

## Deterministic Hooks

### `preflight`

Reject before compilation when any condition is true:

- registry or prereg is missing;
- the latest hypothesis state is killed or parked without a new version;
- source is under an archive path;
- Git/source/input identity is not captured;
- another tester owns the terminal or the runner lock is stale/ambiguous;
- the control report is absent when a matched challenger is requested;
- broker cost, calendar coverage, or required cross-symbol data is unavailable.

### `post_compile`

- Accept only MetaEditor CLI exit `0` or `1`. Exit `1` is accepted only after a
  newly created compile log proves `0 errors` and a fresh non-empty EX5 has a
  timestamp at or after the compile start. Any other exit, stale/missing log,
  nonzero error count, or stale/missing EX5 fails closed.
- Require a fresh compile log and EX5 newer than the compile start.
- Snapshot and hash source, includes, EX5, and compile log into the run packet.
- Run the static non-repaint and forbidden-source-path checks.

### `pre_backtest`

- Acquire the runner lock atomically.
- Record the exact config and its hash before launch.
- Refuse to kill or reuse an unrelated `terminal64` process.
- Allocate a unique report path; never discover results through "latest".

### `post_backtest`

- Accept only the preassigned report path.
- Verify report/config/source/EX5 identity and minimum report structure.
- Join sidecars by EA RunMeta ID, not filename timestamp alone.
- Require schema, header, row-count, reconciliation, and hash checks.

### `post_validation`

- A nonzero/failed producer invocation always blocks. A zero exit is only a
  successful production receipt; strategy verdicts still come from parsed
  numbers and bound artifacts.
- Mark fixed-parameter temporal slicing as diagnostic, not true WFA.
- Fail closed on missing cost, PBO/Reality Check family, equity, execution,
  overnight, or genuine WFA evidence at stages that require them.
- The current realized-P/L robustness suite and current PBO/White Reality Check
  producers are diagnostic-only (`promotion_eligible=false`). Fresh output from
  those tools still cannot satisfy a `confirmed` gate.
- Confirmed validation requires promotion-eligible robustness reruns plus
  preregistered aligned PBO/White Reality Check evidence from a hash-bound full
  variant family, along with month, half-year, and year stability gates.

### `pre_record`

- Require matched comparison, cost matrix, required validation artifacts, and a
  critic verdict.
- Append one registry transition and one concise readout.
- Refuse to overwrite prior rows or reinterpret a failed holdout.

## Target Contract

For the current goal, book-level cadence is calculated from elapsed calendar
time, including inactive weeks:

```text
elapsed_weeks = (ToDate - FromDate).days / 7
trades_per_week = unique_completed_positions / elapsed_weeks
```

Do not use active weeks/months or rounded trades/year. The target band is:

- base PF strictly above `1.30`;
- `2.0 <= trades_per_week <= 5.0`;
- cost PF x1.5 at least `1.25`;
- cost PF x2 at least `1.00`;
- Model 0 for every strict control/challenger run; Model 1 can only screen, park,
  or kill;
- no hidden overnight/weekend exposure for a scalp contract;
- equity audit `PASS`, no unresolved execution reconciliation gaps;
- confirmed stage also requires at least `100` trades, genuine WFA OOS
  profitable ratio at least `0.60`, PBO below `0.20`, White Reality
  Check/SPA `p < 0.05`, and Monte Carlo P95 DD inside the risk budget.

## Failure Triage (forward / backward) — before Deep Research

When a run fails, a gate misses, or performance is materially weak, run this
triage **before** creating a failure packet or opening Deep Research. Skill
pointer: `.cursor/skills/failure-triage/SKILL.md`. Roster:
`04. Project Control/ai/multi_agent_roster.md`.

```text
FAIL / MISS
  -> (0) TRIAGE: invalid run vs valid strategy fail
  -> INVALID: fix infra -> re-run same packet (AlphaFactory) -> stop
  -> VALID:
       (1) FORWARD: thesis -> assumptions -> expected metrics -> which gate missed?
       (2) BACKWARD: gate fail -> concrete cause (thesis/data/exec/sample/regime)
       (3) CLASS: bad_thesis | bad_data | bad_exec | insufficient_sample | regime | unknown
       (4) ACTION (table below)
       (5) only then: failure packet -> Deep Research -> new idea -> probe -> prereg
```

| When | Action |
|------|--------|
| Infra/config/artifact broken | **Re-run** same packet — no thesis change |
| Gate miss; mechanism still testable another way | **Park** old version -> new child hyp -> AlphaFactory |
| Cannot separate bad rule vs bad state read | **Chart/state probe** (locked labels only; `.cursor/skills/chart-state-probe`) — **no** EA patch from chart glance |
| Family already killed/parked or data blocker unchanged | **Stop / NO LEGAL CANDIDATE** |

Hard bans unchanged: no post-hoc hour/day/symbol/regime veto from the readout
just read; no rescue-tune of the failed hypothesis version.

## Loop Budget And Stop Rules

- One hypothesis version contains one feature family and one state separation.
- One implementation step changes one decision surface.
- A failed holdout cannot be reused for redesign.
- Post-result hour, day, session, symbol, or regime findings become new ideas.
- Model 1 may kill or park; it cannot promote.
- One environment retry is allowed after a diagnosed infrastructure failure.
  A second identical infrastructure failure stops the run.
- A strategy gate failure causes immediate park/kill; the coordinator does not
  spend retries tuning toward the target.
- After a **valid** strategy failure or materially poor performance, and after
  Failure Triage above, the coordinator creates a hash-bound failure packet and
  runs Browser -> ChatGPT -> `GPT-5.6 Sol` -> `Pro` -> `+` -> `Nghiên cứu sâu`.
  The failed hypothesis stays terminal; GPT may diagnose it or propose a new
  independent/child hypothesis, but cannot rescue it through post-result tuning.
- The new proposal receives no execution authority until source audit,
  registry de-duplication, a cheap offline probe, a new hypothesis ID, and a
  frozen preregistration all pass. The old exposed holdout is not recycled.
- An unchanged data/execution blocker or a proposal that repeats a closed
  family stops the loop. Continue Deep Research only when new external
  evidence, data, or a genuinely different mechanism exists.
- Parallel critics may inspect the same frozen artifacts. MT5 backtests remain
  sequential unless terminals and data roots are physically isolated.
- Session roster (red-team / research / impl / qc): see
  `04. Project Control/ai/agents/`. Max 2–3 parallel readonly subs per wave;
  serial WRITE; all subs default model `cursor-grok-4.5-high-fast`.

## Current Frontier Decision

The existing Sonic field/symbol frontier is closed: no cataloged run reaches
both PF and cadence, and prior XAU/EUR/GBP rescue families are killed or parked.

One external pivot, `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`, is accepted only
as an `IDEA / COST-DATA BLOCKED` preregistration. It treats synchronous common
USD as a regime and selects the pair already strongest after its own
pullback-break. It must beat locked S555 lead-lag, S618 fixed-target consensus,
and S670 laggard-divergence controls. Missing same-broker tick-derived bid/ask
paths, commission (30 lifecycles or a hash-pinned contract), and at least 100
side-referenced slippage fills per symbol blocks the offline outcome probe.
Commission-to-pip conversion is per trade at the contemporaneous
quote-to-account rate, especially for USDJPY. No EA rule patch, compile, or
backtest is authorized from the current artifacts.

The 2026-07-11 read-only audit made that blocker concrete: historical quote
ticks are unavailable, spread fields are mostly missing, commission has only
two EURUSD lifecycle samples, and all three symbols have zero usable
side-referenced slippage samples.
`sonic_cost_stress.v1` remains diagnostic-only and cannot satisfy a promotion
cost gate.

The lifecycle telemetry contract is now `sonic_telemetry.v3`. PX6/Trades rows
carry `initial_risk_account`, calculated through `OrderCalcProfit` at position
open or restart reconstruction, plus `deal_profit`, `deal_commission`,
`deal_swap`, `deal_fee`, and `deal_net` on both entry and exit lifecycle rows.
For each deal row, `pnl_gross = deal_profit` and
`pnl_net = deal_net = deal_profit + deal_commission + deal_swap + deal_fee`.
Every OPEN row uses the actual history-deal ID, fill volume, fill price, fill
time, position ID, and effective broker stop. Netting scale-ins are separate
immutable OPEN rows; request values or aggregate position values are not valid
deal-level substitutes.
The report-bound
`02. AlphaFactory/tools/build_verified_cost_artifact.py` producer is present and
its focused unit suite passes `6/6`; it requires v3, reconciles the deal-level
components and lifecycle totals, and emits `verified_execution_cost.v1`. Tool
availability does not clear the missing same-broker
quote/commission/slippage blocker.

The producer parses raw spread CSV rows (`timestamp/symbol/bid/ask`), commission
lifecycle CSV rows to derive P90 round-turn account commission per lot, and
slippage fill CSV rows (`side/reference/fill/pip`), or a hash-bound JSON broker
contract. It does not trust self-declared sample counts, values, or P90s. Every
report deal ID must join to the v3 lifecycle; unified validation then rebuilds
the artifact from the raw inputs and compares `trade_repricing` and `scenarios`.

Source S/R is a separate research blocker. `InpUseSourceSrInteractionV1=false`
is documented in code as telemetry-only, but the current implementation still
calculates `source_sr_*` unconditionally and uses `source_sr_runway_pips` in
Classic decision gates. Therefore `false` does not prove "no decision effect".
Do not use Source S/R control/challenger claims for promotion until a dedicated
code fix or matched ablation proves the switch contract. This document records
the mismatch only; it does not authorize an EA logic change.

Registry promotion is also fail-closed. A `confirmed` or `portfolio-sleeve`
row must bind separate train/holdout report, cost, and outcome artifacts; exact
cadence arithmetic; locked control margins; source/compiled/readout evidence;
and the full validation stack. Run
`python "03. EA Developer/EA_SonicR/research/validate_candidate_registry.py"`;
schema conformance alone is not arithmetic or artifact proof.

## Implementation Status

The fail-closed runner and numeric validator contracts are implemented and
covered by focused regression suites. Strict execution now requires Model 0, a
hash-bound `sonic_research_task_packet.v1`, canonical source/prereg identity,
physical source/config/EX5/include receipts, verified cost-source files,
`sonic_telemetry.v3` lifecycle evidence with deal-level reconciliation, and a
report-bound verified cost artifact before unified validation. `RunRole=control`
creates the first strict
baseline without a prior control; `RunRole=challenger` accepts only a completed
strict control with matching economics and artifact hashes.

Three deliberate blockers remain:

- no latest registry row is currently an execution-eligible EA challenger. The
  only new row is the offline, cost-data-blocked common-USD idea;
- same-invocation `ValidationStage=confirmed` is rejected. Confirmed promotion
  is a later validation-only pass over a frozen completed run after an external
  optimization-aware WFA artifact, promotion-eligible robustness/PBO/White
  Reality Check evidence, and the full tried-variant family exist;
- the Source S/R default-off contract is not behaviorally isolated, so any
  claim that `InpUseSourceSrInteractionV1=0` creates a no-effect control is
  blocked pending a code fix or matched ablation.

Do not bypass these blockers with direct low-level runner calls and then treat
their artifacts as promotion evidence.
