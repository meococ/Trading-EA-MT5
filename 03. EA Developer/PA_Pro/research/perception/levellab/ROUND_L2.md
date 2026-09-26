# ROUND L2 — stricter birth gates (dead end, kept for the record)

Config: min_defences=3, min_score=3, approach_abr=1.5.

| ruler | LC recall | LC prec | LC trusted | MINI recall |
|---|---|---|---|---|
| eval.py | 0.521 | 0.020 | 0.600 | 0.469 |
| eval_v2 | 0.542 | 0.021 | 0.625 | 0.452 |

Oracle LC 0.667 (−0.125 vs L1). Snapshot LC 0.447, live med 4.0.

Lesson: raising `min_defences` destroys coverage before it cleans ink —
a defended origin needs time to accrue retests, and by then its approach
window has often passed. Rejected direction.
(Also caught + fixed a price-scale bug in the params-feed path of
run_eval_levels.py during this round: day arrays are pips, `update()`
expects absolute.)
