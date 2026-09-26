# GATE_PACK — data for the 22/09 ~01:00Z gate decision

Generated: 2026-09-21 20:25Z.  Tables only; the Lead writes the recommendation.

Gates (spec §6): BOX recall >= 0.70, BOX precision >= 0.60, PATTERN_LINE recall >= 0.50, LEVEL_CARRIED recall >= 0.60, T/F agreement on matched boxes >= 0.60, clutter ratio median <= 1.5.

## v0 (`63c771d64e18f619`)

| metric | value | CI95 (panel bootstrap) | gate | gap |
|---|---|---|---|---|
| BOX recall | 0.21 (23/108) | 0.13..0.30 | >=0.70 | -0.49 |
| BOX precision | 0.02 (27/1113) | 0.02..0.03 | >=0.60 | -0.58 ; plaus-adj 0.71 |
| PATTERN_LINE recall | 0.11 (20/184) | 0.07..0.15 | >=0.50 | -0.39 |
| LEVEL_CARRIED recall | 0.15 (7/48) | 0.05..0.25 | >=0.60 | -0.45 |
| T/F agreement on matched boxes | 0.00 (0/4) | 0.00..0.00 | >=0.60 | -0.60 |
| clutter ratio (eng/gold per panel) | 9.00 | 8.33..10.00 | <=1.5 | +7.50 |

supporting: snapshot recall **0.22** (105/479); live clutter at tau median **16.00** (p10 9.00 / p90 21.50); oracle BOX **0.31** PATTERN_LINE **0.28**
trusted-subset (non-Tier-A) line recall: CONTEXT_LINE **0.22** (2/9); PATTERN_LINE **0.11** (15/141)

per-panel: golden objects/panel p10/p50/p90 = [1. 2. 4.]; engine objects/panel p10/p50/p90 = [18. 24. 29.]

## v1 (`4aaa6a7ac6fc1162`)

| metric | value | CI95 (panel bootstrap) | gate | gap |
|---|---|---|---|---|
| BOX recall | 0.08 (9/108) | 0.03..0.14 | >=0.70 | -0.62 |
| BOX precision | 0.02 (9/400) | 0.01..0.04 | >=0.60 | -0.58 ; plaus-adj 0.65 |
| PATTERN_LINE recall | 0.10 (19/184) | 0.06..0.15 | >=0.50 | -0.40 |
| LEVEL_CARRIED recall | 0.10 (5/48) | 0.02..0.20 | >=0.60 | -0.50 |
| T/F agreement on matched boxes | 0.00 (0/1) | 0.00..0.00 | >=0.60 | -0.60 |
| clutter ratio (eng/gold per panel) | 5.33 | 4.83..6.00 | <=1.5 | +3.83 |

supporting: snapshot recall **0.11** (52/479); live clutter at tau median **12.00** (p10 8.00 / p90 14.00); oracle BOX **0.31** PATTERN_LINE **0.40**
trusted-subset (non-Tier-A) line recall: CONTEXT_LINE **0.22** (2/9); PATTERN_LINE **0.12** (17/141)

per-panel: golden objects/panel p10/p50/p90 = [1. 2. 4.]; engine objects/panel p10/p50/p90 = [11. 14. 17.]

## linelab (`ceef7d3fc610e67c`)

| metric | value | CI95 (panel bootstrap) | gate | gap |
|---|---|---|---|---|
| BOX recall | 0.00 (0/108) | 0.00..0.00 | >=0.70 | -0.70 |
| BOX precision | 0.00 (0/0) | 0.00..0.00 | >=0.60 | -0.60 ; plaus-adj 0.00 |
| PATTERN_LINE recall | 0.14 (26/184) | 0.09..0.20 | >=0.50 | -0.36 |
| LEVEL_CARRIED recall | 0.00 (0/48) | 0.00..0.00 | >=0.60 | -0.60 |
| T/F agreement on matched boxes | — (no marks on matched boxes) | | >=0.60 | |
| clutter ratio (eng/gold per panel) | 2.00 | 1.75..2.33 | <=1.5 | +0.50 |

supporting: snapshot recall **0.06** (27/479); live clutter at tau median **4.00** (p10 2.00 / p90 6.00); oracle BOX **0.00** PATTERN_LINE **0.14**
trusted-subset (non-Tier-A) line recall: CONTEXT_LINE **0.22** (2/9); PATTERN_LINE **0.17** (24/141)

per-panel: golden objects/panel p10/p50/p90 = [1. 2. 4.]; engine objects/panel p10/p50/p90 = [3. 5. 7.]

## plausibility (W1/W1b)

W1b: judge sensitivity 0.90, specificity 0.67 — SPEC < 0.70 -> plausibility-adjusted numbers UNRELIABLE (wide CIs); plausible-FP shares are Rogan-Gladen corrected (details: PLAUSIBILITY.md)

## recall@k (R17 §17.3 author budget)

