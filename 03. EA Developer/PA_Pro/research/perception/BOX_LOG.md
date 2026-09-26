
### 04:48Z C1 selection anatomy (R38 §38.3.1) — wd arm, 42 oracle-covered box goldens

Coverable (a matching box live at tau): 2/42 — both hit@1. Uncoverable: 40.
Right-cand fate: rate_limited 26, born 3, only-proposed 10, nms 3.
Of rate-killed rows with a logged score, the right cand OUTSCORED the
tau top-1 box in ~24/33 — it arrives later and the rate window
(rate_box=1/72b, joint 5/72b) is already spent. ttl 24 < window 72:
a blocked cand expires before its first retry (rate_blocked_extend=OFF).

| panel | tau | fate | coverable | top box (route, score) | right-cand score | verdict |
|---|---|---|---|---|---|---|
| 9.13a | 505 | rate | no | cluster_range 8.03 | 8.96 | right outscores, blocked |
| 9.15b | 895 | rate | no | congestion_scan 5.20 | 25.78 | right outscores 5x, blocked |
| 9.15b | 900 | prop | no | congestion_scan 5.20 | - | never scored |
| 9.16c | 1070 | rate | no | cluster_range 12.98 | 9.83 | right weaker, blocked |
| 9.17a | 475 | rate | no | cluster_range 20.79 | 12.92 | right weaker, blocked |
| 9.17b | 705 | rate | no | cluster_range 6.22 | 15.67 | right outscores, blocked |
| 9.17b | 775 | rate | no | cluster_range 6.22 | 7.51 | right outscores, blocked |
| 9.17c | 830 | prop | no | cluster_range 20.98 | - | never scored |
| 9.18a | 515 | rate | yes | congestion_scan 7.90 | 19.80 | hit@1 anyway |
| 9.19b | 840 | rate | no | congestion_scan 12.39 | 8.32 | right weaker, blocked |
| 9.20b | 605 | rate | no | cluster_range 12.91 | 12.20 | parity, blocked |
| 9.23c | 985 | rate | no | congestion_scan 9.07 | 14.94 | right outscores, blocked |
| 9.25b | 775 | born | no | cluster_range 12.96 | 20.98 | right born but wrong-window twin lives |
| 9.2b | 765 | rate | no | cluster_range 5.32 | 11.20 | right outscores, blocked |
| 9.2b | 835 | rate | no | cluster_range 5.32 | 26.92 | right outscores 5x, blocked |
| 9.30c | 880 | rate | no | cluster_range 15.67 | 18.89 | right outscores, blocked |
| 9.32a | 510 | rate | no | cluster_range 3.57 | 7.10 | right outscores, blocked |
| 9.32b | 735 | rate | no | cluster_range 3.38 | 14.12 | right outscores 4x, blocked |
| 9.33c | 1055 | rate | no | cluster_range 4.43 | 12.15 | right outscores, blocked |
| 9.34a | 495 | rate | no | cluster_range 4.31 | 8.67 | right outscores, blocked |
| 9.35a | 260 | rate | no | structural 4.11 | 10.91 | right outscores, blocked |
| 9.36b | 560 | rate | no | cluster_range 8.44 | 12.06 | right outscores, blocked |
| 9.3b | 745 | rate | no | structural 3.68 | 7.79 | right outscores, blocked |
| 9.40c | 960 | born | yes | cluster_range 11.02 | 11.08 | hit@1 |
| 9.41b | 835 | rate | no | cluster_range 16.61 | 35.15 | right outscores 2x, blocked |
| 9.43b | 840 | rate | no | cluster_range 9.22 | 8.01 | parity, blocked |
| 9.43c | 870 | prop | no | cluster_range 9.08 | - | never scored |
| 9.44b | 685 | prop | no | cluster_range 19.43 | - | never scored |
| 9.45b | 740 | rate | no | cluster_range 7.49 | 16.02 | right outscores 2x, blocked |
| 9.48a | 420 | prop | no | cluster_range 6.02 | - | never scored |
| 9.48b | 705 | rate | no | cluster_range 6.08 | 7.84 | right outscores, blocked |
| 9.4b | 815 | born | no | cluster_range 15.09 | 39.36 | right born earlier? still uncoverable at tau |
| 9.4b | 855 | rate | no | cluster_range 4.51 | 7.49 | right outscores, blocked |
| 9.50a | 590 | prop | no | cluster_range 12.21 | - | never scored |
| 9.51a | 300 | prop | no | structural 4.03 | - | never scored |
| 9.53b | 840 | nms | no | cluster_range 30.55 | 26.74 | right weaker, suppressed |
| 9.56c | 840 | rate | no | cluster_range 3.73 | 10.93 | right outscores, blocked |
| 9.57c | 980 | rate | no | cluster_range 4.32 | 5.84 | right outscores, blocked |
| 9.58a | 545 | rate | no | cluster_range 5.74 | 8.27 | right outscores, blocked |
| 9.59c | 1035 | prop | no | cluster_range 3.53 | - | never scored |
| 9.7b | 540 | prop | no | cluster_range 8.36 | - | never scored |
| 9.8c | 805 | prop | no | congestion_scan 7.92 | - | never scored |

Reading: box@1 is not lost at ranking — the right object is never
alive at tau (40/42). It is lost at the birth-rate gate: first-come
first-served windows let an early weaker box spend the slot before
the right band qualifies (right cands usually arrive later and score
higher). rate_blocked_extend is the existing lever; A/B in flight.

### 05:29Z C1 v0-table (R39 §39.4 / R40 §40.4.3) — the 15-16 v0 box@1 hits vs v1 live at the same tau

