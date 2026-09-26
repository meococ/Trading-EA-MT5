# SNAPSHOT — fidelity at decision time (mandate Z2)

tau: BOX/lines = build_end else t1 ; levels = t0+10 ; BRACKET/SQUEEZE = t1 ; BAR_MARKER = t0 ; T/F = mark t.
`live` = engine run fed only bars <= tau, objects not DELETED.  Ruler = eval_v2 with w1=tau.

## v0 (`63c771d64e18f619`)

| type | snap recall | cumul-ink recall | n |
|---|---|---|---|
| BAR_MARKER | 0.00 | 0.00 | 4 |
| BOX | 0.14 | 0.21 | 106 |
| BRACKET | 0.73 | 0.73 | 85 |
| CONTEXT_LINE | 0.22 | 0.22 | 9 |
| CONTEXT_RANGE | 0.33 | 0.33 | 6 |
| LABEL_TF | 0.02 | — | 51 |
| LEVEL_CARRIED | 0.09 | 0.15 | 46 |
| MINI_LEVEL | 0.03 | 0.06 | 30 |
| PATTERN_LINE | 0.10 | 0.11 | 184 |
| RANGE_OPEN | 0.00 | 0.38 | 7 |
| SQUEEZE | 0.50 | 0.50 | 2 |

snapshot precision (pooled over 504 decision events): **0.03** ; live clutter median = **18.0** objects

## v1 (`694313a38abc2da6`)

| type | snap recall | cumul-ink recall | n |
|---|---|---|---|
| BAR_MARKER | 0.00 | 0.25 | 4 |
| BOX | 0.01 | 0.05 | 106 |
| BRACKET | 0.16 | 0.20 | 85 |
| CONTEXT_LINE | 0.22 | 0.22 | 9 |
| CONTEXT_RANGE | 0.00 | 0.00 | 6 |
| LABEL_TF | 0.00 | — | 51 |
| LEVEL_CARRIED | 0.02 | 0.10 | 46 |
| MINI_LEVEL | 0.00 | 0.00 | 30 |
| PATTERN_LINE | 0.11 | 0.12 | 184 |
| RANGE_OPEN | 0.14 | 0.25 | 7 |
| SQUEEZE | 0.50 | 0.50 | 2 |

snapshot precision (pooled over 504 decision events): **0.03** ; live clutter median = **12.0** objects

## linelab (`ceef7d3fc610e67c`)

| type | snap recall | cumul-ink recall | n |
|---|---|---|---|
| BAR_MARKER | 0.00 | 0.00 | 4 |
| BOX | 0.00 | 0.00 | 106 |
| BRACKET | 0.00 | 0.00 | 85 |
| CONTEXT_LINE | 0.22 | 0.22 | 9 |
| CONTEXT_RANGE | 0.00 | 0.00 | 6 |
| LABEL_TF | 0.00 | — | 51 |
| LEVEL_CARRIED | 0.00 | 0.00 | 46 |
| MINI_LEVEL | 0.00 | 0.00 | 30 |
| PATTERN_LINE | 0.14 | 0.15 | 184 |
| RANGE_OPEN | 0.00 | 0.00 | 7 |
| SQUEEZE | 0.00 | 0.00 | 2 |

snapshot precision (pooled over 504 decision events): **0.06** ; live clutter median = **4.0** objects

## snapshot vs cumulative-ink — the difference in five lines

Cumulative-ink credit = the object existed at ANY point in the panel, even born after the golden decision or re-anchored later.  Snapshot credit = the object was live, with its at-that-moment geometry, exactly when the golden author decided.  A late-born or drifting object earns ink credit but no snapshot credit.  Snapshot precision also penalizes clutter that cumulative precision dilutes over the whole panel.  So snapshot <= cumulative on recall, and the gap measures how much of the engine's ink is hindsight.
