# GATE_PACK — data for the 22/09 ~01:00Z gate decision

Generated: 2026-09-21 23:40Z.  Tables only; the Lead writes the recommendation.

Gates (spec §6): BOX recall >= 0.70, BOX precision >= 0.60, PATTERN_LINE recall >= 0.50, LEVEL_CARRIED recall >= 0.60, T/F agreement on matched boxes >= 0.60, clutter ratio median <= 1.5.

## v0 (`63c771d64e18f619`)

| metric | value | CI95 (panel bootstrap) | gate | gap |
|---|---|---|---|---|
| BOX recall | 0.21 (23/108) | 0.13..0.30 | >=0.70 | -0.49 |
| BOX precision | 0.02 (27/1113) | 0.02..0.03 | >=0.60 | -0.58 |
| PATTERN_LINE recall | 0.11 (20/184) | 0.07..0.15 | >=0.50 | -0.39 |
| LEVEL_CARRIED recall | 0.15 (7/48) | 0.05..0.25 | >=0.60 | -0.45 |
| T/F agreement on matched boxes | 0.00 (0/4) | 0.00..0.00 | >=0.60 | -0.60 |
| clutter ratio (eng/gold per panel) | 9.00 | 8.33..10.00 | <=1.5 | +7.50 |

supporting: snapshot recall **0.22** (105/479); live clutter at tau median **16.00** (p10 9.00 / p90 21.50); oracle BOX **0.31** PATTERN_LINE **0.28**
trusted-subset (non-Tier-A) line recall: CONTEXT_LINE **0.22** (2/9); PATTERN_LINE **0.11** (15/141)

per-panel: golden objects/panel p10/p50/p90 = [1. 2. 4.]; engine objects/panel p10/p50/p90 = [18. 24. 29.]

## v1 (`584c7743924a8b1b`)

note: `pinned hash, cache-only variant=marker_off`; 198/198 panels served from cache

| metric | value | CI95 (panel bootstrap) | gate | gap |
|---|---|---|---|---|
| BOX recall | 0.06 (6/108) | 0.02..0.10 | >=0.70 | -0.64 |
| BOX precision | 0.02 (7/301) | 0.01..0.04 | >=0.60 | -0.58 |
| PATTERN_LINE recall | 0.10 (19/184) | 0.06..0.15 | >=0.50 | -0.40 |
| LEVEL_CARRIED recall | 0.12 (6/48) | 0.04..0.22 | >=0.60 | -0.47 |
| T/F agreement on matched boxes | 0.00 (0/1) | 0.00..0.00 | >=0.60 | -0.60 |
| clutter ratio (eng/gold per panel) | 5.00 | 4.42..5.50 | <=1.5 | +3.50 |

supporting: snapshot recall **0.10** (46/479); live clutter at tau median **10.00** (p10 7.00 / p90 14.00); oracle BOX **0.29** PATTERN_LINE **0.41**
trusted-subset (non-Tier-A) line recall: CONTEXT_LINE **0.22** (2/9); PATTERN_LINE **0.13** (18/141)

per-panel: golden objects/panel p10/p50/p90 = [1. 2. 4.]; engine objects/panel p10/p50/p90 = [10. 13. 16.]

## linelab (`ceef7d3fc610e67c`)

| metric | value | CI95 (panel bootstrap) | gate | gap |
|---|---|---|---|---|
| BOX recall | 0.00 (0/108) | 0.00..0.00 | >=0.70 | -0.70 |
| BOX precision | 0.00 (0/0) | 0.00..0.00 | >=0.60 | -0.60 |
| PATTERN_LINE recall | 0.14 (26/184) | 0.09..0.20 | >=0.50 | -0.36 |
| LEVEL_CARRIED recall | 0.00 (0/48) | 0.00..0.00 | >=0.60 | -0.60 |
| T/F agreement on matched boxes | — (no marks on matched boxes) | | >=0.60 | |
| clutter ratio (eng/gold per panel) | 2.00 | 1.75..2.33 | <=1.5 | +0.50 |

