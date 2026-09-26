# GATE_MAP -- line-by-line Python -> MQL5 map (T-VPA-VIS-1, A3)

Python truth = the frozen code, not the prose:

- `P` = `03. EA Developer/EA_VolmanPA/research/lab/` (read-only)
  - `vpa_core.py`, `vpa_dr1.py`, `vpa_data.py`, `vpa_random_baseline.py`
- `M` = `03. EA Developer/VPA_Vision/VPA_Core.mqh` (single logic path; the
  indicator and the parity script both include it)
- `I` = `03. EA Developer/VPA_Vision/VPA_Vision.mq5` (drawing only)

Config values are frozen as `#define`s at `M:9-91`; every number below is the
DR3 value (`vpa_dr1.py:95-107` over `vpa_dr1.py:29-93`).

## 1. Clock

| Python | MQL5 | value |
|---|---|---|
| `vpa_random_baseline.eu_server_offset_hours` (server = UTC+2 winter / +3 summer, switches last Sun Mar/Oct +1h) | `M:257 VpaLastSundayOfMonth` + `M:266 VpaUtcMinute` | off = 3 iff close-time in [last Sun Mar 01:00, last Sun Oct 01:00) |
| `vpa_data.py:55-60` `utc_min = (srv_min - off*60) % 1440`, `srv_min` from the bar CLOSE | `M:266-275` | modulo fix present, no negatives |
| bar close time = open + 300 s | `I:170`, `M:1678` (`PeriodSeconds`) | M5 |
| `day = int(t)//86400` (vpa_dr1.py:213) | `M:462-463` | UTC epoch day of the bar OPEN time |
| `pdh/pdl` set on the first bar of a new day, `None` before (vpa_dr1.py:214-225) | `M:462-480` + `M:318 m_pd_ok` | flag replaces `None` |

## 2. Indicators (per closed bar)

| feature | Python | MQL5 | exact |
|---|---|---|---|
| TR | `vpa_core.py:120-124` | `M:427-431` | `max(h-l, abs(h-c[t-1]), abs(l-c[t-1]))` |
| ATR14 Wilder, seed `mean(tr[0:14])` at t==13 | `vpa_core.py:125-128` | `M:432-445` | `(13*atr[t-1]+tr)/14` |
| EMA25, seed `mean(c[0:25])` at t==24, alpha=2/26 | `vpa_core.py:129-132` | `M:446-460` | same recursion (not `iMA`) |
| CLV | `vpa_core.py:133-134` | `M:461` | `(2c-h-l)/rng`, 0 if rng=0 |
| pressure components (disp>=0.60, er>=0.55, meanCLV>=0.20, EMA slope>=0.10; den<=0 -> false) | `vpa_core.py:164-179` | `M:518-541` | 6-bar window, 5-term den, `u>=6` implied |
| pressure run length / `last_pressure_end` | `vpa_core.py:136-151` | `M:484-500` | `pdur` reset on side flip |
| pressure duration threshold 2 (base detector only) | `vpa_core.py:407` | not ported | the DR3 path never reads `pdur` |
| bias (+1/-1/0) | `vpa_core.py:152-162` | `M:502-516` | slope over 6 bars, side band +-0.20; 0 when ATR/EMA invalid |

## 3. Pivots & barriers

| Python | MQL5 | value |
|---|---|---|
| pivot confirm `pivot_lag=2` (vpa_core.py:182-196, vpa_dr1.py:184-195) | `M:544-559` | strict left, `>=` right (high); strict left, `<=` right (low) |
| significant pivot `pivot_sig_lag=5`, tested at `t=j+5`, `j>=5` (vpa_dr1.py:196-207) | `M:560-600` | +-5 window, each j once |
| pivot caps 400 (`vpa_dr1.py:195,206`) | `M:607-636` | keep newest 400 |
| lock scan `scan=17`, spacing >=2, `eps=0.10*A` (vpa_core.py:198-216) | `M:638-671` | j from i-2 down to i-17; median of touch prices |
| `t_min=2` | `M:672-676` | counter `skip_barrier_insufficient_touches` |
| already-broken guard `+-0.05*A` | `M:677-686` | counter `skip_barrier_already_broken` |
| dedupe `0.10*A` or >=2 shared touches | `M:687-707` | counter `skip_duplicate_barrier` |
| barrier record: `exp_idx = lock_idx+20` | `M:708-726` | expiry 20 |
| expiry only in `_barrier_update` (vpa_dr1.py:227-240); base-class break detection is NOT reached | `M:730-754` | counter `barrier_expired` |
| tombstones (`vpa_core.py:235,264`; `vpa_dr1.py:235,240`) | **omitted** | write-only in the DR3 path: `_try_lock` reads only `active` -- no behaviour effect |

