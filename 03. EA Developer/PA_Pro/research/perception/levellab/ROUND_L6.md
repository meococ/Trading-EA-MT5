# ROUND L6 — provisional leg-extreme origins (measured, not adopted)

Code state: FINAL R5 config (edge price + side-free reprice +
`sess_grace_bars=48` + `min_score=1.0`). 198 TUNE, eval_v2 `50e11fd5`.
One-lever A/B: `leg_origins` False→True.

## Idea

A defended swing extreme whose reversal never confirms inside the
window is invisible to the θ-pivot origin stream. Register the running
DC leg extreme (`dc.ext_price`) as a provisional `cls="leg"` origin:
each extension supersedes the previous one (grace to earn defences);
on dir flip the final extreme is confirmed as a θ pivot — merge upgrades
its `cls` and clears the expiry.

## Result (paired A/B)

| metric | leg off (FINAL) | leg on |
|---|---|---|
| LC v2 recall | **0.750** (36/48) | 0.750 (36/48) |
| LC trusted | 0.850 | 0.825 |
| LC oracle | 0.792 | **0.833** |
| MINI oracle | 0.774 | 0.839 |
| snap LC | 0.596 | 0.617 |
| born/panel | LC 4 + MINI 8 | LC 5 + MINI 9 |
| live@τ | 6 | 7 |
| LC prec | 0.045 | 0.033 |

## Read

- Proposal ceiling +2 objects (0.79→0.83) but born recall flat — the
  extra coverage lands on panels where birth timing doesn't overlap the
  golden span. The birth-conversion rate stays ~95% of oracle.
- Ink +2 born/panel and live@τ 6→7 for zero born-recall gain →
  **not adopted** (param kept, default False). If the production lane
  ever needs more proposal coverage (e.g. after a salience fix makes
  proposals scarce relative to slots), `leg_origins=true` is the
  measured knob.
- After this round the residual miss profile is stable: ~8 of 12 LC
  misses are TIER_A suspects, ~4 clean oracle-gap at prices the
  pivot+session+leg universe cannot express (congestion-mid, named-bar
  interior). Trusted recall 0.850 is the practical ceiling for this
  origin universe.
