# HOLD_PROCEDURE.md — how HOLD opens, once (EVAL-AUDIT draft, R56 §56.6.5)

HOLD is the sealed evaluation split: `golden/BOOK2012_HOLD.jsonl` (and its
draft `golden/draft/BOOK2012_HOLD_v2.jsonl`). No lane reads it until the
Lead gives the go, and it opens exactly once.

## Preconditions (all must hold)

1. **P-FREEZE declared** by the Owner on a named FINAL STABLE hash —
   i.e. box@1 has reached the agreed bar (v0 parity, or a threshold the
   Owner set from the human ceiling).
2. **M2 scored.** The Owner's blind answers on the FINAL hash's M2 pack
   are scored (sensitivity on golden controls, specificity on audited
   negatives, plausible share — each with a CI), and the result is in
   VERIFY_LOG.
3. **End thresholds confirmed by the Owner** in writing: the pass bar for
   each M1 family on HOLD, and the clutter bar.
4. **The frozen snapshot** `_scratch/freeze_candidates/<hash>/` exists
   with SHA256.txt, and EVAL-AUDIT has re-verified the on-disk hash
   equals it.

## The one opening

- The Lead writes one line, `HOLD OPEN <hash>`, in LEAD_RULINGS.md.
- Only then may a process read the HOLD files. The run is the ruler
  `eval_v2` (`50e11fd5a2ab7974`) on the FINAL STABLE engine, full window,
  no tuning, no arm variants — one measurement.
- EVAL-AUDIT runs its own scorer (`m1_row.py` path) independently in the
  same step, from a separate process.
- Both results go into the log verbatim: per-family recall at budget,
  clutter median + margin, the six diagnostics, n_panels.

## Rules

- **One opening, one verdict.** No re-runs with tweaked parameters, no
  "one more check" on HOLD. If a bug is found in the measurement itself
  (not the engine), the fix and re-run are logged with the reason.
- A failed HOLD leg is a result, not a trigger to unfreeze. The Lead
  writes the P-FREEZE verdict from the numbers as they stand.
- HOLD data never enters any cache, fixture, or parameter path. Nothing
  learned from HOLD may flow back into engine code — the freeze is the
  freeze.
- Bars for HOLD panels come from the same read-only bars store as TUNE;
  the wall scanner (`evalcheck/test_walls.py`) keeps enforcing the split.

## Sealed until then

- mtime check on the two HOLD files is part of EVAL-AUDIT's hourly wall
  audit. Any read or write before the go is an escalation (playbook §8.1).
