# FUNNEL — proposal-to-birth funnel, TUNE v2, 198 panels

## Candidate -> engine-record conversion

A cand_log entry has no drawn span; it is converted at its proposal-time window:
- `span = [t_left or t0, t1 or idx]` bar indices -> minutes, then clipped to [w0, w1] (same as `eval_v2.eng_objects`);
- the containment window = the same span (`bs..be`): a candidate IS the buildup observed so far;
- edges `lo/hi` (v0) or `bottom/top` (v1), already pip-scale;
- lines: `p0, slope, t0_bar = t0` — evaluated at minutes via `searchsorted(m)`, same as born lines;
- levels: `price, side`; brackets: `t0, t1, letter`;
- `LABEL_TF` -> mark record with `t_birth = cet_min`;
- `BAR_MARKER` -> point span `t0..t1`.

Matching: born objects use `eval_v2.match_detail`/`match_mark` (the R11 ruler).  Candidates are judged by the R11 §11.2 prefix-consistent rule (`cand_right`): BOX = both edges within tol + start within 20 min of build_start + i <= build_end + 10 min; line = two-point check on the shared span + i <= t1; level = price within tol + i inside the golden span.  Born-object labels use the panel's greedy assignment; candidate labels are pairwise best-match under that rule.  Miss taxonomy precedence: matched > proposed_not_born (refusal reason kept) > born_diff_episode > born_closed_early > proposed_wrong_geometry > born_wrong_geometry > never_proposed.

## engine v1 (`9283b3892c7fe8fc`)

| type | golden | oracle ceiling | born recall | gap |
|---|---|---|---|---|
| BAR_MARKER | 4 | 0.50 (2) | 0.50 (2) | 0.00 |
| BOX | 108 | 0.29 (31) | 0.06 (6) | 0.23 |
| BRACKET | 85 | 0.61 (52) | 0.29 (25) | 0.32 |
| CONTEXT_LINE | 9 | 0.78 (7) | 0.22 (2) | 0.56 |
| CONTEXT_RANGE | 6 | 0.17 (1) | 0.17 (1) | 0.00 |
| LABEL_TF | 60 | 0.42 (25) | 0.08 (5) | 0.33 |
| LEVEL_CARRIED | 48 | 0.50 (24) | 0.15 (7) | 0.35 |
| MINI_LEVEL | 31 | 0.16 (5) | 0.06 (2) | 0.10 |
| PATTERN_LINE | 184 | 0.39 (71) | 0.10 (19) | 0.28 |
| RANGE_OPEN | 8 | 0.38 (3) | 0.25 (2) | 0.12 |
| SQUEEZE | 2 | 0.00 (0) | 0.00 (0) | 0.00 |

Miss taxonomy (golden objects): proposed_wrong_geometry=302, proposed_not_born=153, matched=71, born_unassigned=12, never_proposed=5, born_diff_episode=2

BOX pairs passing edge test: nested=10, disjoint=5

### nested examples
- `9.2b` 9.2b/BOX#2 golden W=[780, 835] engine W=[780, 840] IoU=0.92 ovcoef=1.00
- `9.4b` 9.4b/BOX#1 golden W=[675, 815] engine W=[675, 720] IoU=0.32 ovcoef=1.00
- `9.18a` 9.18a/BOX#1 golden W=[370, 515] engine W=[415, 480] IoU=0.45 ovcoef=1.00
- `9.20c` 9.20c/CONTEXT_RANGE#1 golden W=[985, 1110] engine W=[25, 1080] IoU=0.09 ovcoef=0.76
- `9.25b` 9.25b/BOX#1 golden W=[645, 775] engine W=[650, 695] IoU=0.35 ovcoef=1.00

### partial examples

### disjoint examples
- `9.2a` 9.2a/BOX#1 golden W=[240, 250] engine W=[305, 410] IoU=0.00 ovcoef=0.00
- `9.6a` 9.6a/BOX#2 golden W=[565, 610] engine W=[385, 440] IoU=0.00 ovcoef=0.00
- `9.14a` 9.14a/RANGE_OPEN#1 golden W=[520, 540] engine W=[20, 455] IoU=0.00 ovcoef=0.00
- `9.14a` 9.14a/RANGE_OPEN#1 golden W=[520, 540] engine W=[45, 95] IoU=0.00 ovcoef=0.00
- `9.14a` 9.14a/RANGE_OPEN#1 golden W=[520, 540] engine W=[340, 400] IoU=0.00 ovcoef=0.00
