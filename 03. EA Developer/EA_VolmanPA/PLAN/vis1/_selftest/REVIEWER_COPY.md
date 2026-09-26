# VPA_Vision parity report

- dir: `_selftest`
- generated (UTC): 2026-09-20T11:11:11Z
- symbol: EURUSD  pip=0.0001  tick=1e-05
- window: none (all rows)
- detector: DR3_CFG + round_grid_price=50*pip, collect_gates=True, trace_barriers=True
- fail_set gate order: warmup;session;direction;trend;integrity;chop;buildup;room;adverse;anti_chase;cost
- compared fields: events (all except event_id), barriers (all except barrier_id)
- tolerances: doubles 1e-7, room_r/trend_slope/frac_side 1e-3, ints/strings/bools exact, inf == inf, empty == NaN == not evaluable
- matching: events grouped by (bar_idx, trig_idx, side), barriers by (lock_idx, side); inside a group greedy nearest `level` with |delta| <= 1e-6
- paired = rows matched by key+level; full match = paired rows whose every compared field agrees; mismatched = max(mql, py) - full match; rate = full match / max(mql, py)
- window: events filtered on the timestamp of `trig_idx`, barriers on the timestamp of `lock_idx`

## Time check (server -> UTC, Python rule)

| rows | srv_min mismatch | utc_min mismatch | idx mismatch |
|---|---|---|---|
| 4000 | 0 | 0 | 0 |

Target 0. The detector runs on the recomputed `utc_min`; a non-zero count means the MQL5 time rule diverges.

## Detector run

- bars: 4000
- records: 1169
- lock_log: 534 barriers, event_log: 270 events
- counters: {'barrier_expired': 260, 'barrier_locked': 534, 'chop_exempt_buildup': 13, 'executable_combi': 1, 'executable_pattern_break': 62, 'signal_eval': 1169, 'skip_missed_break': 207}

## Counts

| table | mql | py | paired | full match | mismatched | rate |
|---|---|---|---|---|---|---|
| events | 1169 | 1169 | 1169 | 1169 | 0 | 1.000000 |
| barriers | 534 | 534 | 534 | 534 | 0 | 1.000000 |
| **total** | 1703 | 1703 | 1703 | 1703 | 0 | 1.000000 |

## Field mismatch histogram

| table | field | rows |
|---|---|---|
| - | (none) | 0 |

## Details (first 25)

```
(none)
```

## Verdict

match_rate=1.000000 min_match=0.950000 -> PASS