## 4. Signal evaluation & consumption (`_dr1_eval`, vpa_dr1.py:270-319)

| Python | MQL5 | value |
|---|---|---|
| skip when `dist < -signal_atr*A` | `M:773-775` | `signal_atr=0.50` |
| breakout when `dist > signal_max_atr*A` | `M:777` | `signal_max_atr=0.25` |
| `signal_prev_bar=True`: signal = last element of `[i for i in touches if lock_idx<=i<t]` | `M:779-785` | in the frozen code this always resolves to `lock_idx` (see `PARITY.md` section "Port findings") |
| candidate evaluated then the barrier is consumed as missed when it returns None | `M:786-798` | counter `signal_eval`, then `skip_missed_break` |
| inside the band -> candidate at `t`, barrier stays active on reject | `M:801-809` | counter `signal_eval` |
| consumption removes the barrier and stamps `end_idx`/`end_kind` | `M:811-839` | `exec` / `missed` |

## 5. Gates (`_dr1_gates`, vpa_dr1.py:322-402) -- all evaluated, no short-circuit

| # | gate | Python | MQL5 | DR3 value |
|---|---|---|---|---|
| 0 | warmup | `vpa_dr1.py:334` | `M:993-994` | `sig >= 50` |
| 1 | session | `vpa_dr1.py:332,335` (`_session_dr1` 253-261) | `M:996-997`, `M:968-977` | eu [300,660), us [690,1050) UTC min, measured at the **trigger** bar |
| 2 | direction | `vpa_dr1.py:336-341` | `M:999-1004` | body sign, doji if `abs(body) <= 0.10*rng` |
| 3 | trend | `vpa_dr1.py:342-347` | `M:1006-1024` | `slope>=0.10` over 6 bars, `frac>=0.6` over 10 |
| 4 | integrity | `vpa_dr1.py:348-365` | `M:1026-1046` | `eps=0.10*A`, window `[first_touch..sig]`, `pass=True` if no touch <= sig |
| 5 | chop | `vpa_dr1.py:368-376` | `M:1064-1072`, `M:1296 ChopDr1`, `M:1263 ChopMetrics` | 4 bars before the signal bar: overlap>=0.65, falling-lows<=1/3, (doji<=0.35 or bar>1.5A); exempt if buildup |
| 6 | buildup | `vpa_dr1.py:366-367`, `466-515` | `M:1048-1063`, `M:1139 BuildupDr1` | largest n in [3,10] with 4/4 conds (band closes>=2, touches>=1, overlap>=0.45, contraction<=0.85); logs v2of4/vtight/squeeze |
| 7 | room | `vpa_dr1.py:377-384` | `M:1073-1109`, `M:1329 RoomDetail`, `M:1304 RoomZone` | `room >= 2.0*S`; sources: +-5 pivots, active barriers, PDH/PDL, 00/50 grid; zone `max(touch_extreme+eps, entry+max(eps,0.5R))` |
| 8 | adverse | `vpa_dr1.py:385-386`, `620-641` | `M:1110-1115`, `M:1424 AdverseDetail` | pivot older than `buildup_start`, band (0.10S, 0.5S); round grid below/above |
| 9 | anti-chase | `vpa_dr1.py:387-394` | `M:1116-1127` | `entry_b<=1pip+0.35A`, `range<=1.5A`, `abs(entry-EMA)<=1.5A` |
| 10 | cost | `vpa_dr1.py:395-396` | `M:1128-1131` | `rho = 1/8 = 0.125 <= 0.20` (always passes) |
| entry / invalidation | `vpa_dr1.py:378-379` | `M:1076-1094` | entry = extreme -/+ 1 pip; inv = min(low)/max(high) of `[bu_start..sig)` -/+ 0.10A |
| first-fail verdict, hard subset | `vpa_dr1.py:126-149`, `GATE_ORDER` 111-123 | `M:204-226` (keys/reasons/hard), `M:866-880` | DR3 hard = warmup, session, direction, trend, integrity, cost |
| counters | `vpa_dr1.py:114-115` | `M:384-407` | same key names |

## 6. Feature logging

