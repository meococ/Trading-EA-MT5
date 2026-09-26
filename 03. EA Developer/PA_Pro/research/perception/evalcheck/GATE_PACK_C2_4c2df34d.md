# GATE_PACK_C2 — C-round-2 close pack (EVAL-AUDIT)

Generated 2026-09-22 15:15Z by EVAL-AUDIT's own scorer (m1_row.py), TUNE 198 panels, ruler `50e11fd5a2ab7974`.

STABLE C-2: `4c2df34d7a2a8ee3` = C1 `9acaa206` + K7 + K8 + K9 + F1. F1 is behaviour-neutral (TUNE 1728/1728 byte-identical, verified), so the measured row below is the K9 state — `c1r_p_base@ee2cbf12`, byte-identical to the merged engine's canonical output.

## M1 — per-family recall at the author's budget

| arm | box@1 | level@1 | line@2 | bracket@1 † |
|---|---|---|---|---|
| v0 `63c771d6` | 0.134 (16/119) | 0.066 (5/76) | 0.093 (18/193) | 0.388 (33/85) |
| STABLE C-2 | 0.084 (10/119) -0.064 [-0.137..-0.001] | 0.105 (8/76) +0.072 [-0.011..+0.167] | 0.104 (20/193) +0.015 [-0.040..+0.070] | 0.341 (29/85) -0.015 [-0.172..+0.134] |

† bracket@1 reported, not part of M1 (no price check, R30 §30.3). CIs are paired day-bootstrap of (arm − v0), seed 20260921, 1000 resamples.

## Clutter + diagnostics (STABLE C-2)

- clutter ratio median (eng/gold per panel): **4.33** (v0 9.00); 114/179 scored panels <= 5.0
- BOX recall 0.102 | BOX precision 0.036 | PATTERN_LINE recall 0.114 | LEVEL_CARRIED recall 0.208 | LABEL_TF agreement 0/1 | clutter ratio med 4.33

## Keep verdicts (C-2, EVAL-AUDIT independent, own scorer)

- K7 marker.off @66f596dc (ctxy_off vs bmoff_on): CONFIRMED, ink-only rule. M1 level 6->7 (+1), box/line/bracket flat; clutter 5.00->4.67; margin 90->103 (+13>=+5); OFF-id vs m1_v1@9acaa206 1728/1728 obj+cand_log+events; suite 65/72 named-seven. Flipped golden: +1 miss->hit = 9.64c MINI_LEVEL t1010-1025 @1.25277; zero hit->miss.
- K8 box.cong_pivedge @81f7503f (pedg_off vs pedg_on; defaults be4eea26): CONFIRMED, generation rule. box 9->10 (+1), level 7->8 (+1), line/bracket flat; clutter 4.67=; margin 103->101 (-2 allowed under generation rule); OFF-id vs both parent references 1728/1728; suite 65/72 named-seven. Flipped goldens: +2 miss->hit = 9.2b BOX t580-810 @1.3261, 9.49a LEVEL_CARRIED t591-630 @1.3027; zero hit->miss.
- K9 salience.rate_label_tf=2/day @759d9036 (ltfcap_off vs ltfcap_on; defaults ee2cbf12): CONFIRMED, ink-only rule. M1 all flat; clutter 4.67->4.33; margin 101->114 (+13>=+5); OFF-id 1728/1728; suite 65/72 named-seven. Zero flipped goldens (pure ink reduction).
- F1 perf patch (engine.py+swings.py): CONFIRMED behaviour-neutral — TUNE 1728/1728 canonical identity incl. cand_log+events, 35-day DESIGN continuous identical, suite 65/72 same-seven; crossover ~day 20 (patched faster on long runs: d24 189v131, d27 188v141, d33 179v140 bars/s). Merged as STABLE C-2 4c2df34d — on-disk hash recomputes exact, engine.py+swings.py == _scratch/perf/v2, 5-panel spot check byte-identical to K9 cache.

## Tested and rejected this round (EVAL-AUDIT own scorer)

| arm | hash | box@1 | level@1 | line@2 | clutter | margin | why |
|---|---|---|---|---|---|---|---|
| bmday marker.day_extreme_only | 66f596dc | .076 = | .079 = | .104 = | 5.00 | 94 (+4) | margin +4 < +5 (ink-only needs +5) |
| ctcv loose (ctx_convert overlap) | 084caa52 | .101 +2 | .053 -4 | .088 -3 | 5.00 | - | level -4 > -1; suite 72/72 cannot rescue |
| ctcv wraps (contains+<=2xw) | 3ca9097b | .092 +1 | .092 -1 | .093 -2 | 5.00 | - | level -1 edge + line -2; suite 72/72 |
| lnsf42 line.slope_floor .25->.42 | ee2cbf12 | .084 = | .092 -1 | .083 -4 | 4.00 | 120 (+6) | line -4 on target fam; margin cannot rescue |
| p_wick / wick_birth (BOX-LAB probe) | 81f7503f | flat | - | - | - | - | log_only bucket does not convert (orc .407, box@1 8/119, born/pan 1.52) — not pooled |
| CONTEXT_LINE-while-PL-live (sim) | - | - | -3 | - | +8 margin sim | - | skipped: -3 hits in simulation |
| LEVEL_CARRIED nearest-ahead (sim) | - | - | -3 | - | +3 margin sim | - | skipped: -3 hits in simulation |

## Fixture debt carried (spec-vs-author conflict)

- Suite 65/72 — the same seven named fixtures fail under fam_budget (CONTEXT_RANGE occupies the box-family live slot): pullback_end_box_birth, range_box_double_top, false_break_wick_keeps_edge, break_close_beyond_edge, tease_vs_proper_break_class, tf_relabel, reanchor_on_new_double_top. Documented in FIXTURE_CONFLICT.md; ctcv conversion-in-place cured all seven but cost level -4 (rejected). Decision is the Owner's.

## Box gap — why C-2 ends 6 hits short of v0

- BOX-LAB R1 census (119 box goldens): 10 hit, 16 below-min score, 11 outranked, 8 rate-limited, 2 expired, 10 log-only, 62 no coverage. The dominant class is no-coverage, then selection losses (score/outrank/rate).
- R1 hypothesis table (107 wrong-pick pairs, label-shuffle nulls, seeds 56+777 identical): KEEP H5 recency (+14.4, but uses post-tau author t1_drawn — needs a causal proxy), H4 prior-leg +0.59, H10 tall +1.19, H6 height-ratio +0.014; thin: H1 press, H3 probes; DROP: H2 flat-EMA (reversed), H7 overlap, H8 wick-tip, H9 round-50.
- Density-matched null review (_null_review_c2.py): pivot coverage .711 does NOT beat null p95 .763 on the 38 no-edge goldens; trigger-window close-extremes .368 vs p95 .528 (drop). The C1 pivot-source claim does not survive the stronger null.

## Status

C-round 2 closed STABLE `4c2df34d7a2a8ee3` at ~15:01Z. Ruling 56 withdrew the freeze: 'Owner: machine is wrong on boxes -> research a different approach'. C-3 is a box research round; this pack records the C-2 end state as the new research parent. All numbers above are independently measured; the suite's seven failures are a spec-vs-author conflict pending the Owner.
