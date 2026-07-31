# Operator Recovery Pointer

Updated: 2026-07-30.

This file is a non-authoritative recovery pointer for long operator sessions.
It must not duplicate hypothesis metrics, package ledgers, current row counts,
external-key blockers or terminal verdict histories. Those facts drift and have
canonical sources elsewhere.

## Stable state

- Workspace goal: `ACTIVE / UNMET`; see `01. GOAL/GOAL.md`.
- A compile pass, engineering audit, terminal KILL or completed subtask does not
  complete the book goal.
- This file never grants source, run, rerun, promotion, paper or live authority.

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
- Pre-cleanup status snapshot:
  `00. Old File/agent_guidance_archive/governance_cleanup_20260730/`.

If these sources conflict, follow the authority order in `AGENTS.md`; do not
repair the conflict by editing this pointer into a second live ledger.