| field | Python | MQL5 |
|---|---|---|
| `bar_idx` (signal) / `trigger_idx` | `vpa_dr1.py:418` | `M:850-851` |
| `session` at the trigger bar | `vpa_dr1.py:413` | `M:856` |
| `atr`, `ema`, `bias`, `pressure`, `bars_since_pressure` (sentinel `10**9+sig`) | `vpa_dr1.py:420,435-436` | `M:857-864` |
| `lunch` = utc_min in [660,780) or [1020,1140) | `vpa_dr1.py:263-268,437` | `M:979-984` |
| `n, contraction, overlap, band_closes, touches_in_buildup, squeeze` | `vpa_dr1.py:422-427` | `M:1052-1063` |
| `trend_slope` round(4), `frac_side` round(3) | `vpa_dr1.py:347,428-429` | `M:1021-1023` |
| `signal_body_frac`, `doji` | `vpa_dr1.py:341,430` | `M:1002-1004` |
| `room_r` = room/S round(3), adverse flag | `vpa_dr1.py:383-384,446-447` | `M:1103-1109` |
| `rho` | `vpa_dr1.py:434` | `M:1128-1131` |
| `hard_gates` list (stored only) | `vpa_dr1.py:438` | not stored (constant subset) |
| `active_others` (diagnostic, unused by the CSV) | `vpa_dr1.py:439-440` | not ported |
| **combi** classification of an accepted record | `vpa_dr1.py:456-459`, `646-663` | `M:1481-1498` |
| **CSV export** (bars/events/barriers) | schema frozen in `PLAN/vis1/CONVERT_PLAN.md` + `compare_parity.py` (the row shape follows `vpa_trace.py:37-60`) | `M:1508 ExportCsv`, `M:1657 VpaExportWindow` |
| `fail_set` empty on ACCEPT rows | `vpa_trace.py:137-143` | `M:1563-1569` |

## 7. Drawing (indicator only) -> requirement map

| packet item | MQL5 |
|---|---|
| 1 barrier lines, dashed grey when integrity fails + `integrity` text | `I:309 DrawBarriers`, `I:214 MkTrend`, `I:230 MkText` |
| 1 touch markers | `I:326-336` (`OBJ_ARROW` 159) |
| 2 EMA25 as the detector computes it | `I:134 Rebuild` -> buffer 0 (`I:90`, `I:195-204`) |
| 2 ATR(14) Wilder | `I:435 DrawAtrPanel` (numeric + spark) |
| 3 signal bar highlight, entry/stop(S=8)/target(2R) lines | `I:387 DrawEvents` (`I:410-419`) |
| 3 ACCEPT/SKIP label with the failed hard gates | `I:349 EventLabel` (line 1) |
| 4 `room_r`, obstacle line, `ema_dist_atr`, squeeze, lunch | `I:349-385` (line 3), `I:420-423` orange line |
| 5 layer toggles, history depth, colors | `I:33-72` inputs |
| 6 server->UTC incl. modulo fix | `M:266 VpaUtcMinute` |
| no repaint: forming bar excluded, redraw once per closed bar | `I:106-131` (`iTime(...,1)` gate), `I:154-181` (slice ends at `r[1]`) |
| object cleanup on every redraw (prefix wipe) | `I:477-486 DrawAll` -> `ObjectsDeleteAll(0,"VPA_VIS_")` |
| parity export on the indicator (optional) | `I:136-150` -> `M:1657` |

## 8. Deliberate non-ports (with reason)

1. `Detector._maybe_pr` / `_pr_at` / `_eval_pattern_break` / `_on_break` /
   `_bias_ok` / `_chop_at` / `_room_pips` / `_buildup` / `_combi_bars`
   (`vpa_core.py`) -- unreachable from `Dr1Detector.run` (`vpa_dr1.py:242-250`
   never calls `_maybe_pr`, and `Dr1Detector._barrier_update` replaces the base
   `_on_break` path).
2. `pdur` / `last_pressure_side` -- written but never read in the DR3 path
   (the pressure features logged are `pressure[sig]` and `bars_since_pressure`).
3. `tombstones` -- write-only (see section 3).
4. `_median` of an empty list returning `nan` -- replaced by an explicit
   `n<=0` guard (`M:228-252`) on paths the frozen config can reach; the
   `VpaMedian` of >=1 element is exact (odd -> middle, even -> mean of the two
   middle values, `statistics.median` semantics).
5. `active_others` and the `hard_gates` copy inside each record -- diagnostic
   fields the census/trace never read.

