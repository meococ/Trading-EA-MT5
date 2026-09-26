# ROUND L1 — baseline proposer

Config (defaults): origin = θ1/θ2 pivots + every running session/Asia
extreme; birth when defences≥2 and |close−price| ≤ 1.75 ABR,
score = n_def − dist ≥ 2.0; NMS ±2.5p; pierce 2 closes; stale 60 bars.

Result (198 panels, both rulers):

| ruler | LC recall | LC prec | LC trusted | MINI recall | MINI prec |
|---|---|---|---|---|---|
| eval.py | 0.646 (31/48) | 0.028 | 0.725 | 0.594 | 0.022 |
| eval_v2 | 0.604 (29/48) | 0.026 | 0.675 | 0.645 | 0.023 |

Oracle: LC 0.792, MINI 0.806. Born ink ~9/panel (LC ~5 + MINI ~4).

Diagnosis: coverage is excellent — the defended-origin design matches
V2 anatomy. Ink is the problem: born-by-route shows `asia` 882 +
`session` 501 = 69% of births from running-extreme origins (every new
day-high/low creates a candidate that later earns defences). Golden
anatomy says session-class origins should be ~20%.

Round-2 hypothesis: stricter birth (def3/sc3/app1.5) cuts ink.
Result: WORSE on all axes — oracle 0.667, LC recall 0.542, prec 0.021.
min_defences=3 delays qualification so long that coverage collapses.
Lesson: the origin universe is right; the *session-extreme origin
factory* is the noise, not the defence threshold.