supporting: snapshot recall **0.06** (27/479); live clutter at tau median **4.00** (p10 2.00 / p90 6.00); oracle BOX **0.00** PATTERN_LINE **0.14**
trusted-subset (non-Tier-A) line recall: CONTEXT_LINE **0.22** (2/9); PATTERN_LINE **0.17** (24/141)

per-panel: golden objects/panel p10/p50/p90 = [1. 2. 4.]; engine objects/panel p10/p50/p90 = [3. 5. 7.]

## recall@k (R17 §17.3 author budget)

**v1 does not select better than v0 at the author's budget** — top-k snapshot recall, all families:

| engine | k=1 | k=2 | k=5 |
|---|---|---|---|
| v1 STABLE (`584c7743`) | 0.01 [0.00–0.02] | 0.01 [0.00–0.03] | 0.07 [0.05–0.10] |
| v0 | 0.04 [0.02–0.06] | 0.07 [0.05–0.10] | 0.14 [0.11–0.17] |

Cumulative BOX recall (unbudgeted): v1 **0.06** vs v0 **0.21**.  v1's edge is ink only — clutter ratio ~5.0 vs ~9.0, live objects at tau 10 vs 16.

**At the author's own budget, per family** (per-family recall@k at the family's budget k):

| arm | box @1 | level @1 | line @2 | bracket @1 † |
|---|---|---|---|---|
| v0 | 0.134 [0.07-0.20] | 0.066 [0.01-0.12] | 0.093 [0.05-0.14] | 0.388 [0.29-0.49] |
| v1 STABLE | 0.025 [0.00-0.06] | 0.013 [0.00-0.04] | 0.078 [0.04-0.12] | 0.224 [0.14-0.32] |
| linelab | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.124 [0.08-0.18] | 0.000 [0.00-0.00] |
| famledger (c) | 0.034 [0.01-0.07] | 0.026 [0.00-0.07] | 0.109 [0.06-0.16] | 0.282 [0.19-0.38] |

