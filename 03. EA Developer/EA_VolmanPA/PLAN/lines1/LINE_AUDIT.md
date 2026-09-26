# LINE_AUDIT — pro lines vs the burned boundaries (T-VPA-LINE-1)

Engine: `research/lines/vpa_lines.py` (causal, closed bars only). Score = 0.35*touch + 0.20*age + 0.25*visibility + 0.20*HTF-swing alignment; armed = score >= 0.50. On-chart = the pruned set (max 8 lines, max 2 per type, same-price merge 0.15*ATR). No outcomes anywhere (E4/F7).

## 1. The 16 Lead-A/B burned cases

`boundary` = the Lead's key level for the case (`PLAN/grading/KEY_HIDDEN.csv`), falling back to the DR3 barrier. `match` = best armed line within the DR3 tolerance (0.10*ATR) / within the pro line zone (0.35*ATR).

| case | grade | UTC | setup | side | boundary | nearest armed line | d(pips) | score | touches | age | integrity | eps-match | zone-match | on-chart |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| case_003 | A | 10:10 | pattern_break | short | 1.154745 | level | 0.05 | 0.685 | 4 | 9 | no | level | level | - |
| case_010 | B | 16:05 | pullback_reversal | short |  | - |  |  |  |  | - | - | - | - |
| case_012 | A | 16:40 | pattern_break | long | 1.139435 | sess_hi | 2.35 | 1.0 | 10 | 140 | no | - | sess_hi | sess_hi |
| case_020 | B | 12:40 | pattern_break | short | 1.1835 | sess_lo | 2.4 | 0.742 | 3 | 14 | yes | - | - | - |
| case_021 | B | 06:15 | pattern_break | short | 1.119615 | level | 0.05 | 0.79 | 4 | 13 | no | level | level | trendline |
| case_025 | A | 08:25 | pattern_break | long | 1.188715 | level | 0.15 | 0.762 | 4 | 15 | yes | level | level | flag_upper |
| case_065 | B | 08:05 | pattern_break | short | 1.172185 | level | 1.45 | 0.682 | 3 | 10 | no | - | level | box_bottom |
| case_067 | A | 05:25 | pattern_break | long | 1.04724 | box_top | 0.2 | 0.845 | 5 | 41 | yes | - | box_top | box_top |
| case_085 | B | 17:05 | pattern_break | short | 1.082815 | trendline | 3.9 | 0.706 | 3 | 12 | no | - | - | - |
| case_118 | B | 06:05 | pattern_break | long | 1.17937 | trendline | 0.02 | 0.887 | 8 | 42 | no | trendline | trendline | flag_upper |
| case_153 | B | 09:10 | pattern_break | long | 1.188395 | level | 1.05 | 0.776 | 8 | 18 | no | - | level | box_top |
| case_154 | B | 16:15 | pattern_break | long | 1.13057 | trendline | 0.84 | 0.833 | 5 | 16 | yes | - | trendline | trendline |
| case_160 | A | 17:25 | pattern_break | long | 1.177535 | flag_upper | 1.25 | 0.865 | 9 | 32 | yes | - | flag_upper | flag_upper |
| case_172 | B | 05:05 | pattern_break | short | 1.180655 | level | 0.05 | 0.574 | 3 | 5 | no | level | level | - |
| case_178 | B | 12:30 | pattern_break | short | 1.22326 | level | 0.2 | 0.768 | 14 | 39 | no | level | level | level |
| case_196 | B | 16:20 | pattern_break | long | 1.232865 | trendline | 1.17 | 1.0 | 19 | 221 | yes | - | trendline | trendline |

**Summary:** eps-match 6/16, zone-match 13/16, zone-match on chart 11/16. `case_010` is a pullback-reversal case: the DR1/DR3 key carries no barrier level for it, so it cannot be matched (1 of 16). `d(pips)` = distance from the boundary to the nearest armed line; `integrity` = that line was never closed through since it formed.

## 2. Armed lines per bar (DESIGN 2016-2021, every 100th bar)

| metric | raw armed (score >= 0.50) | on chart (pruned) |
|---|---|---|
| median | 21.0 | 8.0 |
| p90 | 25.0 | 8.0 |
| max | 36 | 8 |
| bars sampled | 4400 | 4400 |

Distance of an armed line from the close: median 2.85 ATR, p90 11.34 ATR (raw armed set). A line far from price is a level drawn in advance; the on-chart set keeps the nearest/best ones.

Pruning rule (chart hygiene): sort by score; keep at most 8 lines, at most 2 per type; drop a line that sits within 0.15*ATR of an already-kept line (two lines at the same price are one line). The raw count is the honest 'how many lines exist'; the on-chart count is what the trader sees.

## 3. DR3 micro-barriers vs significant lines

All barriers locked by the frozen DR3 barrier engine (`research/lab/vpa_core.py`, `barrier_expiry=20`) over DESIGN 2016-2021. A barrier coincides when an armed line (score >= 0.50) is within tolerance at the lock bar.

| tolerance | share | n coincident / n locks |
|---|---|---|
| 0.10*ATR (DR3's own eps) | 40.6% | 18366 / 45266 |
| 0.35*ATR (pro line zone) | 80.9% | 36609 / 45266 |
| 0.35*ATR + same side | 73.4% | 33205 / 45266 |
| 0.35*ATR + on chart (10% sample) | 45.7% | 2068 / 4527 |

| side | n locks | zone share |
|---|---|---|
| ceiling | 22534 | 81.1% |
| floor | 22732 | 80.6% |

Detail per lock: `DR3_BARRIER_COINCIDENCE.csv`. Counts per sampled bar: `ARMED_COUNTS.csv`. Case detail: `LINE_AUDIT_CASES.csv`. The on-chart sample (every 10th lock, `chart_match` column): `DR3_BARRIER_COINCIDENCE_CHART_SAMPLE.csv`.

## 4. Line book (created over DESIGN 2016-2021)

| kind | lines created |
|---|---|
| box_bottom | 46413 |
| box_top | 46396 |
| flag_lower | 7816 |
| flag_upper | 7759 |
| level | 55583 |
| pdh | 1556 |
| pdl | 1556 |
| round | 49 |
| sess_hi | 3114 |
| sess_lo | 3114 |
| trendline | 91805 |
| tri_lower | 3373 |
| tri_upper | 3372 |

Engine counters: `box_seeded=46592, level_seed=55583, level_seed_dup=29007, line_expired=271882, line_retired_level=2986, line_retired_trendline=39753, line_stale=331, pattern_seeded_flag=8757, pattern_seeded_triangle=3948, round_seeded=49, tl_seed=91805, tl_seed_dup=573612`

## 5. Method and recompute

```
cd "03. EA Developer/EA_VolmanPA/research/lines"
python test_vpa_lines.py          # 36/36 fixtures + prefix invariance (synthetic + real data)
python lines1_run.py --audit      # this file + the 3 CSVs
python lines1_run.py --snapshots  # PLAN/lines1/snapshots/*.png
```

Config = `vpa_lines.DEFAULTS` (the engine prints nothing it does not use). Causality: a pivot at i is known at i+lag; a line exists only from `created_idx`; `armed_at(t)` recomputes from bars <= t through the same `_step_line` path the pass used; `test_prefix_invariance` re-runs on bars[:t+1] and matches. No outcomes (fills/PnL/win rate) are read or written anywhere.
