# RECALL@K — R17 §17.3 author-budget measurement

Regenerated 2026-09-22 05:56Z by EVAL-AUDIT from cache (R38 s.38.1); matches GATE_PACK_9283b389: yes

At each golden decision time tau only the top-k live objects are scored.  Ranking: object -> born cand_log score when linkable (kind + birth minute; ~97% of objects link), else recency.  k in (1, 2, 3, 5).

Rebuild provenance: cache pickles `run_*` under evalcheck/_cache (read-only).  linelab was never cached (store=False), re-run live at the same file hash.  Supersedes the BOX-LAB 04:33Z rewrite (quarantined at evalcheck/_quarantine/RECALL_AT_K_boxlab_0433Z_plus_lead_addendum.md); the numbers of record stay in GATE_PACK_9283b389.md (R38 §38.1).

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

## linelab (`ceef7d3fc610e67c`) — lab engine (own ranker), live re-run (never cached: store=False)

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
| line | 193 | 0.114 [0.07-0.16] | **0.124 [0.08-0.18]** | 0.140 [0.09-0.19] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## v1_STABLE_9283b389 (`9283b3892c7fe8fc`, variant=ab_base) — frozen STABLE, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (3/479) | 0.00..0.01 | 0.00 (0/4) | 0.01 (1/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.01 (1/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (13/479) | 0.01..0.04 | 0.00 (0/4) | 0.01 (1/106) | 0.04 (3/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.04 (8/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.05 (26/479) | 0.03..0.07 | 0.00 (0/4) | 0.02 (2/106) | 0.13 (11/85) | 0.11 (1/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.06 (11/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.08 (38/479) | 0.06..0.11 | 0.00 (0/4) | 0.02 (2/106) | 0.22 (19/85) | 0.11 (1/9) | 0.17 (1/6) | 0.02 (1/46) | 0.00 (0/30) | 0.08 (14/184) | 0.00 (0/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 10.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.017 [0.00-0.04]** | 0.034 [0.01-0.07] | 0.034 [0.00-0.07] | k=1 |
| bracket † | 85 | **0.224 [0.14-0.32]** | 0.247 [0.16-0.34] | 0.247 [0.16-0.34] | k=1 |
| level | 76 | **0.013 [0.00-0.04]** | 0.013 [0.00-0.04] | 0.013 [0.00-0.04] | k=1 |
| line | 193 | 0.052 [0.02-0.09] | **0.083 [0.05-0.12]** | 0.104 [0.06-0.15] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## lever_reviveON_samehash (`a62edc195a154775`, variant=ab_reviveON) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (5/479) | 0.00..0.02 | 0.00 (0/4) | 0.01 (1/106) | 0.02 (2/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.01 (1/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (16/479) | 0.02..0.05 | 0.00 (0/4) | 0.02 (2/106) | 0.05 (4/85) | 0.11 (1/9) | 0.00 (0/6) | 0.04 (2/46) | 0.00 (0/30) | 0.04 (7/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.05 (26/479) | 0.03..0.08 | 0.00 (0/4) | 0.03 (3/106) | 0.13 (11/85) | 0.11 (1/9) | 0.00 (0/6) | 0.04 (2/46) | 0.00 (0/30) | 0.05 (9/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.08 (37/479) | 0.05..0.10 | 0.00 (0/4) | 0.03 (3/106) | 0.20 (17/85) | 0.22 (2/9) | 0.17 (1/6) | 0.04 (2/46) | 0.00 (0/30) | 0.07 (12/184) | 0.00 (0/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 12.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.06]** | 0.034 [0.00-0.07] | 0.034 [0.00-0.07] | k=1 |
| bracket † | 85 | **0.271 [0.18-0.37]** | 0.318 [0.22-0.42] | 0.329 [0.23-0.44] | k=1 |
| level | 76 | **0.026 [0.00-0.07]** | 0.026 [0.00-0.06] | 0.026 [0.00-0.07] | k=1 |
| line | 193 | 0.047 [0.02-0.08] | **0.073 [0.04-0.11]** | 0.093 [0.05-0.14] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## lever_markerON_samehash (`a62edc195a154775`, variant=ab_markerON) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (3/479) | 0.00..0.01 | 0.00 (0/4) | 0.01 (1/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.01 (1/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (14/479) | 0.01..0.05 | 0.00 (0/4) | 0.01 (1/106) | 0.05 (4/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.04 (8/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.06 (27/479) | 0.04..0.08 | 0.00 (0/4) | 0.03 (3/106) | 0.13 (11/85) | 0.11 (1/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.06 (11/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.08 (37/479) | 0.05..0.10 | 0.00 (0/4) | 0.03 (3/106) | 0.21 (18/85) | 0.11 (1/9) | 0.17 (1/6) | 0.02 (1/46) | 0.00 (0/30) | 0.07 (13/184) | 0.00 (0/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 9.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.06]** | 0.042 [0.01-0.08] | 0.042 [0.01-0.08] | k=1 |
| bracket † | 85 | **0.224 [0.14-0.32]** | 0.247 [0.16-0.34] | 0.259 [0.17-0.36] | k=1 |
| level | 76 | **0.013 [0.00-0.04]** | 0.013 [0.00-0.04] | 0.013 [0.00-0.04] | k=1 |
| line | 193 | 0.052 [0.02-0.08] | **0.078 [0.04-0.12]** | 0.098 [0.06-0.14] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## lever_tailON_samehash (`a62edc195a154775`, variant=ab_tailON) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (5/479) | 0.00..0.02 | 0.00 (0/4) | 0.02 (2/106) | 0.01 (1/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.01 (1/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (14/479) | 0.02..0.05 | 0.00 (0/4) | 0.02 (2/106) | 0.05 (4/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.04 (7/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.05 (26/479) | 0.03..0.08 | 0.00 (0/4) | 0.03 (3/106) | 0.12 (10/85) | 0.11 (1/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.06 (11/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.08 (39/479) | 0.06..0.11 | 0.00 (0/4) | 0.03 (3/106) | 0.22 (19/85) | 0.11 (1/9) | 0.17 (1/6) | 0.02 (1/46) | 0.00 (0/30) | 0.08 (14/184) | 0.00 (0/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.06]** | 0.042 [0.01-0.08] | 0.042 [0.01-0.08] | k=1 |
| bracket † | 85 | **0.235 [0.15-0.33]** | 0.247 [0.15-0.35] | 0.247 [0.16-0.34] | k=1 |
| level | 76 | **0.013 [0.00-0.05]** | 0.013 [0.00-0.04] | 0.013 [0.00-0.04] | k=1 |
| line | 193 | 0.052 [0.02-0.09] | **0.083 [0.04-0.12]** | 0.098 [0.06-0.14] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## lever_budgetGOLD_samehash (`a62edc195a154775`, variant=ab_budgetGOLD) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (5/479) | 0.00..0.02 | 0.00 (0/4) | 0.01 (1/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (12/479) | 0.01..0.04 | 0.00 (0/4) | 0.02 (2/106) | 0.02 (2/85) | 0.11 (1/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.03 (6/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.04 (18/479) | 0.02..0.06 | 0.00 (0/4) | 0.03 (3/106) | 0.02 (2/85) | 0.11 (1/9) | 0.17 (1/6) | 0.02 (1/46) | 0.00 (0/30) | 0.05 (9/184) | 0.14 (1/7) | 0.00 (0/2) |
| 5 | 0.05 (25/479) | 0.03..0.07 | 0.00 (0/4) | 0.03 (3/106) | 0.06 (5/85) | 0.11 (1/9) | 0.17 (1/6) | 0.02 (1/46) | 0.00 (0/30) | 0.07 (13/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 7.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.034 [0.01-0.07]** | 0.042 [0.01-0.08] | 0.042 [0.01-0.08] | k=1 |
| bracket † | 85 | **0.082 [0.03-0.15]** | 0.082 [0.03-0.15] | 0.082 [0.03-0.14] | k=1 |
| level | 76 | **0.013 [0.00-0.04]** | 0.013 [0.00-0.04] | 0.013 [0.00-0.04] | k=1 |
| line | 193 | 0.052 [0.02-0.08] | **0.078 [0.04-0.11]** | 0.078 [0.04-0.12] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## lab_defended_origin_ON (`e3538ee74029223f`, variant=ab_labON) — lab ranker, not engine, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (3/479) | 0.00..0.01 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.04 (2/46) | 0.00 (0/30) | 0.01 (1/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (14/479) | 0.01..0.04 | 0.00 (0/4) | 0.00 (0/106) | 0.04 (3/85) | 0.00 (0/9) | 0.00 (0/6) | 0.07 (3/46) | 0.00 (0/30) | 0.04 (8/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.06 (27/479) | 0.04..0.08 | 0.00 (0/4) | 0.01 (1/106) | 0.12 (10/85) | 0.11 (1/9) | 0.00 (0/6) | 0.09 (4/46) | 0.00 (0/30) | 0.06 (11/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.08 (38/479) | 0.05..0.10 | 0.00 (0/4) | 0.02 (2/106) | 0.18 (15/85) | 0.11 (1/9) | 0.17 (1/6) | 0.09 (4/46) | 0.00 (0/30) | 0.08 (15/184) | 0.00 (0/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.008 [0.00-0.03]** | 0.034 [0.01-0.07] | 0.034 [0.01-0.07] | k=1 |
| bracket † | 85 | **0.212 [0.13-0.30]** | 0.224 [0.14-0.32] | 0.224 [0.14-0.32] | k=1 |
| level | 76 | **0.053 [0.01-0.11]** | 0.066 [0.01-0.12] | 0.066 [0.01-0.13] | k=1 |
| line | 193 | 0.073 [0.04-0.11] | **0.088 [0.05-0.13]** | 0.109 [0.07-0.15] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## lab_defended_v2 (`e3538ee74029223f`, variant=ab_labV2) — lab ranker, not engine, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (5/479) | 0.00..0.02 | 0.00 (0/4) | 0.01 (1/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.04 (2/46) | 0.00 (0/30) | 0.01 (2/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (12/479) | 0.01..0.04 | 0.00 (0/4) | 0.01 (1/106) | 0.04 (3/85) | 0.00 (0/9) | 0.00 (0/6) | 0.04 (2/46) | 0.00 (0/30) | 0.03 (6/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.05 (25/479) | 0.03..0.07 | 0.00 (0/4) | 0.03 (3/106) | 0.09 (8/85) | 0.11 (1/9) | 0.00 (0/6) | 0.04 (2/46) | 0.00 (0/30) | 0.06 (11/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.08 (39/479) | 0.06..0.11 | 0.00 (0/4) | 0.03 (3/106) | 0.24 (20/85) | 0.11 (1/9) | 0.00 (0/6) | 0.04 (2/46) | 0.00 (0/30) | 0.07 (13/184) | 0.00 (0/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 11.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.06]** | 0.042 [0.01-0.08] | 0.042 [0.01-0.09] | k=1 |
| bracket † | 85 | **0.235 [0.15-0.33]** | 0.259 [0.17-0.35] | 0.259 [0.17-0.35] | k=1 |
| level | 76 | **0.026 [0.00-0.06]** | 0.039 [0.00-0.09] | 0.039 [0.00-0.09] | k=1 |
| line | 193 | 0.047 [0.02-0.08] | **0.078 [0.04-0.12]** | 0.098 [0.06-0.14] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## lever_famledger_samehash (`9283b3892c7fe8fc`, variant=ab_famledger) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (3/479) | 0.00..0.01 | 0.00 (0/4) | 0.01 (1/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.01 (1/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.04 (19/479) | 0.02..0.06 | 0.00 (0/4) | 0.02 (2/106) | 0.05 (4/85) | 0.22 (2/9) | 0.00 (0/6) | 0.04 (2/46) | 0.00 (0/30) | 0.05 (9/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.06 (29/479) | 0.04..0.08 | 0.00 (0/4) | 0.02 (2/106) | 0.15 (13/85) | 0.22 (2/9) | 0.00 (0/6) | 0.04 (2/46) | 0.00 (0/30) | 0.05 (10/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.09 (41/479) | 0.06..0.11 | 0.00 (0/4) | 0.02 (2/106) | 0.26 (22/85) | 0.22 (2/9) | 0.00 (0/6) | 0.04 (2/46) | 0.00 (0/30) | 0.07 (13/184) | 0.00 (0/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 10.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.06]** | 0.025 [0.00-0.05] | 0.025 [0.00-0.06] | k=1 |
| bracket † | 85 | **0.271 [0.18-0.37]** | 0.282 [0.19-0.38] | 0.282 [0.18-0.39] | k=1 |
| level | 76 | **0.026 [0.00-0.07]** | 0.026 [0.00-0.06] | 0.026 [0.00-0.07] | k=1 |
| line | 193 | 0.073 [0.04-0.11] | **0.109 [0.07-0.15]** | 0.109 [0.06-0.15] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

## lever_famledgerV2_samehash_keeprule_pass (`9283b3892c7fe8fc`, variant=ab_famledgerV2) — lever, cache-only

| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (4/479) | 0.00..0.02 | 0.00 (0/4) | 0.01 (1/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.00 (0/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.03 (15/479) | 0.02..0.05 | 0.00 (0/4) | 0.02 (2/106) | 0.02 (2/85) | 0.22 (2/9) | 0.00 (0/6) | 0.00 (0/46) | 0.00 (0/30) | 0.05 (9/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.05 (25/479) | 0.03..0.07 | 0.00 (0/4) | 0.03 (3/106) | 0.11 (9/85) | 0.22 (2/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.05 (10/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.09 (42/479) | 0.06..0.11 | 0.00 (0/4) | 0.03 (3/106) | 0.26 (22/85) | 0.22 (2/9) | 0.00 (0/6) | 0.04 (2/46) | 0.03 (1/30) | 0.07 (12/184) | 0.00 (0/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)

median live objects at tau: 10.0; tau-rows: 456

per-family recall@k (top-k within the golden's own family at its tau):

| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.034 [0.01-0.07]** | 0.034 [0.01-0.07] | 0.034 [0.00-0.07] | k=1 |
| bracket † | 85 | **0.282 [0.19-0.38]** | 0.294 [0.20-0.39] | 0.294 [0.20-0.39] | k=1 |
| level | 76 | **0.026 [0.00-0.07]** | 0.053 [0.01-0.11] | 0.053 [0.01-0.11] | k=1 |
| line | 193 | 0.073 [0.04-0.11] | **0.109 [0.06-0.16]** | 0.109 [0.07-0.15] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)

ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)

