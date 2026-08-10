# Operator Recovery Pointer

Updated: 2026-08-10.

This file is a non-authoritative recovery pointer for long operator sessions.
It must not duplicate hypothesis metrics, package ledgers, current row counts,
external-key blockers or terminal verdict histories. Those facts drift and have
canonical sources elsewhere.

## Stable state

- Workspace goal: `ACTIVE / UNMET`; see `01. GOAL/GOAL.md`.
- A compile pass, engineering audit, terminal KILL or completed subtask does not
  complete the book goal.
- This file never grants source, run, rerun, promotion, paper or live authority.

## Current scoped frontier

- The long Supertrend/STBS campaign is terminal as a source of campaign
  priority. Its engineering artifacts remain evidence, but no new comparator,
  parser or governance child is allowed merely to preserve that lane.
- `HYP-JCDR-EURUSD-M5-006` completed one admissible untuned Model-0 baseline and
  is terminally killed: 562 trades, 2.1568/week, PF 0.763972 after report costs,
  price-only PF 0.851207, expectancy -14.04/trade and equity DD 8.02%.
- Goal remains `ACTIVE / UNMET`. The active KPI is now
  `time-to-first-admissible-untuned-baseline`, not hypothesis/artifact count.
- Only one market mechanism may be active. Before its baseline: one short
  prereg, source-to-spec/boundary review, focused tests, compile and non-repaint
  audit through the existing AlphaFactory path. Maximum two engineering
  revisions; a third requires an independent opportunity-cost PASS.
- Governance-only work is explicitly a cost and is never reported as market
  progress. Bind scoped source/config/prereg/run artifacts; do not seal the
  dynamic whole-worktree path set.
- Current next experiment: choose one materially fresh indicator mechanism,
  freeze its standard formula and risk/exit contract, then go directly to one
  untuned Model-0 baseline. If PF is far below 1.30 and the raw/pre-cost edge is
  negative across directions/years without an implementation defect, kill the
  mechanism rather than adding filters or parser/harness children.

## Recover current truth

1. Apply `AGENTS.md`; read `01. GOAL/GOAL.md` and `INDEX.md`.
2. Run `02. AlphaFactory/alpha.ps1 status`.
3. Run `python -B 04. Memory/research/validate_candidate_registry.py`.
4. Run `python -B 04. Memory/validate_source_of_truth.py`.
5. Resolve the relevant latest registry row, prereg, task packet, lock and
   artifact hashes directly from disk.
6. Use `04. Memory/hot.md` only as a recent routing cache and verify it.

## Canonical history

- Operator experiment ledger: `.codex/operator/EXPERIMENTS.jsonl`.
- Hypothesis transitions: `04. Memory/research/CANDIDATE_REGISTRY.jsonl`.
- Failure radius: `04. Memory/do_not_repeat_failures.md`.
- Strategy history: `02. AlphaFactory/STRATEGY_LOG.md`.
- Package state: `03. EA Developer/README.md` and package research artifacts.
- Quant infrastructure producers: `analysis/param_optimizer.py`,
  `analysis/purged_cpcv.py`, `analysis/dynamic_cost_model.py`; schema v1 outputs
  are diagnostic-only rather than gate or promotion authority.
- Shared execution compile harness: `EA_ExecutionKernelHarness`; engineering-only,
  mutation-disabled, experimental and not a live-success claim.
- Pre-cleanup status snapshot:
  `00. Old File/agent_guidance_archive/governance_cleanup_20260730/`.

If these sources conflict, follow the authority order in `AGENTS.md`; do not
repair the conflict by editing this pointer into a second live ledger.