## v0 (`63c771d64e18f619`)
| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.04 (20/479) | 0.02..0.06 | 0.00 (0/4) | 0.06 (6/106) | 0.12 (10/85) | 0.00 (0/9) | 0.00 (0/6) | 0.07 (3/46) | 0.00 (0/30) | 0.01 (1/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.07 (34/479) | 0.05..0.10 | 0.00 (0/4) | 0.10 (11/106) | 0.19 (16/85) | 0.11 (1/9) | 0.00 (0/6) | 0.07 (3/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.09 (44/479) | 0.07..0.12 | 0.00 (0/4) | 0.11 (12/106) | 0.24 (20/85) | 0.11 (1/9) | 0.17 (1/6) | 0.07 (3/46) | 0.00 (0/30) | 0.04 (7/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.14 (68/479) | 0.11..0.17 | 0.00 (0/4) | 0.13 (14/106) | 0.39 (33/85) | 0.22 (2/9) | 0.17 (1/6) | 0.09 (4/46) | 0.00 (0/30) | 0.08 (14/184) | 0.00 (0/7) | 0.00 (0/2) |
median live objects at tau: 16.0; tau-rows: 456
## v1 (`a01bf298feda2603`)
| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 (4/479) | 0.00..0.02 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.02 (3/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.01 (7/479) | 0.00..0.03 | 0.00 (0/4) | 0.01 (1/106) | 0.00 (0/85) | 0.00 (0/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.03 (5/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.03 (15/479) | 0.02..0.05 | 0.00 (0/4) | 0.02 (2/106) | 0.01 (1/85) | 0.11 (1/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.05 (10/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.07 (34/479) | 0.05..0.09 | 0.00 (0/4) | 0.02 (2/106) | 0.14 (12/85) | 0.22 (2/9) | 0.00 (0/6) | 0.02 (1/46) | 0.00 (0/30) | 0.09 (16/184) | 0.14 (1/7) | 0.00 (0/2) |
median live objects at tau: 10.0; tau-rows: 456
## linelab (`ceef7d3fc610e67c`)
| k | snapshot recall | CI95 | BAR_MARKER | BOX | BRACKET | CONTEXT_LINE | CONTEXT_RANGE | LEVEL_CARRIED | MINI_LEVEL | PATTERN_LINE | RANGE_OPEN | SQUEEZE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.05 (22/479) | 0.03..0.06 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.11 (1/9) | 0.00 (0/6) | 0.00 (0/46) | 0.00 (0/30) | 0.11 (21/184) | 0.00 (0/7) | 0.00 (0/2) |
| 2 | 0.05 (24/479) | 0.03..0.07 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.22 (2/9) | 0.00 (0/6) | 0.00 (0/46) | 0.00 (0/30) | 0.12 (22/184) | 0.00 (0/7) | 0.00 (0/2) |
| 3 | 0.06 (27/479) | 0.04..0.08 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.22 (2/9) | 0.00 (0/6) | 0.00 (0/46) | 0.00 (0/30) | 0.14 (25/184) | 0.00 (0/7) | 0.00 (0/2) |
| 5 | 0.06 (27/479) | 0.04..0.08 | 0.00 (0/4) | 0.00 (0/106) | 0.00 (0/85) | 0.22 (2/9) | 0.00 (0/6) | 0.00 (0/46) | 0.00 (0/30) | 0.14 (25/184) | 0.00 (0/7) | 0.00 (0/2) |
median live objects at tau: 4.0; tau-rows: 456

## LEVEL-LAB V8 recall@k (lab, TUNE, CV)

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
source: levellab/ROUND_L7.md

## definitions & reconciliation (R15 §15.4)

- **Clutter gate** = median of engine_objects/golden_objects per panel (the row 'clutter ratio'); the live-objects-at-tau median is a separate diagnostic, not the gate.
- **T/F agreement** is computed only on golden marks that sit inside a MATCHED golden box's span (n shown in the row).
- **Oracle (SCOREBOARD vs FUNNEL):** same `cand_right` rule, different aggregation. Scoreboard credits a golden when ANY same-family candidate is a right proposal (a candidate may credit several goldens); funnel assigns each candidate to its single best golden (best_cand_match). On ef06f265: PL oracle .397 (any) vs .375 (assigned) — a 4-golden gap. This pack reports the scoreboard (any) convention; funnel's is the stricter bound.
- **Born recall:** funnel fills missing golden t0/t1 with the panel window before matching (gold_with_keys mutates); scoreboard/gate_pack match the ruler on raw goldens. On ef06f265 LC born: 7/48 (.146) funnel vs 6/48 (.125) raw. This pack reports raw-golden recall.
- **Ruler caveat (W0 / R19 §19.1):** v1 BOX windows use proposal-time ends (`meta_build_end` = proposal bar); conversion to break-time ends (`break_bar`) would move BOX recall by about +0.02 GROSS (net not yet measured — extending a window past golden build_end can also LOSE matches). Ruler frozen; not adopted before the morning.

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

## reproducibility

```
python evalcheck/scoreboard.py v0   # one row
python evalcheck/scoreboard.py v1
python evalcheck/snapshot.py        # snapshot table
python evalcheck/funnel.py          # oracle ceilings
python evalcheck/gate_pack.py       # this file
```

hashes: eval_v2 `50e11fd5a2ab7974`, common `c6b3fa0d28713204`, eval.py `8d016922aecae265`, book_loader `b40c2cab5c2ffe7d`; engines v0 `63c771d64e18f619`, v1 `996e56304290877b`, linelab `ceef7d3fc610e67c`
