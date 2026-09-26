---
name: goal
description: Show/manage the active GOAL contract and the campaign's position vs it. Amend only on explicit Owner instruction in the current message.
argument-hint: "[show|amend <owner instruction>]"
triggers:
  - user
  - model
---

# /goal — GOAL contract operator for Trading-EA-MT5

Authority order (hard): Owner request > `01. GOAL/GOAL.md` > attempt/hypothesis contract > verified artifact > registry. `04. Memory/hot.md` is cache, never authority.

## Default action: `show`

1. Read `01. GOAL/GOAL.md` verbatim — quote the DONE gates exactly (PF, cadence band, cost tiers, HQ, exposure, evidence window).
2. Load `04. Memory/research/CANDIDATE_REGISTRY.jsonl` — count rows/hypotheses by state (screened/killed/passed/pending).
3. Print the campaign gap table: for each governed run, the binding gates that failed (PF/cadence/cost/DD). Identify WHICH constraint is binding hardest across all attempts (e.g., cadence-vs-PF bimodal wall).
4. Print closest-ever attempts and what specifically separated them from DONE.
5. Output the "goal gap" the next `/loop` iteration must attack.

## `amend <owner instruction>`

Only when the Owner's CURRENT message explicitly states a contract change (cadence band, PF threshold, cost plane, universe, exposure). Never infer an amendment from silence, frustration, or assistant suggestion. When valid:

1. Quote the Owner's exact words authorizing the change.
2. Edit `01. GOAL/GOAL.md`: update the gate, append a dated `Owner YYYY-MM-DD:` note — never delete prior Owner statements.
3. Re-derive implications: which killed hypotheses become legal again, which pending hypotheses change acceptance, which evidence becomes stale.
4. Report the new contract diff and affected hypotheses. Do NOT auto-revive anything — revival still needs a fresh screened row + frozen prereg.

## Hard rules

- `hot.md` never overrides GOAL.md.
- No amendment without quoting the Owner's explicit current-message instruction.
- If the contract looks infeasible (e.g., PF>1.30 ∩ 10-40/wk empty on this cost plane), REPORT the evidence to the Owner — do not silently relax gates.
- Live trading stays blocked regardless; only Owner authorizes.
