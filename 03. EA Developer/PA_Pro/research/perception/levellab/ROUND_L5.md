# ROUND L5 — miss audit → NMS reprice + score-floor sweep

Code state: `levels_lab.py` edge-price + `sess_grace_bars=48` (R4c).
198 TUNE panels, eval_v2 `50e11fd5` (+ eval.py paired). All deltas are
paired A/B at one code state.

## 1. Miss audit (miss_audit.py, 20 LC misses under R4c)

For each unmatched golden LC: golden price vs closest born object vs
all proposals inside the golden span.

- **10/20 — right-priced proposal exists (≤1.0p) but never born, or
  born with the wrong price.** Root cause: NMS band (3p). A
  first-seen incumbent accrues `n_def` in `_maintain`, so a later,
  correctly-priced same-side challenger is suppressed forever; the
  incumbent keeps its inferior price. Examples: 9.39b golden 13149.9,
  proposal 13149.8 n_def=15 suppressed by incumbent 13151.4 (born t=90);
  9.57b born at right price but t=760, after golden span end 705 —
  suppression delayed the birth.
- **10/20 — no proposal within tol at all** (best gap 1.7–19.8p):
  9.17b×2, 9.18c, 9.21b, 9.37c, 9.40a, 9.56b, 9.63a, 9.65a×2. Golden
  price is not a pivot/session extreme in our stream (congestion-mid,
  named-bar interior, or suspect labels). Oracle-gap, not birth-gap.

## 2. Fix: defended-edge reprice (one-object-per-band, price tracks
   the most-defended same-side origin)

`_birth` NMS branch: when a challenger inside the band has
`n_def >= incumbent.n_def0` (origin defence count, not accrued) and the
same side, the incumbent **reprices to the challenger edge price** and
keeps its early `t_birth` — instead of the old close-incumbent +
birth-new (which reset `t_birth` and lost temporal overlap) or silent
suppression (which kept the wrong price).

## 3. Results (paired, same state except the lever)

| config | LC v2 recall | trusted | oracle | MINI v2 | snap LC | live@τ |
|---|---|---|---|---|---|---|
| R4c edge, no reprice | .583 | .700 | .792 | .548 | .489 | 4–5 |
| + reprice same-side (ms=2.0) | .646 | .775 | .792 | .516 | .511 | 5 |
| + reprice ms=1.5 | .688 | .775 | .792 | .581 | .574 | 5 |
| + reprice ms=1.2 | .708 | .800 | .792 | .677 | .574 | 6 |
| + reprice ms=1.0 | .708 | .800 | .792 | .677 | .574 | 6 |
| + reprice ms=0 | .729 | .825 | .792 | .677 | .596 | 6–7 |
| reprice `>` only (ms=2.0) | .625 | .750 | .792 | .484 | .532 | 5 |
| **reprice side-free, ms=1.0 (FINAL)** | **.750** | **.850** | .792 | .677 | .596 | 6 |
| ms=1.0 + min_defences=1 | .729* | .825* | **.875** | .710 | .596 | 6 |
| ms=1.0 + approach 2.5 | .729* | .825* | .792 | .613 | .574 | 6 |

(*side-free reprice measured only for the final row pattern; the
side-free variant was measured at ms=1.0 and adopted as FINAL.)

eval.py LC recall (FINAL): 0.708. Precision ~0.045 (ink-heavy stream —
precision is not the gate; live@τ 6 vs engine clutter ~12).

Side-free reprice (+0.04 over same-side): a ±3p defended zone flips
roles (support↔resistance); the side the first origin was approached
from is not the level's identity.

## 4. Read

- Born recall is now 36/38 = **95% of the proposal ceiling**; the
  frontier moved from births to proposals.
- `min_score=1.0` still gates: n_def=2 needs approach ≤1 ABR; n_def≥3
  births on any approach within 1.75 ABR. `min_score=0` adds only +0.02
  recall — kept 1.0 as the honest floor.
- `min_defences=1` raises the oracle to 0.875 but adds nothing to born
  recall (n_def=1 needs dist≈0 to score ≥1) — not adopted; noted as the
  proposal-side ceiling if a later lane wants it.
- Remaining 12 LC misses: **8 are TIER_A suspects** (labels at prices on
  nothing) + ~4 clean oracle-gap (no right-priced origin in stream —
  congestion-mid / named-bar interior prices the pivot+session origin
  universe cannot express). Trusted recall 0.850 is effectively the
  ceiling for this origin universe.
- Gate check: LC v2 recall **0.750 ≥ 0.60** in the lab (production will
  lose a share to rate limiting — see LEVEL_INTEGRATION.md honesty
  note).
