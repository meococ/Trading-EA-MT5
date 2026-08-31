---
name: alpha-orchestration-guard
description: Coordinate multi-skill AlphaFactory workflows and prevent conflicts between skills/agents via deterministic order, ownership boundaries, and artifact contracts.
---

## Purpose
Use this skill first whenever two or more `alpha-*` skills are involved in one objective.

## Deterministic order
1. Define objective, hard gates, and one-run-one-change scope.
2. Select minimal required skills.
3. Lock execution order and writers before running commands.
4. Validate artifacts after each stage before allowing next stage.

## Ownership contract
- `alpha-ea-runner`: compile/backtest and run folder creation.
- `alpha-report-analyzer`: normalized report artifacts under `analysis/`.
- `alpha-datalog-db`: log-derived summaries under `analysis/datalog/`.
- `alpha-regime-buckets`: regime outputs under `regime/`.
- `alpha-parameter-sensitivity`: outputs under `sensitivity/`.
- `alpha-walk-forward`: outputs under `walk_forward/`.
- `alpha-monte-carlo`: outputs under `monte_carlo/`.
- `alpha-robustness-suite`: outputs under `robustness/` and gate context.
- `alpha-correlation-exposure`: exposure/correlation outputs under dedicated correlation subfolder.
- `alpha-strategy-memory`: append to `STRATEGY_LOG.md` only after gates are finalized.

## Conflict rules
1. Latest explicit user instruction wins.
2. Safety/integrity constraints override heuristics.
3. This orchestration contract overrides individual skill heuristics.
4. If two skills attempt to write same artifact phase, stop and enforce single writer.

## Parameter normalization
- For duplicate overrides (`k=v;...;k=v2`), normalize with last value wins.

## Minimum acceptance before handoff
- Required artifacts for current stage exist.
- Artifact timestamps are current for this run.
- Claimed metrics can be traced to concrete artifact files.
- Next skill receives explicit `run_id`, paths, and pending gate checklist.