† upper bound (R30 §30.3)

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
| line | 193 | 0.114 [0.07-0.16] | **0.124 [0.08-0.18]** | 0.140 [0.09-0.19] | k=2 |
| squeeze | 2 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
author per-family budget (birth-rate params, golden p90): box k=1, line k=2, level k=1, bracket k=1 — budget-k cells in bold
† ruler: BRACKET rule has no price check — every bracket figure is an upper bound (R30 §30.3)
ranking provenance: object-carried salience score when present, else born `cand_log` score linked on (kind + birth minute), else recency by `t_birth` (R20 §20.4.2)
## v1_STABLE_584c7743 (`584c7743924a8b1b`, variant=marker_off) — frozen STABLE, cache-only
| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (4/479) | 0.00..0.02 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.01 (7/479) | 0.00..0.03 | 0.00 (0/4) | 0.01 (1/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.03 (5/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.03 (15/479) | 0.02..0.05 | 0.00 (0/4) | 0.02 (2/106) | 0.01 (1/85) | 0.11 (1/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.05 (10/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.07 (34/479) | 0.05..0.10 | 0.00 (0/4) | 0.02 (2/106) | 0.14 (12/85) | 0.22 (2/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.09 (16/184) | 0.14 (1/7) | 0.00 (0/2) |
BRACKET column is an upper bound: the ruler's BRACKET rule has no price check (R30 §30.3)
median live objects at tau: 10.0; tau-rows: 456
per-family recall@k (top-k within the golden's own family at its tau):
| family | goldens | k=1 | k=2 | k=5 | author k |
|---|---|---|---|---|---|
| annot | 4 | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | 0.000 [0.00-0.00] | - |
| box | 119 | **0.025 [0.00-0.06]** | 0.034 [0.01-0.07] | 0.034 [0.00-0.07] | k=1 |
| bracket † | 85 | **0.224 [0.14-0.32]** | 0.247 [0.16-0.34] | 0.247 [0.16-0.34] | k=1 |
| level | 76 | **0.013 [0.00-0.04]** | 0.013 [0.00-0.04] | 0.013 [0.00-0.04] | k=1 |
| line | 193 | 0.052 [0.02-0.09] | **0.078 [0.04-0.12]** | 0.104 [0.06-0.15] | k=2 |
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

## plausibility (W1/W1b)

W1b: judge sensitivity 0.90, specificity 0.68 — SPEC < 0.70 -> plausibility-adjusted numbers UNRELIABLE (wide CIs); plausible-FP shares are Rogan-Gladen corrected (details: PLAUSIBILITY.md).  v1 FP sample was drawn at hash ef06f265; applying it to a different v1 state is an approximation.

R22 §22.3 + R30 §30.1: the blind judge is too lenient — specificity .67 on all 30 negatives, **.68 [.50-.86] on the 28 valid** (2 invalid: BRACKET price-shifts still match — the ruler's bracket rule has no price check). The invalid negatives do NOT explain the low specificity; plausibility stays **inconclusive** and the pack does NOT claim 'most engine extras are defensible'. A 20-item human sample is prepared under OWNER_JUDGE_PACK/.
OWNER_JUDGE_PACK: **GO** — 20 items re-rendered with a uniform per-kind tau event (BOX/CONTEXT_RANGE tau = drawn right edge for every class, killing the tau-inside-box tell) and a single blue ~2.5px item style (R30 §30.2); truth key outside the pack.

## levers (measured A/B arms — NOT the shipped engine)

Same-hash pairs (R24 §24.3): every arm ran in this lane at one code hash `a62edc19` with runtime flags (`arm_ab.py`, variants `ab_*`); base arm reproduced STABLE `584c7743` numbers exactly, so the deltas also read against the frozen default.

| lever | same-hash delta vs base | verdict |
|---|---|---|
| REQ-1(b) revive ON | BOX .06->.08, BRACKET .29->.38, LC .12->.10, snapR .10->.11; live clutter 10->12 | kept OUT of default (R20 §20.1: fails keep-rule on ink) — Owner lever: +2 BOX +7 BRACKET for +2 live |
| BAR_MARKER day_extreme_only ON | BOX .06->.06, PL .10->.09, LC .12->.12, BRACKET .29->.32, snapR .10, clutter 10->9 | flag OFF (PL -1, fails keep-rule); lever logged |
| BOX drawn tail (+12 bars) | BOX .06->.06, PL .10->.10, LC .12->.12, BRACKET .29->.31, snapR .10, clutter 10->11 | ~zero delta (BRACKET +2, clutter +1 — lane's 'zero' was close but not exact); lever |
| golden-faithful live budget (2/1/2/4) | BOX .06->.04, PL .10->.08, LC .12->.10, BRACKET .29->.11, snapR .10->.06, clutter 10->7 | REJECTED — score cannot select (R22 §22.1) |
| LABEL_TF cap exemption | cross-hash code arm (`28de3f03`): marks 242->462, BOX 9->6, LC 5->4 | REJECTED — not a runtime flag, excluded from same-hash table per R24 §24.3 |
| LEVEL-LAB `level.defended_origin` ON (lab flag, not shipped) | `e3538ee7` ab_labON: LC born .12->.21, BOX .06->.04, PL .10, BRACKET .29, snapR .10, clutter 10->11 | fails keep-rule (BOX -2) — lab lever only (R26) |
| LEVEL-LAB defended-origin + `def_mini_off` (lab flag) | `e3538ee7` ab_labV2: LC .12->.15, BOX .06 healed, PL .10->.09, clutter 11 | fails keep-rule (PL -1) — lab lever only (R26) |
| LEVEL-LAB + `def_all_lc` (lab flag) | `9283b389` ab_labV2B rerun complete: BOX .06, PL .10->.09, LC .12->.15, BRACKET .29->.33, snapR .10, clutter 10->11 | fails keep-rule (PL -1) — lab lever only (R26); completes the e3538ee7 run that aborted mid-edit |
| `salience.fam_ledger` only (arm b, `9283b389` ab_famledger) | BOX .06->.04, LC .12->.10, BRACKET .29->.35, snapR .10, clutter 10 | ledger-only fails keep-rule (BOX -2) — EVAL-AUDIT verified (R29 §29.1) |
| famledger v1 + defended LC (arm c, `9283b389` ab_famledgerV2) | LC born .12->.21 (+27/-15 per golden, verified R29 §29.1); BOX .06, PL .10, BRACKET .29->.35; engine top-k all families: k1 .006 vs base .01, k2 .025 vs .01, k5 .088 vs .07; LC at tau .065 | **famledger v1 + defended LC: keep-rule pass on born recall (verified); four kinds silenced (defect); no gain at the author's budget** — R29 §29.2 |
| d2 ceiling probe — LC share 2, rate_level_carried 2 (lab flag, not shipped) | LC born .229->.292; births 6->7/panel, clutter 2.5->3.0, live +1, flicker x2 | priced trade, not kept — ink leg fails (R29 §29.3) |

famledger (c) defects (R29 §29.2): kinds with no share entry are never born — CONTEXT_RANGE, CONTEXT_LINE, MINI_LEVEL, SQUEEZE silenced; the live budget, geometric NMS and bar timing are still shared, so 'loses no BOX' is partly outcome luck, not proof of isolation; `cont` routes bypass the ledger.  Read as a direction, not an author-budget result.  Re-measured by this lane with the object-score ranking now wired (R20 §20.4.2): k1 .008, k2 .031, k5 .088 — same flat conclusion as the R29-quoted .006/.025/.088.

## LEVEL-LAB V8 recall@k + CV (lab, TUNE)

## Recall@k — top-k levels live at τ (LC all | trusted)
| ranker | lab k1 / k2 / k3 | prod k1 / k2 / k3 | naive k1 / k2 / k3 |
|---|---|---|---|
| birth_score | .167 / .271 / .417 | .146 / .208 / .208 | .083 / .188 / .292 |
| dist | .146 / .229 / .271 | .146 / .167 / .188 | .188 / .250 / .312 |
| ndef | .188 / .250 / .354 | .125 / .167 / .167 | .188 / .271 / .354 |
| age | .167 / .312 / .438 | .125 / .167 / .167 | .083 / .167 / .208 |
| cls | .188 / .271 / .375 | .104 / .188 / .208 | .021 / .167 / .292 |
| **ret24** | **.188 / .333 / .417** | .146 / .208 / .208 | **.208 / .292 / .354** |
| barrier | .125 / .250 / .333 | .146 / .208 / .208 | .146 / .208 / .271 |
| combo | .125 / .312 / .375 | .125 / .167 / .167 | .188 / .292 / .312 |
MINI (all) — best @k2: lab ret24 **.387**, prod ndef/age/ret24/barrier .194,
naive dist .194 (@k3 .419).
## Day-level 5-fold CV (choose ranker on 4 folds, score on 5th)
| metric | lab | prod | naive |
|---|---|---|---|
| LC@1 | 0.107 | **0.171** | 0.127 |
| **LC@2** | **0.267** | 0.208 | 0.203 |
| MINI@2 | **0.264** | 0.082 | 0.137 |
LC@2 chosen rankers: lab ret24×3+age×2; prod birth_score×5; naive mixed.
Fold scores LC@2: lab .10/.33/.00/.40/.50, prod .20/.17/.22/.20/.25,
naive .20/.17/.00/.40/.25 — high day-level variance (~10 goldens/fold).
**Integration condition (mandate §4): lab beats both prod and naive at
k = 2 under CV** (0.267 vs 0.208/0.203), and on MINI@2 (0.264 vs
0.082/0.137). **Caveat: at k = 1 lab LOSES to prod** (0.107 vs 0.171) —
a single-slot budget would make the production stream better; the lab
edge needs ≥ 2 live slots to exist. The k = 2..3 regime is the one the
author's ink actually occupies (~2 objects/panel).
source: levellab/ROUND_L7.md

## definitions & reconciliation (R15 §15.4)

- **Clutter gate** = median of engine_objects/golden_objects per panel (the row 'clutter ratio'); the live-objects-at-tau median is a separate diagnostic, not the gate.
- **T/F agreement** is computed only on golden marks that sit inside a MATCHED golden box's span (n shown in the row).
- **tau per family** (snapshot / recall@k decision time, R21 §21.2): BOX and all lines = golden `build_end` (the LAST contained bar before the break, not the break bar itself), else drawn `t1` when `build_end` is absent; LEVEL_CARRIED / MINI_LEVEL = `t0` + 10 min; BRACKET / SQUEEZE = `t1`; BAR_MARKER = `t0`.
- **Oracle (SCOREBOARD vs FUNNEL):** same `cand_right` rule, different aggregation. Scoreboard credits a golden when ANY same-family candidate is a right proposal (a candidate may credit several goldens); funnel assigns each candidate to its single best golden (best_cand_match). On ef06f265: PL oracle .397 (any) vs .375 (assigned) — a 4-golden gap. This pack reports the scoreboard (any) convention; funnel's is the stricter bound.
- **Born recall:** funnel fills missing golden t0/t1 with the panel window before matching (gold_with_keys mutates); scoreboard/gate_pack match the ruler on raw goldens. On ef06f265 LC born: 7/48 (.146) funnel vs 6/48 (.125) raw. This pack reports raw-golden recall.
- **Ruler caveat (W0 / R19 §19.1):** v1 BOX windows use proposal-time ends (`meta_build_end` = proposal bar); conversion to break-time ends (`break_bar`) measured NET on cached runs: +2 gains / -1 loss -> net +1 of 108 (~+0.01 recall) on v1@1f4bed5b and v1@4aaa6a7a; 0 on v0. Ruler frozen; not adopted before the morning.

## scoreboard history (all rows)

| 2026-09-21 18:27Z | v0 | 63c771d6 | 50e11fd5 | 0.21/0.02 | 0.11/0.02 | 0.15/0.02 | 0.24 | 0.31 | 0.28 | 16.00 | 0.22 |
| 2026-09-21 18:27Z | v1 | 694313a3 | 50e11fd5 | 0.05/0.02 | 0.11/0.04 | 0.10/0.02 | 0.06 | 0.30 | 0.39 | 11.00 | 0.08 |
| 2026-09-21 18:51Z | v1 | ef06f265 | 50e11fd5 | 0.06/0.02 | 0.10/0.03 | 0.12/0.03 | 0.07 | 0.29 | 0.40 | 10.00 | 0.08 |
| 2026-09-21 18:57Z | v1 | ef06f265 | 50e11fd5 | 0.06/0.02 | 0.10/0.03 | 0.12/0.03 | 0.07 | 0.29 | 0.40 | 10.00 | 0.08 |
| 2026-09-21 19:12Z | v1 | 97cc437f | 50e11fd5 | 0.15/0.02 | 0.19/0.03 | 0.12/0.02 | 0.16 | 0.32 | 0.41 | 15.00 | 0.14 |
| 2026-09-21 19:31Z | v1 | cb2794f5 | 50e11fd5 | 0.06/0.02 | 0.10/0.03 | 0.12/0.03 | 0.07 | 0.29 | 0.40 | 10.00 | 0.08 |
| 2026-09-21 19:33Z | v1 | 1f4bed5b | 50e11fd5 | 0.06/0.02 | 0.10/0.03 | 0.12/0.03 | 0.07 | 0.29 | 0.40 | 10.00 | 0.08 |
| 2026-09-21 19:42Z | v1 | 92f09c8e | 50e11fd5 | 0.06/0.02 | 0.10/0.03 | 0.12/0.03 | 0.07 | 0.29 | 0.40 | 10.00 | 0.08 |
| 2026-09-21 19:44Z | v1 | 54756075 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 |
| 2026-09-21 19:47Z | v1 | df15a53d | 50e11fd5 | 0.05/0.02 | 0.09/0.04 | 0.15/0.03 | 0.06 | 0.28 | 0.41 | 11.00 | 0.11 |
| 2026-09-21 19:49Z | v1 | f9ae8fad | 50e11fd5 | 0.05/0.02 | 0.10/0.04 | 0.15/0.03 | 0.06 | 0.28 | 0.42 | 11.00 | 0.10 |
| 2026-09-21 19:58Z | v1 | a01bf298 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 |
| 2026-09-21 19:59Z | v1 | a3feb448 | 50e11fd5 | 0.05/0.02 | 0.12/0.04 | 0.10/0.02 | 0.06 | 0.31 | 0.41 | 11.00 | 0.10 |
| 2026-09-21 20:01Z | v1 | dd9ead35 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 |
| 2026-09-21 20:02Z | v1 | 38b2289d | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 |
| 2026-09-21 20:03Z | v1 | 0cf85d73 | 50e11fd5 | 0.05/0.02 | 0.12/0.04 | 0.12/0.03 | 0.06 | 0.31 | 0.42 | 11.00 | 0.10 |
| 2026-09-21 20:10Z | v1 | 03917fd5 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 |
| 2026-09-21 20:11Z | v1 | 03dbe495 | 50e11fd5 | 0.08/0.02 | 0.10/0.03 | 0.10/0.02 | 0.10 | 0.31 | 0.40 | 12.00 | 0.11 | — | — |
| 2026-09-21 20:15Z | v1 | 97cc437f | 50e11fd5 | 0.15/0.02 | 0.19/0.03 | 0.12/0.02 | 0.16 | 0.32 | 0.41 | 15.00 | 0.14 | BUILD | reverted-d18-DO-NOT-USE |
| 2026-09-21 20:16Z | v1 | 71f34b84 | 50e11fd5 | 0.08/0.02 | 0.10/0.03 | 0.10/0.02 | 0.10 | 0.31 | 0.40 | 12.00 | 0.11 | — | — |
| 2026-09-21 20:17Z | v1 | 916f7887 | 50e11fd5 | 0.08/0.02 | 0.10/0.03 | 0.08/0.01 | 0.10 | 0.31 | 0.41 | 12.00 | 0.11 | — | — |
| 2026-09-21 20:21Z | v1 | b4913da0 | 50e11fd5 | 0.08/0.02 | 0.10/0.03 | 0.10/0.02 | 0.10 | 0.31 | 0.40 | 12.00 | 0.11 | — | — |
| 2026-09-21 20:24Z | v1 | 42084398 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.02 | 0.08 | 0.30 | 0.39 | 11.00 | 0.09 | — | — |
| 2026-09-21 20:25Z | v1 | 4aaa6a7a | 50e11fd5 | 0.08/0.02 | 0.10/0.03 | 0.10/0.02 | 0.10 | 0.31 | 0.40 | 12.00 | 0.11 | — | — |
| 2026-09-21 20:26Z | v1 | 996e5630 | 50e11fd5 | 0.08/0.02 | 0.10/0.03 | 0.10/0.02 | 0.10 | 0.31 | 0.40 | 12.00 | 0.11 | — | — |
| 2026-09-21 20:31Z | v1 | c188ae66 | 50e11fd5 | 0.08/0.02 | 0.10/0.03 | 0.08/0.02 | 0.10 | 0.31 | 0.40 | 12.00 | 0.11 | — | — |
| 2026-09-21 20:39Z | v1 | 9044ab77 | 50e11fd5 | 0.08/0.02 | 0.10/0.03 | 0.10/0.02 | 0.10 | 0.30 | 0.39 | 12.00 | 0.10 | — | — |
| 2026-09-21 20:44Z | v1 | 0090488f | 50e11fd5 | 0.05/0.01 | 0.08/0.03 | 0.10/0.03 | 0.05 | 0.31 | 0.42 | 7.00 | 0.06 | — | — |
| 2026-09-21 20:47Z | v1 | 28de3f03 | 50e11fd5 | 0.06/0.02 | 0.11/0.03 | 0.08/0.02 | 0.07 | 0.31 | 0.42 | 11.00 | 0.10 | — | — |
| 2026-09-21 20:52Z | v1 | 05ad54cf | 50e11fd5 | 0.09/0.03 | 0.09/0.03 | 0.08/0.02 | 0.11 | 0.31 | 0.39 | 10.00 | 0.11 | — | — |
| 2026-09-21 20:59Z | v1 | 584c7743 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | build | marker_off |
| 2026-09-21 21:03Z | v1 | a7b09b74 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | build | tail_off |
| 2026-09-21 21:04Z | v1 | a7b09b74 | 50e11fd5 | 0.06/0.02 | 0.10/0.03 | 0.12/0.03 | 0.07 | 0.29 | 0.40 | 11.00 | 0.10 | levellab | flag_off |
| 2026-09-21 21:04Z | v1 | 1c24be53 | 50e11fd5 | 0.06/0.02 | 0.10/0.03 | 0.12/0.03 | 0.07 | 0.29 | 0.40 | 11.00 | 0.10 | build | tail_on |
| 2026-09-21 21:05Z | v1 | 1c24be53 | 50e11fd5 | 0.03/0.02 | 0.10/0.03 | 0.23/0.04 | 0.06 | 0.30 | 0.39 | 11.00 | 0.10 | levellab | flag_on |
| 2026-09-21 21:07Z | v1 | 1c24be53 | 50e11fd5 | 0.06/0.02 | 0.10/0.03 | 0.12/0.03 | 0.07 | 0.29 | 0.40 | 10.00 | 0.09 | levellab | flag_off |
| 2026-09-21 21:09Z | v1 | a606f9b1 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | build | marker_off |
| 2026-09-21 21:10Z | v1 | e9fd5283 | 50e11fd5 | 0.06/0.03 | 0.09/0.03 | 0.12/0.03 | 0.08 | 0.30 | 0.39 | 9.00 | 0.10 | build | marker_on |
| 2026-09-21 21:18Z | v1 | 20ac1e24 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | build | marker_anchor |
| 2026-09-21 21:23Z | v1 | d8641b38 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | build | stable |
| 2026-09-21 21:29Z | v1 | a9d6af1c | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | levellab | flag_off |
| 2026-09-21 21:29Z | v1 | a9d6af1c | 50e11fd5 | 0.06/0.03 | 0.09/0.03 | 0.15/0.03 | 0.08 | 0.30 | 0.40 | 11.00 | 0.10 | levellab | v2 |
| 2026-09-21 21:36Z | v1 | a62edc19 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | build | tail_off |
| 2026-09-21 21:36Z | v1 | a62edc19 | 50e11fd5 | 0.06/0.02 | 0.10/0.03 | 0.12/0.03 | 0.07 | 0.29 | 0.40 | 11.00 | 0.10 | build | tail_on |
| 2026-09-21 21:36Z | v1 | a62edc19 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | build | marker_off |
| 2026-09-21 21:36Z | v1 | a62edc19 | 50e11fd5 | 0.06/0.03 | 0.09/0.03 | 0.12/0.03 | 0.08 | 0.30 | 0.39 | 9.00 | 0.10 | build | marker_on |
| 2026-09-21 21:36Z | v1 | a62edc19 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | build | marker_anchor |
| 2026-09-21 21:39Z | v1 | a62edc19 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | levellab | flag_off |
| 2026-09-21 21:39Z | v1 | a62edc19 | 50e11fd5 | 0.05/0.02 | 0.10/0.03 | 0.12/0.02 | 0.06 | 0.30 | 0.40 | 11.00 | 0.10 | levellab | v2b |
| 2026-09-21 21:47Z | v1 | a62edc19 | 50e11fd5 | 0.04/0.02 | 0.10/0.03 | 0.21/0.04 | 0.06 | 0.31 | 0.40 | 11.00 | 0.10 | levellab | flag_on |
| 2026-09-21 21:49Z | v1 | a62edc19 | 50e11fd5 | 0.06/0.03 | 0.09/0.03 | 0.15/0.03 | 0.08 | 0.30 | 0.40 | 11.00 | 0.10 | levellab | v2 |
| 2026-09-21 22:09Z | v1 | 2795e5e0 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | build | famledger_off |
| 2026-09-21 22:09Z | v1 | 2795e5e0 | 50e11fd5 | 0.04/0.02 | 0.10/0.04 | 0.10/0.02 | 0.06 | 0.28 | 0.41 | 10.00 | 0.10 | build | famledger_on |
| 2026-09-21 22:10Z | v1 | 2795e5e0 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | levellab | flag_off |
| 2026-09-21 22:10Z | v1 | 2795e5e0 | 50e11fd5 | 0.04/0.02 | 0.10/0.04 | 0.10/0.02 | 0.06 | 0.28 | 0.41 | 10.00 | 0.10 | levellab | fam_ledger |
| 2026-09-21 22:10Z | v1 | 2795e5e0 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.21/0.04 | 0.08 | 0.29 | 0.40 | 10.00 | 0.11 | levellab | famledger_v2 |
| 2026-09-21 22:46Z | v1 | 9283b389 | 50e11fd5 | 0.05/0.02 | 0.10/0.04 | 0.27/0.03 | 0.07 | 0.29 | 0.40 | 11.00 | 0.12 | levellab | lcshare2 |
| 2026-09-21 22:47Z | v1 | 9283b389 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.12/0.03 | 0.07 | 0.29 | 0.41 | 10.00 | 0.10 | evalaudit | ab_base |
| 2026-09-21 22:47Z | v1 | 9283b389 | 50e11fd5 | 0.04/0.02 | 0.10/0.04 | 0.10/0.02 | 0.06 | 0.28 | 0.41 | 10.00 | 0.10 | evalaudit | ab_famledger |
| 2026-09-21 22:47Z | v1 | 9283b389 | 50e11fd5 | 0.06/0.02 | 0.10/0.04 | 0.21/0.04 | 0.08 | 0.29 | 0.40 | 10.00 | 0.11 | evalaudit | ab_famledgerV2 |
| 2026-09-21 22:47Z | v1 | 9283b389 | 50e11fd5 | 0.06/0.03 | 0.09/0.03 | 0.15/0.03 | 0.08 | 0.30 | 0.40 | 11.00 | 0.10 | evalaudit | ab_labV2B |

## reproducibility

```
python evalcheck/scoreboard.py v0   # one row
python evalcheck/scoreboard.py v1
python evalcheck/snapshot.py        # snapshot table
python evalcheck/funnel.py          # oracle ceilings
python evalcheck/gate_pack.py       # this file
```

hashes: eval_v2 `50e11fd5a2ab7974`, common `c6b3fa0d28713204`, eval.py `8d016922aecae265`, book_loader `b40c2cab5c2ffe7d`; engines v0 `63c771d64e18f619`, v1 `9283b3892c7fe8fc`, linelab `ceef7d3fc610e67c`
## one-screen status

- IN: gate metrics + CIs on frozen v1 `584c7743`; same-hash lever table (R24 §24.3) incl. famledger b/c verified per R29 and the d2 priced trade; plausibility (all-30 vs valid-28, INCONCLUSIVE); recall@k all-family + per-family (k=1/2/5, CIs, author budget line, BRACKET upper-bound footnote); lab numbers separated and labelled 'lab ranker'; cache-integrity status; scoreboard history; reproducibility hashes.
- OJP: **GO** (uniform tau + blue style, R30 §30.2 fixes verified p03/p04/p09).
- MISSING: none blocking. Known caveats: BRACKET figures are upper bounds (ruler has no price check, R30 §30.3); plausibility judge spec .68 < .70 (inconclusive, not an artefact of the 2 invalid negatives); famledger (c) is a direction, not an author-budget gain.

