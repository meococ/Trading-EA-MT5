# RECALL@K — R17 §17.3 author-budget measurement

Generated: 2026-09-22 04:19Z UTC.  At each golden decision time tau only the top-k live objects are scored.  Ranking: object -> born cand_log score when linkable (kind + birth minute; ~97% of objects link), else recency.  k in (1, 2, 3, 5).

## base (`b9f968b121629ce6`, variant=c1r_base) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (5/479) | 0.00..0.02 | 0.00 (0/4) | 0.00 (0/106) | 0.01 (1/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.00 (0/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (16/479) | 0.02..0.05 | 0.00 (0/4) | 0.03 (3/106) | 0.07 (6/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.07 (33/479) | 0.05..0.09 | 0.00 (0/4) | 0.03 (3/106) | 0.25 (21/85) | 0.11 (1/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (4/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.10 (48/479) | 0.07..0.13 | 0.00 (0/4) | 0.03 (3/106) | 0.38 (32/85) | 0.11 (1/9) | 0.17 (1/6) | 0.09 (4/46) | 0.00 (0/30) | 0.03 (6/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.05]** | 0.042 [0.01-0.08] | 0.042 [0.01-0.08] | k=1 |
| bracket † | 85 | **0.329 [0.24-0.43]** | 0.435 [0.33-0.55] | 0.435 [0.33-0.54] | k=1 |
| level | 76 | **0.053 [0.01-0.11]** | 0.053 [0.01-0.11] | 0.053 [0.01-0.11] | k=1 |
| line | 193 | 0.073 [0.04-0.11] | **0.093 [0.05-0.14]** | 0.098 [0.06-0.14] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## leg (`b9f968b121629ce6`, variant=c1r_leg) — lever, cache-only

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
| bracket † | 85 | **0.329 [0.24-0.42]** | 0.447 [0.34-0.56] | 0.447 [0.34-0.55] | k=1 |
| level | 76 | **0.053 [0.01-0.12]** | 0.053 [0.01-0.10] | 0.053 [0.01-0.11] | k=1 |
| line | 193 | 0.073 [0.04-0.11] | **0.093 [0.05-0.14]** | 0.098 [0.06-0.15] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## wick (`b9f968b121629ce6`, variant=c1r_wick) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (5/479) | 0.00..0.02 | 0.00 (0/4) | 0.00 (0/106) | 0.01 (1/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.00 (0/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (16/479) | 0.02..0.05 | 0.00 (0/4) | 0.03 (3/106) | 0.07 (6/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.07 (33/479) | 0.05..0.09 | 0.00 (0/4) | 0.03 (3/106) | 0.25 (21/85) | 0.11 (1/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (4/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.10 (48/479) | 0.07..0.13 | 0.00 (0/4) | 0.03 (3/106) | 0.38 (32/85) | 0.11 (1/9) | 0.17 (1/6) | 0.09 (4/46) | 0.00 (0/30) | 0.03 (6/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.05]** | 0.042 [0.01-0.08] | 0.042 [0.01-0.08] | k=1 |
| bracket † | 85 | **0.329 [0.23-0.43]** | 0.435 [0.33-0.54] | 0.435 [0.33-0.55] | k=1 |
| level | 76 | **0.053 [0.01-0.11]** | 0.053 [0.01-0.11] | 0.053 [0.01-0.11] | k=1 |
| line | 193 | 0.073 [0.04-0.11] | **0.093 [0.05-0.14]** | 0.098 [0.06-0.14] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## dense (`b9f968b121629ce6`, variant=c1r_dense) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (7/479) | 0.01..0.03 | 0.00 (0/4) | 0.01 (1/106) | 0.02 (2/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.00 (0/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (12/479) | 0.01..0.04 | 0.00 (0/4) | 0.01 (1/106) | 0.06 (5/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.01 (2/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.06 (29/479) | 0.04..0.08 | 0.00 (0/4) | 0.01 (1/106) | 0.24 (20/85) | 0.11 (1/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.09 (45/479) | 0.07..0.12 | 0.00 (0/4) | 0.01 (1/106) | 0.36 (31/85) | 0.11 (1/9) | 0.17 (1/6) | 0.09 (4/46) | 0.00 (0/30) | 0.03 (6/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.008 [0.00-0.03]** | 0.025 [0.00-0.06] | 0.025 [0.00-0.06] | k=1 |
| bracket † | 85 | **0.318 [0.22-0.42]** | 0.459 [0.35-0.56] | 0.459 [0.35-0.57] | k=1 |
| level | 76 | **0.053 [0.01-0.10]** | 0.053 [0.01-0.11] | 0.053 [0.01-0.11] | k=1 |
| line | 193 | 0.067 [0.03-0.10] | **0.088 [0.05-0.13]** | 0.093 [0.05-0.14] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## dedup (`b9f968b121629ce6`, variant=c1r_dedup) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (5/479) | 0.00..0.02 | 0.00 (0/4) | 0.00 (0/106) | 0.01 (1/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.00 (0/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (16/479) | 0.02..0.05 | 0.00 (0/4) | 0.03 (3/106) | 0.07 (6/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.07 (33/479) | 0.05..0.09 | 0.00 (0/4) | 0.03 (3/106) | 0.25 (21/85) | 0.11 (1/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (4/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.10 (48/479) | 0.07..0.13 | 0.00 (0/4) | 0.03 (3/106) | 0.38 (32/85) | 0.11 (1/9) | 0.17 (1/6) | 0.09 (4/46) | 0.00 (0/30) | 0.03 (6/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.06]** | 0.042 [0.01-0.08] | 0.042 [0.01-0.08] | k=1 |
| bracket † | 85 | **0.329 [0.24-0.43]** | 0.435 [0.33-0.54] | 0.435 [0.33-0.54] | k=1 |
| level | 76 | **0.053 [0.01-0.11]** | 0.053 [0.00-0.10] | 0.053 [0.01-0.10] | k=1 |
| line | 193 | 0.073 [0.04-0.11] | **0.093 [0.06-0.14]** | 0.098 [0.06-0.14] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## watch (`ffd74452b8523cbc`, variant=c1r_watch) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (3/479) | 0.00..0.01 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.07 (3/46) | 0.00 (0/30) | 0.00 (0/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (15/479) | 0.02..0.05 | 0.00 (0/4) | 0.01 (1/106) | 0.09 (8/85) | 0.11 (1/9) | 0.00 (0/6) | 0.07 (3/46) | 0.00 (0/30) | 0.01 (1/184) | 0.14 (1/7) | 0.00 (0/2) |
| 3 | 0.06 (28/479) | 0.04..0.08 | 0.00 (0/4) | 0.01 (1/106) | 0.22 (19/85) | 0.11 (1/9) | 0.00 (0/6) | 0.07 (3/46) | 0.00 (0/30) | 0.02 (3/184) | 0.14 (1/7) | 0.00 (0/2) |
| 5 | 0.10 (50/479) | 0.08..0.13 | 0.00 (0/4) | 0.01 (1/106) | 0.40 (34/85) | 0.22 (2/9) | 0.17 (1/6) | 0.07 (3/46) | 0.00 (0/30) | 0.04 (8/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.017 [0.00-0.04]** | 0.025 [0.00-0.06] | 0.034 [0.01-0.07] | k=1 |
| bracket † | 85 | **0.341 [0.24-0.45]** | 0.388 [0.29-0.49] | 0.412 [0.30-0.52] | k=1 |
| level | 76 | **0.039 [0.00-0.09]** | 0.039 [0.00-0.09] | 0.039 [0.00-0.09] | k=1 |
| line | 193 | 0.067 [0.04-0.11] | **0.088 [0.05-0.13]** | 0.093 [0.05-0.13] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## tail (`ffd74452b8523cbc`, variant=c1r_tail) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (7/479) | 0.00..0.03 | 0.00 (0/4) | 0.01 (1/106) | 0.01 (1/85) | 0.00 (0/9) | 0.00 (0/6) | 0.11 (5/46) | 0.00 (0/30) | 0.00 (0/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.04 (17/479) | 0.02..0.05 | 0.00 (0/4) | 0.03 (3/106) | 0.09 (8/85) | 0.00 (0/9) | 0.00 (0/6) | 0.11 (5/46) | 0.00 (0/30) | 0.01 (1/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.08 (36/479) | 0.05..0.10 | 0.00 (0/4) | 0.04 (4/106) | 0.27 (23/85) | 0.11 (1/9) | 0.00 (0/6) | 0.11 (5/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.11 (52/479) | 0.08..0.14 | 0.00 (0/4) | 0.04 (4/106) | 0.41 (35/85) | 0.11 (1/9) | 0.17 (1/6) | 0.11 (5/46) | 0.00 (0/30) | 0.03 (5/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.034 [0.01-0.07]** | 0.059 [0.02-0.10] | 0.059 [0.02-0.10] | k=1 |
| bracket † | 85 | **0.353 [0.24-0.46]** | 0.459 [0.35-0.56] | 0.459 [0.36-0.56] | k=1 |
| level | 76 | **0.066 [0.01-0.13]** | 0.066 [0.01-0.13] | 0.066 [0.01-0.12] | k=1 |
| line | 193 | 0.067 [0.03-0.11] | **0.083 [0.05-0.13]** | 0.088 [0.05-0.13] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## watchtail (`ffd74452b8523cbc`, variant=c1r_watchtail) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (4/479) | 0.00..0.02 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.00 (0/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (15/479) | 0.02..0.05 | 0.00 (0/4) | 0.00 (0/106) | 0.09 (8/85) | 0.11 (1/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.01 (1/184) | 0.14 (1/7) | 0.00 (0/2) |
| 3 | 0.06 (30/479) | 0.04..0.08 | 0.00 (0/4) | 0.01 (1/106) | 0.24 (20/85) | 0.11 (1/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (3/184) | 0.14 (1/7) | 0.00 (0/2) |
| 5 | 0.10 (48/479) | 0.07..0.13 | 0.00 (0/4) | 0.01 (1/106) | 0.40 (34/85) | 0.22 (2/9) | 0.17 (1/6) | 0.09 (4/46) | 0.00 (0/30) | 0.03 (5/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.017 [0.00-0.04]** | 0.034 [0.01-0.07] | 0.034 [0.01-0.07] | k=1 |
| bracket † | 85 | **0.341 [0.24-0.45]** | 0.388 [0.28-0.49] | 0.412 [0.31-0.51] | k=1 |
| level | 76 | **0.053 [0.01-0.11]** | 0.053 [0.01-0.11] | 0.053 [0.01-0.11] | k=1 |
| line | 193 | 0.052 [0.02-0.09] | **0.073 [0.04-0.11]** | 0.073 [0.04-0.11] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## score (`3ab5f3aa9d085cc5`, variant=c1r_score) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (5/479) | 0.00..0.02 | 0.00 (0/4) | 0.00 (0/106) | 0.01 (1/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.00 (0/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (16/479) | 0.02..0.05 | 0.00 (0/4) | 0.03 (3/106) | 0.07 (6/85) | 0.00 (0/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.07 (33/479) | 0.05..0.09 | 0.00 (0/4) | 0.03 (3/106) | 0.25 (21/85) | 0.11 (1/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.02 (4/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.10 (48/479) | 0.07..0.12 | 0.00 (0/4) | 0.03 (3/106) | 0.38 (32/85) | 0.11 (1/9) | 0.17 (1/6) | 0.09 (4/46) | 0.00 (0/30) | 0.03 (6/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.06]** | 0.042 [0.01-0.08] | 0.042 [0.01-0.09] | k=1 |
| bracket † | 85 | **0.329 [0.23-0.43]** | 0.435 [0.33-0.54] | 0.435 [0.33-0.55] | k=1 |
| level | 76 | **0.053 [0.01-0.11]** | 0.053 [0.01-0.11] | 0.053 [0.01-0.11] | k=1 |
| line | 193 | 0.073 [0.04-0.11] | **0.093 [0.05-0.14]** | 0.098 [0.06-0.14] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## all (`3ab5f3aa9d085cc5`, variant=c1r_all) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (3/479) | 0.00..0.01 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.07 (3/46) | 0.00 (0/30) | 0.00 (0/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.02 (10/479) | 0.01..0.03 | 0.00 (0/4) | 0.00 (0/106) | 0.06 (5/85) | 0.00 (0/9) | 0.00 (0/6) | 0.07 (3/46) | 0.00 (0/30) | 0.01 (1/184) | 0.14 (1/7) | 0.00 (0/2) |
| 3 | 0.05 (25/479) | 0.03..0.07 | 0.00 (0/4) | 0.00 (0/106) | 0.21 (18/85) | 0.11 (1/9) | 0.00 (0/6) | 0.07 (3/46) | 0.00 (0/30) | 0.01 (2/184) | 0.14 (1/7) | 0.00 (0/2) |
| 5 | 0.09 (45/479) | 0.07..0.12 | 0.00 (0/4) | 0.00 (0/106) | 0.40 (34/85) | 0.11 (1/9) | 0.17 (1/6) | 0.07 (3/46) | 0.00 (0/30) | 0.03 (5/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.008 [0.00-0.03]** | 0.025 [0.00-0.06] | 0.025 [0.00-0.05] | k=1 |
| bracket † | 85 | **0.341 [0.25-0.45]** | 0.388 [0.28-0.49] | 0.412 [0.31-0.52] | k=1 |
| level | 76 | **0.039 [0.00-0.09]** | 0.039 [0.00-0.09] | 0.039 [0.00-0.09] | k=1 |
| line | 193 | 0.052 [0.03-0.09] | **0.073 [0.04-0.11]** | 0.073 [0.04-0.11] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## watch_fl (`3ab5f3aa9d085cc5`, variant=c1r_watch_fl) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (7/479) | 0.00..0.03 | 0.00 (0/4) | 0.00 (0/106) | 0.05 (4/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.01 (1/184) | 0.14 (1/7) | 0.00 (0/2) |
| 2 | 0.04 (18/479) | 0.02..0.05 | 0.00 (0/4) | 0.02 (2/106) | 0.12 (10/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.02 (4/184) | 0.14 (1/7) | 0.00 (0/2) |
| 3 | 0.06 (28/479) | 0.04..0.08 | 0.00 (0/4) | 0.02 (2/106) | 0.20 (17/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.04 (7/184) | 0.14 (1/7) | 0.00 (0/2) |
| 5 | 0.09 (42/479) | 0.06..0.11 | 0.00 (0/4) | 0.02 (2/106) | 0.27 (23/85) | 0.22 (2/9) | 0.00 (0/6) | 0.02 (1/46) | 0.03 (1/30) | 0.07 (12/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.06]** | 0.025 [0.00-0.05] | 0.025 [0.00-0.06] | k=1 |
| bracket † | 85 | **0.282 [0.19-0.38]** | 0.306 [0.21-0.40] | 0.306 [0.21-0.41] | k=1 |
| level | 76 | **0.026 [0.00-0.07]** | 0.053 [0.01-0.11] | 0.053 [0.01-0.11] | k=1 |
| line | 193 | 0.067 [0.03-0.11] | **0.098 [0.06-0.14]** | 0.124 [0.08-0.17] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

