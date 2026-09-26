# TIME_SANITY — F4: the `-1:15` UTC value, root cause and fix

Task: T-VPA-DR3, step 0 (done BEFORE the prereg freeze).
Owner of the fix: `research/lab/vpa_data.py:55-59`.

## 1. Symptom

`PLAN/diag_dr1/snapshots/INDEX.csv` (pre-fix) had `missed_04 ... utc = -1:15`
(bar_idx 162562). Negative / wrapped UTC labels are invalid.

## 2. Root cause (two bugs, one visible)

`vpa_data.load_m5_bars` computed

```python
utc_min = (naive_all.hour.values * 60 + naive_all.minute.values) - off * 60
```

with `off = eu_server_offset_hours(naive)` (server = UTC + 2 winter / + 3 summer,
`vpa_random_baseline.py:60-70`).

- **B1 (real bug, data):** no wrap into `[0, 1440)`. For server times just after
  midnight the UTC clock is on the previous day: server 01:15 with `off = 2`
  → `-45` (i.e. 23:15 UTC). Count over DESIGN: **41,449 / 440,040 bars
  (9.4%) had negative `utc_min`.**
- **B2 (display bug, presentation):** the snapshot formatter
  (`vpa_diag_snapshots.hhmm`, `vpa_snapshots` equivalent) prints `int(m)//60`
  and `int(m)%60` on the negative value: `-45` → `-1:15` (floor division on a
  negative). Only cosmetic once B1 is fixed.

## 3. Fix

`vpa_data.py`: `utc_min = (srv_min - off * 60) % 1440` (numpy non-negative
modulus). `srv_min` is now computed once and reused. No other file changed.

## 4. Impact check (fix must not move any decision)

| check | result |
|---|---|
| `utc_min` range after fix | `[0, 1435]`, negatives **0** |
| session class (v1 windows 05:00–11:00 / 11:30–17:30 UTC) old vs new | **0 changes over 440,040 bars** |
| DR1 detector after fix | `records 19957, exec 1, chop_exempt 278` (identical to pre-fix) |
| DR2c detector after fix | `records 98213, exec 4` (identical to pre-fix) |
| `missed_04` label after fix | **23:15** (was `-1:15`) |

Why zero session impact: the affected bars are UTC 21:30–24:00, outside both v1
windows (05:00–11:00 and 11:30–17:30). The negative values previously fell
through the session test as `None`; after the wrap they are still outside.

## 5. Verification against the data source's timezone/DST (3 timestamps)

Server clock convention (broker, EU): UTC + 2 winter, UTC + 3 summer; EU DST
switches on the last Sunday of March/October. Verified on the parquet index:

| case | server (naive) | offset fn | `utc_min` | UTC label | in session? |
|---|---|---|---|---|---|
| winter | 2019-01-15 10:00 | +2 | 480 | 08:00 | yes (london) |
| summer | 2019-07-15 10:00 | +3 | 420 | 07:00 | yes (london) |
| DST switch week (March) | first bar after the weekend: 2019-04-01 00:25 | +3 | 1285 | Sun 21:25 | no |
| DST switch week (October) | first bar after the weekend: 2019-10-28 00:25 | +2 | 1345 | Sun 22:25 | no |

The March/October switch week is verified through the first post-weekend bar
(Monday 00:25 server): it is labelled with the **new** offset (21:25 / 22:25 UTC
on Sunday), which matches the real EU switch at 01:00 UTC Sunday.

**Known residual (documented, zero effect on data):** `eu_server_offset_hours`
switches at the last Sunday 01:00 **server** time, while the real EU switch is
01:00 **UTC** (03:00/04:00 server). The imprecision window is therefore Sunday
01:00–04:00 server — the market is closed then (no bars exist; the first bar is
Monday 00:25 server, already after the real switch). No existing bar carries a
wrong offset; this is why the shared v1 helper was NOT modified (frozen
convention, and changing it would alter v1 outputs for zero data benefit).

## 6. Consequence for DR3

`utc_min` is now a valid clock and is used as-is by the session gate
(v1 windows: `eu (300, 660)`, `us (690, 1050)`). The lunch dead-zone
(tr. 227/273: EU 12:00–14:00 CET = 11:00–13:00 UTC, NY 18:00–20:00 CET
= 17:00–19:00 UTC) is a **logged feature only** in DR3, per F2/F4.
