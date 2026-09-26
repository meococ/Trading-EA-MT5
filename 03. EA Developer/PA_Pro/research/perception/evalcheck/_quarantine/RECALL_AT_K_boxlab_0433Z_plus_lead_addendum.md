# RECALL@K — R17 §17.3 author-budget measurement

Generated: 2026-09-22 04:28Z UTC.  At each golden decision time tau only the top-k live objects are scored.  Ranking: object -> born cand_log score when linkable (kind + birth minute; ~97% of objects link), else recency.  k in (1, 2, 3, 5).

## v0 (`63c771d64e18f619`)

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.04 (20/479) | 0.02..0.06 | 0.00 (0/4) | 0.06 (6/106) | 0.12 (10/85) | 0.00 (0/9) | 0.00 (0/6) | 0.07 (3/46) | 0.00 (0/30) | 0.01 (1/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.07 (34/479) | 0.05..0.10 | 0.00 (0/4) | 0.10 (11/106) | 0.19 (16/85) | 0.11 (1/9) | 0.00 (0/6) | 0.07 (3/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.09 (44/479) | 0.07..0.12 | 0.00 (0/4) | 0.11 (12/106) | 0.24 (20/85) | 0.11 (1/9) | 0.17 (1/6) | 0.07 (3/46) | 0.00 (0/30) | 0.04 (7/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.14 (68/479) | 0.11..0.17 | 0.00 (0/4) | 0.13 (14/106) | 0.39 (33/85) | 0.22 (2/9) | 0.17 (1/6) | 0.09 (4/46) | 0.00 (0/30) | 0.08 (14/184) | 0.00 (0/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 16.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.134 [0.07-0.20]** | 0.134 [0.08-0.20] | 0.143 [0.08-0.21] | k=1 |
| bracket † | 85 | **0.388 [0.29-0.49]** | 0.659 [0.55-0.76] | 0.729 [0.63-0.82] | k=1 |
| level | 76 | **0.066 [0.01-0.12]** | 0.066 [0.01-0.13] | 0.066 [0.01-0.13] | k=1 |
| line | 193 | 0.052 [0.02-0.08] | **0.093 [0.05-0.14]** | 0.104 [0.06-0.15] | k=2 |
| squeeze | 2 | 0.500 [0.00-1.00] | 0.500 [0.00-1.00] | 0.500 [0.00-1.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## v1 (`e62f2dc9ee7fa6e2`)

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (5/479) | 0.00..0.02 | 0.00 (0/4) | 0.00 (0/106) | 0.01 (1/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.00 (0/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (16/479) | 0.02..0.05 | 0.00 (0/4) | 0.03 (3/106) | 0.07 (6/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.07 (33/479) | 0.05..0.09 | 0.00 (0/4) | 0.03 (3/106) | 0.25 (21/85) | 0.11 (1/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (4/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.10 (48/479) | 0.08..0.13 | 0.00 (0/4) | 0.03 (3/106) | 0.38 (32/85) | 0.11 (1/9) | 0.17 (1/6) | 0.09 (4/46) | 0.00 (0/30) | 0.03 (6/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.06]** | 0.042 [0.01-0.08] | 0.042 [0.01-0.08] | k=1 |
| bracket † | 85 | **0.329 [0.24-0.42]** | 0.435 [0.33-0.54] | 0.435 [0.33-0.55] | k=1 |
| level | 76 | **0.053 [0.01-0.12]** | 0.053 [0.01-0.10] | 0.053 [0.01-0.11] | k=1 |
| line | 193 | 0.073 [0.04-0.11] | **0.093 [0.05-0.14]** | 0.098 [0.06-0.15] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## linelab (`ceef7d3fc610e67c`)

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.05 (22/479) | 0.03..0.07 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.11 (1/9) | 0.00 (0/6) | 0.00 (0/46) | 0.00 (0/30) | 0.11 (21/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.05 (24/479) | 0.03..0.07 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.22 (2/9) | 0.00 (0/6) | 0.00 (0/46) | 0.00 (0/30) | 0.12 (22/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.06 (27/479) | 0.04..0.08 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.22 (2/9) | 0.00 (0/6) | 0.00 (0/46) | 0.00 (0/30) | 0.14 (25/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.06 (27/479) | 0.04..0.08 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.22 (2/9) | 0.00 (0/6) | 0.00 (0/46) | 0.00 (0/30) | 0.14 (25/184) | 0.00 (0/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 4.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.000 [0.00-0.00]** | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | k=1 |
| bracket † | 85 | **0.000 [0.00-0.00]** | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | k=1 |
| level | 76 | **0.000 [0.00-0.00]** | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | k=1 |
| line | 193 | 0.114 [0.07-0.16] | **0.124 [0.08-0.17]** | 0.140 [0.09-0.19] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)


---
ADDENDUM (Lead, 2026-09-22 04:36Z; LEAD_RULINGS R38 §38.1): this file is NOT the frozen RECALL_AT_K.md of 2026-09-21 23:27:44Z (24490 B). That version was overwritten at about 04:28Z by a BOX-LAB run of recall_at_k.py; the content above is BOX-LAB's 04:33Z regeneration. The numbers of record are in GATE_PACK_9283b389.md (sha256 2CC4CCA277E7...). EVAL-AUDIT regenerates the frozen content and checks it against the pack.
