# DISCRIMINATION_DR2C — per-gate fail rates, Lead A/B vs C (BURNED set)

Config: DR2c = signal_atr 0.50 + v1 sessions + room_sig/PDH + signal_prev_bar. Evaluated cases only ((iii)+(iv)). No outcomes (E4); burned set (E3).

Source: `RECALL_TRACE_DR2C.csv` (same run, one row per case; the per-gate cells below are recomputable from its `category` + `fail_set` columns). NOTE: `RECALL_TRACE.csv` is the DR1-default trace and does NOT reproduce this table.

| gate | fail A/B | rate | fail C | rate | gap (C-AB) |
|---|---|---|---|---|---|
| warmup | 0/15 | 0.000 | 0/34 | 0.000 | +0.000 |
| session | 1/15 | 0.067 | 1/34 | 0.029 | -0.037 |
| direction | 3/15 | 0.200 | 10/34 | 0.294 | +0.094 |
| trend | 2/15 | 0.133 | 24/34 | 0.706 | +0.573 |
| chop | 5/15 | 0.333 | 4/34 | 0.118 | -0.216 |
| buildup | 11/15 | 0.733 | 22/34 | 0.647 | -0.086 |
| room | 4/15 | 0.267 | 12/34 | 0.353 | +0.086 |
| adverse | 4/15 | 0.267 | 11/34 | 0.324 | +0.057 |
| anti_chase | 4/15 | 0.267 | 3/34 | 0.088 | -0.178 |
| cost | 0/15 | 0.000 | 0/34 | 0.000 | +0.000 |

Evaluated: A/B 15/16, C 34/44.

First-fail histogram (the funnel's binding gate):

| first_fail | A/B | C |
|---|---|---|
| skip_chop | 3 | 2 |
| skip_direction | 3 | 9 |
| skip_no_buildup | 3 | 1 |
| skip_room | 3 | 3 |
| skip_session | 1 | 1 |
| skip_trend | 2 | 18 |