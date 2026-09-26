# CENSUS_DR3 — trend-primary + integrity (prereg SHA A61F06BA…)

DESIGN EURUSD 2016-2021: 440040 bars, 312.7 weeks. records 91734, evaluated 29780, accepted 4331, rejected 25449.

## 1. Cadence (F6/D2)

**accepted 4331 = 13.85/week → NORMAL** (>=10 NORMAL, 3-<10 LOW_CADENCE, <3 STOP)

| year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|
| accepted | 717 | 744 | 723 | 735 | 668 | 744 |

per session: {'eu': 2055, 'us': 2276}

## 2. Funnel (first fail over the hard gates)

| first_fail | n |
|---|---|
| skip_trend | 22010 |
| executable | 4331 |
| skip_integrity | 3439 |

counters: `{"barrier_expired": 21112, "barrier_locked": 45599, "chop_exempt_buildup": 903, "executable_combi": 10, "executable_pattern_break": 4321, "signal_eval": 91734, "skip_barrier_already_broken": 26, "skip_barrier_insufficient_touches": 67321, "skip_direction": 7358, "skip_duplicate_barrier": 5671, "skip_integrity": 3439, "skip_missed_break": 20154, "skip_session": 54596, "skip_trend": 22010}`

## 3. Features (median [IQR]) accepted vs rejected

| feature | accepted | rejected |
|---|---|---|
| n | 10 [2] | 10.0 [1] |
| band_closes | 3 [2] | 3.0 [2] |
| buildup_touches | 2 [1] | 2.0 [2] |
| overlap | 0.7652350568478041 [0.12498350697336891] | 0.7575071939110349 [0.12596489855234683] |
| contraction | 0.7590361445781038 [0.12713734142289146] | 0.7628865979380853 [0.1303158223888261] |
| conditions_passed | 4 [0] | 4.0 [0] |
| v2of4_n | 10 [0] | 10.0 [0] |
| vtight_n | 10.0 [1] | 10 [0] |
| room_r | 0.612 [0.263] | 0.6 [0.21299999999999997] |
| entry_b_atr | 0.1849 [0.3448] | 0.2761 [0.3904000000000001] |
| range_atr | 0.8227 [0.4201999999999999] | 0.8156 [0.4262] |
| ema_dist_atr | 1.5082 [0.7394999999999998] | 0.72135 [0.7566999999999999] |
| bars_since_pressure | 10 [14] | 11 [15] |
| rho | 0.125 [0.0] | 0.125 [0.0] |
| atr | 0.000422568922793529 [0.00024096647135604345] | 0.00041653538609863304 [0.00023457188889655845] |

| rate | accepted | rejected |
|---|---|---|
| squeeze | 0.0074 | 0.1129 |
| chop_legacy | 0.2937 | 0.303 |
| chop_window | 0.1155 | 0.1259 |
| adverse | 0.2445 | 0.2714 |
| pressure | 0.1154 | 0.0574 |
| lunch | 0.1866 | 0.1925 |
| room_inf | 0.0071 | 0.0016 |

## 4. Burned-set diagnostic (E3: DIAGNOSTIC-ONLY, never fidelity)

- evaluated: A/B 15/16, C 34/44
- accepted (iv): A/B 9, C 8
- integrity fail: A/B 3, C 13 (F2c)
- trend fail: A/B 1, C 23
- first hard fail by grade: `{"AB:skip_direction": 3, "AB:skip_integrity": 2, "AB:skip_trend": 1, "C:skip_direction": 6, "C:skip_integrity": 1, "C:skip_session": 1, "C:skip_trend": 18}`

No outcome fields anywhere (F7/E4).