# EVAL_TUNE — spec §6.1 on BOOK2012_TUNE_v2

Frozen yardstick: T000366. Engine run per panel day up to window.x1 (CET). All counts per spec matching table.

## v1

| type | golden | engine | matched | recall | precision |
|---|---|---|---|---|---|
| BAR_MARKER | 4 | 0 | 1 | 0.25 | nan |
| BOX | 111 | 281 | 5 | 0.05 | 0.02 |
| BRACKET | 85 | 132 | 1 | 0.01 | 0.01 |
| CONTEXT_LINE | 9 | 202 | 3 | 0.33 | 0.01 |
| CONTEXT_RANGE | 6 | 165 | 0 | 0.00 | 0.00 |
| LABEL_TF | 63 | 156 | 4 | 0.06 | 0.03 |
| LEVEL_CARRIED | 48 | 275 | 6 | 0.12 | 0.02 |
| MINI_LEVEL | 32 | 9 | 5 | 0.16 | 0.56 |
| PATTERN_LINE | 186 | 491 | 4 | 0.02 | 0.01 |
| RANGE_OPEN | 8 | 58 | 1 | 0.12 | 0.02 |
| SQUEEZE | 2 | 91 | 0 | 0.00 | 0.00 |

- clutter ratio median: **4.33** (n=181 panels)
- LABEL_TF agreement on matched boxes: **0.00** (0/1)
- re_anchor events: 740 (all edge moves are logged by construction)
- excluded: 36 unusable/fragment, 5 time_only (time/type only)
- panels: 198
