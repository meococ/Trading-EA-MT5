# GATE_PACK_C1 — C-round-1 freeze pack (EVAL-AUDIT)

Generated 2026-09-22 07:39Z by EVAL-AUDIT's own scorer (m1_row.py), TUNE 198 panels, ruler `50e11fd5a2ab7974`.

Candidate: `75a9650ca6ae7f79` variant=`lnfloor_on` (K5 kept config (provisional - pending fam_context))

## M1 — per-family recall at the author's budget

| arm | box@1 | level@1 | line@2 | bracket@1 † |
|---|---|---|---|---|
| v0 `63c771d6` | 0.134 (16/119) | 0.066 (5/76) | 0.093 (18/193) | 0.388 (33/85) |
| candidate | 0.059 (7/119) -0.077 [-0.151..-0.015] | 0.079 (6/76) +0.039 [-0.033..+0.117] | 0.104 (20/193) +0.015 [-0.040..+0.070] | 0.341 (29/85) -0.015 [-0.172..+0.134] |

† bracket@1 reported, not part of M1 (no price check, R30 §30.3). CIs are paired day-bootstrap of (arm − v0), seed 20260921, 1000 resamples.

## Clutter + diagnostics (candidate)

- clutter ratio median (eng/gold per panel): **5.00** (v0 9.00); 90/179 scored panels ≤ 5.0
- BOX recall 0.093 | BOX precision 0.038 | PATTERN_LINE recall 0.114 | LEVEL_CARRIED recall 0.188 | LABEL_TF agreement 0/1 | clutter ratio med 5.00

## Keep verdicts (EVAL-AUDIT independent, own scorer)

- K1 line.lab_score @afba83c5: CONFIRMED (+2 line hits, OFF-id 1728/1728 vs STABLE parent)
- K2 defended_origin+def_mini_off @e62f2dc9: CONFIRMED (+2 level, −1/−1 allowed, OFF-id 1728/1728 cross-hash)
- K3 bxcombo @dd96c5fe: CONFIRMED (+1 box, +2 line, clutter 5.00, OFF-id 1728/1728 cross-hash)
- K4 box_score_pick arm A @cfb862d4: CONFIRMED (+4 box, OFF-id 1728/1728); arm B rejection CONFIRMED (−2 box)
- K5 line.slope_floor=0.25 @75a9650c: CONFIRMED (+1 line, clutter 5.00 thin margin 90/179, OFF-id 1728/1728)
- box_prio (§42.4, 4 forms): all FAIL keep-rule on own scorer — v1 cd14f5fc lvl −3 cl 6.33; v2 cd00d0be box +1 lvl −4 cl 6.00 (+OFF-id broken: 3 obj + 1107 cand_log diffs); v3 afe99034 box +2 lvl −2 cl 6.33; v4 box_tau_prio c14060cb box −3 cl 5.00. Suite on v2-ON config 72/72 (fixes the 7 fixtures) but M1 cost stands — correctly rejected.
- §42.5 choice rows (own scorer): kept .059/.079/.104 cl 5.00; famoff_on .067/.053/.067 cl 5.67 (line below v0); famoff_nosup .042/.053/.073 cl 5.00 — kept config is M1-best.
- Suite leg (R42 §42.3, unmodified fixtures, each keep's own config): K1 72/72, K2 72/72, K3 65/72, K4 65/72, K5 65/72 — the same 7 theory fixtures fail once fam_budget+fam_caps hold (CONTEXT_RANGE occupies the box-family slot); box_prio ON or fam flags OFF each restore 72/72.

## Status

_status block filled at freeze._
