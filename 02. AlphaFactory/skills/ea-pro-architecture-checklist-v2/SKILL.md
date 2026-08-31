---
name: ea-pro-architecture-checklist-v2
description: Use before building a new EA, performing a major architecture/risk refactor, promoting an MT5 strategy toward production, or auditing whether an EA is truly prop-firm/live-trade ready. Enforces FSM-grade execution design, non-repaint data discipline, volatility-aware risk, OnTradeTransaction-first handling, SQN/equity-curve evaluation, and autonomous long-horizon R&D loops.
---

## Purpose
Use this skill when the task is any of:
- create a new EA from scratch
- refactor EA architecture or execution/risk pipeline
- harden an EA for live trade or prop-firm constraints
- audit whether a strategy is robust enough beyond headline PF
- define the next high-value research/build loop for an active EA

## Quick use
1. Read `references/checklist-v2.md`.
2. Read `references/project-lifecycle-fsm.md` when the task is about autonomous execution, phase control, or deciding whether an EA is truly done.
3. Extract only the sections relevant to the current EA change.
4. Turn checklist items into concrete artifacts:
   - code/module changes
   - tester settings
   - robustness tasks
   - promotion/rejection gates
   - lifecycle state + next milestone
5. If the task includes AlphaFactory analysis, pair this skill with:
   - `alpha-orchestration-guard` first
   - then the minimal needed `alpha-*` skills

## Non-negotiables
- No PF-only promotion.
- No major rule without a pain-cluster, research reason, or measurable weakness behind it.
- One meaningful strategy change -> one compile -> one run -> one analysis cycle.
- Every serious EA branch should keep a current lifecycle status artifact (`candidate_status.md` or equivalent).
- If you would not trust the EA with your own money or a prop challenge, continue research/hardening instead of declaring victory.
- After backtests, restore MT5 to a usable state.

## When to stop
Do not stop at “good enough”. Stop only when:
- architecture is production-safe,
- metrics pass the declared hard gates,
- robustness stack is acceptable,
- live-safety controls are in place,
- and the remaining limitations are explicitly documented.
