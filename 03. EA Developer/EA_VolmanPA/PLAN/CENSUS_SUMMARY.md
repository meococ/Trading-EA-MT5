# CENSUS_SUMMARY — VPA-P2 (outcome-blind)

DESIGN 2016-01-01 → 2021-12-31 · detector `research/lab/vpa_core.py` · no PnL, no exits, no fills — candidate counts only.

## EURUSD

- bars: 440,040 · weeks: 314 · detector runtime: 6.23s

| metric | total | /week mean | /week median | p10 | p90 |
|---|---|---|---|---|---|
| raw breaks (locked barrier + close-break) | 19778 | 62.987 | 63.0 | 54.0 | 71.0 |
| EXECUTABLE pattern break | 11 | 0.035 | 0.0 | 0.0 | 0.0 |
| EXECUTABLE combi | 0 | 0.0 | 0.0 | 0.0 | 0.0 |
| EXECUTABLE pullback reversal | 51 | 0.162 | 0.0 | 0.0 | 1.0 |
| EXECUTABLE total | 62 | 0.197 | 0.0 | 0.0 | 1.0 |

By year:

```
      raw_break  exec_pb  exec_combi  exec_pr
year                                         
2016       3309        1           0        3
2017       3315        4           0        2
2018       3356        0           0        8
2019       3281        2           0       10
2020       3252        0           0       15
2021       3265        4           0       13
```

By session: {'london': {'exec': 33, 'raw': 4979}, 'ny': {'exec': 29, 'raw': 4799}}

Funnel (pattern break):

| stage | count |
|---|---|
| raw breaks | 19778 |
| - skip_session | 10000 |
| - skip_bias | 931 |
| - skip_chop | 2326 |
| - skip_no_pressure | 5979 |
| = reached buildup gate | 542 |
| - skip_no_buildup | 531 |
| - skip_room / skip_cost | 0 |
| = EXECUTABLE pattern break | 11 |

Exit-code counters: `{"barrier_expired": 26554, "buildup_fail_contraction": 22, "buildup_fail_counter": 5, "buildup_fail_inside": 3180, "buildup_fail_overlap": 1, "buildup_fail_progression": 6, "buildup_fail_touches": 21, "executable_pattern_break": 11, "executable_pullback_reversal": 51, "pr_skip_chop": 15, "pr_skip_session": 55, "raw_break": 19778, "skip_barrier_already_broken": 26, "skip_barrier_insufficient_touches": 67321, "skip_bias": 931, "skip_chop": 2326, "skip_duplicate_barrier": 4937, "skip_no_buildup": 531, "skip_no_pressure": 5979, "skip_pbp_excluded": 108, "skip_session": 10000}`

## GBPUSD

- bars: 439,687 · weeks: 314 · detector runtime: 6.28s

| metric | total | /week mean | /week median | p10 | p90 |
|---|---|---|---|---|---|
| raw breaks (locked barrier + close-break) | 19937 | 63.494 | 64.0 | 53.0 | 73.0 |
| EXECUTABLE pattern break | 6 | 0.019 | 0.0 | 0.0 | 0.0 |
| EXECUTABLE combi | 0 | 0.0 | 0.0 | 0.0 | 0.0 |
| EXECUTABLE pullback reversal | 43 | 0.137 | 0.0 | 0.0 | 1.0 |
| EXECUTABLE total | 49 | 0.156 | 0.0 | 0.0 | 1.0 |

By year:

```
      raw_break  exec_pb  exec_combi  exec_pr
year                                         
2016       3355        2           0        4
2017       3342        1           0        6
2018       3308        0           0        8
2019       3342        0           0        5
2020       3224        0           0        8
2021       3366        3           0       12
```

By session: {'london': {'exec': 24, 'raw': 4780}, 'ny': {'exec': 25, 'raw': 4928}}

Funnel (pattern break):

| stage | count |
|---|---|
| raw breaks | 19937 |
| - skip_session | 10228 |
| - skip_bias | 1026 |
| - skip_chop | 2304 |
| - skip_no_pressure | 5855 |
| = reached buildup gate | 524 |
| - skip_no_buildup | 515 |
| - skip_room / skip_cost | 2 |
| = EXECUTABLE pattern break | 6 |

Exit-code counters: `{"barrier_expired": 27496, "buildup_fail_contraction": 20, "buildup_fail_counter": 3, "buildup_fail_inside": 3072, "buildup_fail_progression": 7, "buildup_fail_touches": 17, "executable_pattern_break": 6, "executable_pullback_reversal": 43, "pr_skip_chop": 15, "pr_skip_session": 46, "raw_break": 19937, "skip_barrier_already_broken": 20, "skip_barrier_insufficient_touches": 66867, "skip_bias": 1026, "skip_chop": 2304, "skip_duplicate_barrier": 5396, "skip_no_buildup": 515, "skip_no_pressure": 5855, "skip_pbp_excluded": 100, "skip_room": 2, "skip_session": 10228, "skip_warmup": 1}`

## Verdict vs Lead stop rule

Stop rule (Lead, VPA-P1/P2): *executable census < 10/week on EURUSD → finish census + summary, skip snapshots, report.*

EURUSD EXECUTABLE total = **0.197/week** (62 candidates / 314 weeks). Pattern-break alone = 0.035/week; pullback reversal = 0.162/week.

**STOP RULE TRIGGERED → snapshots skipped, no grading, no economics.** The pre-buildup ceiling (session+bias+chop+pressure) is also far below the 10/week floor, so this is structural for the frozen M5 definition, not a final-gate strictness artifact.