v0 box@1 hits located: 15 of 16 (one golden lacks a v0 tau pickle).
v1 (parent lvltr_off@22888182) has a matching box live at those tau:
2/15 — and both are just v1's own 3 hits overlapping.

| panel | tau | golden edges | v0 top box (route) | v0 edges | v1 top (route) | v1 edges | v1 sco | v1 match rank |
|---|---|---|---|---|---|---|---|---|
| 9.2b | 765 | 13239-13261 | range_double_bottom | 13240-13264 | structural | 13311-13332 | 6.6 | none |
| 9.2b | 835 | 13212-13225 | pullback_end | 13212-13222 | structural | 13311-13332 | 6.6 | none |
| 9.4b | 815 | 13131-13150 | pullback_end | 13131-13149 | cluster_range | 13131-13149 | 6.0 | none |
| 9.6a | 600 | 13167-13185 | range_double_top | 13165-13184 | structural | 13135-13151 | 5.0 | none |
| 9.16c | 1070 | 13188-13202 | pullback_end | 13185-13202 | cluster_range | 13134-13167 | 2.2 | none |
| 9.17b | 705 | 13244-13251 | pullback_end | 13243-13252 | structural | 13191-13212 | 8.3 | none |
| 9.17c | 830 | 13222-13252 | pullback_end | 13222-13251 | (no box live) | - | - | none |
| 9.25b | 775 | 13161-13175 | pullback_end | 13161-13174 | structural | 13217-13233 | 7.9 | none |
| 9.33c | 1055 | 13061-13076 | pullback_end | 13060-13075 | cluster_range | 13028-13039 | 1.0 | none |
| 9.36b | 560 | 13109-13127 | range_double_top | 13107-13127 | structural | 13111-13126 | 7.7 | 1 |
| 9.39a | 475 | 13146-13157 | pullback_end | 13146-13156 | structural | 13146-13156 | 5.6 | 1 |
| 9.40c | 960 | 13214-13226 | range_double_top | 13212-13225 | structural | 13193-13206 | 7.4 | none |
| 9.41b | 835 | 13203-13219 | pullback_end | 13200-13216 | structural | 13218-13233 | 9.9 | none |
| 9.43b | 840 | 13212-13232 | pullback_end | 13208-13235 | structural | 13237-13245 | 3.3 | none |
| 9.44b | 730 | 13243-13254 | range_double_top | 13243-13255 | structural | 13236-13243 | 9.3 | none |

Reading: v0's box@1 advantage is ROUTE-TIMING, not ranking. Its box
births fire on pattern-completion events (pullback_end,
range_double_top/bottom) — the author's draw moment — at the
confirmed geometry. v1 births on band qualification
(cluster_range/structural) early and often on a neighbouring band;
the right band then dies rate_limited behind the spent window. In
13/15 v0-hit cases v1 has NO matching box live at tau at all — the
gap is upstream of ranking. (script: boxlab/c1_v0table.py)

### 05:32Z C1 unwinnable set (R40 §40.4.4) — for the ruler-v3 list

Mechanism: funnel.cand_as_record clamps cand t0 to the scored window
(r["t0"] = max(t0m, w0)); cand_right for BOX requires
|t0 - (build_start|t0)| <= 2*TIME_SIGMA_MIN = 20 min. Any golden
whose build_start precedes w0 by >20 min can NEVER be matched — no
proposal can carry a legal t0. Generation cannot fix this; it is a
ruler/funnel boundary.

| panel | golden t0 | w0 | gap | edges |
|---|---|---|---|---|
| 9.1c | 695 | 720 | 25 | 13317.0-13332.0 |
| 9.8b | 450 | 480 | 30 | 13092.0-13114.0 |
| 9.14b | 435 | 480 | 45 | 13228.4-13240.9 |
| 9.16c | 670 | 720 | 50 | 13145.1-13199.8 |
| 9.20a | 140 | 180 | 40 | 13319.0-13338.0 |
| 9.34a | 215 | 240 | 25 | 13107.0-13129.0 |
| 9.34b | 450 | 480 | 30 | 13089.9-13145.9 |
| 9.39a | 70 | 120 | 50 | 13146.0-13157.0 |
| 9.42b | 395 | 420 | 25 | 13157.2-13204.6 |

9 of 108 scorable box goldens (~8 pct). The author build_start is the
buildup's true left edge, often before the panel's scored window.
Ruler-v3 options (for the Lead, not this round): judge the cand's
UNclamped t0_raw against gbs; or treat pre-window starts as legal
with the window IoU doing the containment work.

### 05:42Z C1 residual miss taxonomy under wd (oracle .407 -> 64 uncovered)

Same-cand clause analysis (cand_right needs edges + t0±20 +
t_birth<=gbe+10 on ONE cand row):
- t0 only, edges never proposed:        22
- edges proposed, t0 never right:       22
- neither edges nor t0:                 19
- right edges+t0 but proposed late:      3
- (of these, 5 also carry the pre-w0 t0 clamp — unwinnable)

All three non-covered classes are GENERATION-side: no existing flag
reaches them because _variants only fires on a band that already
qualified.  The 22 wrong-t0 class wants an edge-walk anchor (emit the
same edges re-anchored at pivot t0s near golden bs — dense_anchors did
this but on the parent band's edges, not the golden's).  The 39
edges-missing classes want a new edge source entirely (author edges
often sit mid-band on eye-level structure, not on defended extremes —
matches the lab's residual classes).

Box-side levers exhausted this round; next real lever is the build
lane's box_score_pick supersede (est. +10-16 box@1 hits, c1_supersede
.py bracket) then a ranker on the engine live set (§40.4.5).
