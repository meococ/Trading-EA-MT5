# LEVEL FUNNEL (V3)

Source: `evalcheck/labels_v1_ef06f265ab84889f.jsonl` (the L6 funnel run,
ruler 50e11fd5) — per-candidate outcome labels on the production stream.
Rebuilt per-golden taxonomy with per-type key counters (same key scheme as
`funnel.gold_with_keys`).

## Golden-side miss taxonomy

| type | golden | matched (born) | proposed_not_born | proposed_wrong_geometry | never_proposed |
|---|---|---|---|---|---|
| LEVEL_CARRIED | 48 | 7 (0.15) | 17 (0.35) | 24 (0.50) | 0 |
| MINI_LEVEL | 31 | 2 (0.06) | 3 (0.10) | 26 (0.84) | 0 |

Oracle ceiling (any right proposal): LEVEL_CARRIED 24/48 = 0.50,
MINI_LEVEL 5/31 = 0.16 — matches FUNNEL.md.

## Right-proposal outcomes (label != null, 112 level proposals)

| outcome | n | share |
|---|---|---|
| born | 6 | 5% |
| rate_limited | 57 | 51% |
| expired | 38 | 34% |
| outranked | 11 | 10% |

Per-golden view (LEVEL_CARRIED, the 17 proposed_not_born goldens):
`rate_limited` appears in 16/17, `expired` in 5, `outranked` in 2 —
usually stacked (the same golden was re-proposed and killed several times).

## Who spends the slots

Born candidates within ±45 min of a killed right level proposal
(57 rate_limited right proposals):

| spender family:route | n |
|---|---|
| PATTERN_LINE / hull_max_touch | 30 |
| BAR_MARKER / star_extreme | 24 |
| BOX / cluster_range | 17 |
| CONTEXT_LINE / hull_max_touch | 16 |
| LEVEL_CARRIED / broken_line_edge | 15 |
| BRACKET / letter_* | 14 |
| BOX / congestion_scan | 2 |
| LEVEL_CARRIED / other routes | 7 |

Slots are spent mostly by **lines, bar markers and boxes** — the level
family does not crowd itself out. Some killed proposals had no born
neighbour inside ±45 min → the rate window/budget was already exhausted
before they arrived.

## Selection on the production stream (§15.3 test)

`levellab/select_levels.py`, 198 panels, engine ef06f265, funnel
prefix-consistent labels, day-level 5-fold AUC:

- LEVEL_CARRIED: 1361 cands, 24 right (1.8%). Best feats: `score` 0.58,
  `prom_abr` 0.59, `touches` 0.56 — **none ≥0.60 on every fold**
  (fold ranges e.g. touches 0.40–0.80, score 0.42–0.81).
- MINI_LEVEL: 1823 cands, 39 right (2.1%). All feats ≈0.5;
  `age_min`/`span_min` 0.58 overall, folds 0.12–0.78.

Same result as LINE-LAB L8: on the production stream, **no candidate
feature separates right from wrong** at the §15.3 bar. The proposals the
engine generates are too loosely tethered to golden geometry — the miss
is upstream (wrong_geometry 50%), not in scoring.

## Verdict

Salience binding is real (71% of right LEVEL_CARRIED proposals die
unborn) but is the *second* wall: half the goldens never get a
right-geometry proposal at all. Priority order for V4:

1. fix proposal geometry (origin classes from V2 — old defended pivots);
2. then salience. A cap raise alone would lift ink, not recall:
   1361 wrong vs 24 right candidates is a 57:1 noise floor.
