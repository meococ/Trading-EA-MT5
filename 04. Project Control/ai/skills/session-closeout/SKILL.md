---
name: session-closeout
description: >-
  End-of-session chốt phiên: research/docs update, self-improve merge via
  parent, and artifact cleanup. Use after any meaningful research/improvement
  session. Coordinator-owned and proactive; respects run_data_policy
  archive-before-delete.
---

# Session Closeout (Chốt phiên)

Standing ops for parent + roster. Rules: `AGENTS.md` §6;
`multi_agent_roster.md` § E; retention: `run_data_policy.md`.

**Parent drives this after meaningful work — do not wait for Owner to ask.**

## A. Research / docs update

Update only files the session actually changed:

| Typically touch | When |
|-----------------|------|
| `hot.md` | truth, scope, blocker, or next move changed |
| `INDEX.md` | workspace map / canonical path changed |
| doctrine / roster / role specs / skills | process changed |
| receipts / manifests | ceremony or cleanup produced them |
| `do_not_repeat_failures.md` | new kill / dead-end |
| `GOAL.md` | **only** if Owner decided |

Gates red → fix before declaring the session closed. Checklist detail:
`agents/packets/SESSION_CLOSEOUT_TEMPLATE.md` § A.

## B. Self-improve + sub proposals → parent merge

Promote when you saw **repeated friction**, a **failed call pattern**, or a
**clearly better procedure** — not taste.

| Step | Action |
|------|--------|
| 1 | Capture lesson in one line (what broke / what works better) |
| 2 | Collect sub proposals from receipts / packets (readonly + impl drafts) |
| 3 | Classify target: skill \| tool wrapper \| role spec \| lean AGENTS pointer \| checklist |
| 4 | **Parent merges**; subs never unilaterally edit standing ops files |
| 5 | Put detail in skill/doc; AGENTS gets short rule + pointer only |
| 6 | Keep sub model pin `cursor-grok-4.5-high-fast` |

**Standing ops (propose → parent merge only):** `AGENTS.md`, `CLAUDE.md`,
`INDEX.md`, `hot.md`, `multi_agent_roster.md`, `agents/<role>.md`, standing
skill rules. **`impl` write exception:** packet-scoped EA/code under
`03. EA Developer/` (+ AlphaFactory compile in packet) — not standing ops.

Skip promote if one-off or speculative.

## C. Artifact cleanup (mandatory if session created clutter)

```text
INVENTORY → CLASSIFY KEEP vs DROP → DRY-RUN → ARCHIVE/DELETE → NOTE hot.md
```

1. **Inventory** session touchpoints: `02. AlphaFactory/runs/`, analysis
   dumps, scratch/temp, agent worktrees, oversized logs.
2. **Keep** anything cited by `hot.md`, cleanup/process receipts, registry,
   prereg, readout, or Owner keep list (protected tier).
3. **Drop candidates:** unused scratch, duplicate mirrors, unreferenced research
   history past age gate, temp analysis not needed going forward.
4. **Tools (prefer dry-run first):**
   - `backtest_storage_inventory.py` — size / orphans (no delete)
   - `archive_backtest_artifacts.ps1` — archive+SHA256 then remove source
   - `dedupe_backtest_log_mirrors.ps1` — exact mirror → hardlink
   - `workspace_hygiene.ps1` — stale worktrees / sample experts
   - `large_log_reader.py` — inspect/search/window; never dump whole logs
5. **Execute** only with clear scope; off-volume archive default for run folders.
6. Optional receipt under `04. Project Control/ai/cleanup_receipts/` for
   meaningful batches; brief English bullet in `hot.md` if cleanup mattered.
7. Fill `agents/packets/SESSION_CLOSEOUT_TEMPLATE.md` when useful.

## Hard bans

- No destroy of hash-bound evidence without archive+manifest (or Owner exception)
- No treat `00. Old File/` as active compile/evidence surface
- No AGENTS bloat with full skill text
- No sub unilateral patch of standing ops files
- No git commit unless Owner asked in the current message
- No skip chốt phiên after meaningful research/improvement work
