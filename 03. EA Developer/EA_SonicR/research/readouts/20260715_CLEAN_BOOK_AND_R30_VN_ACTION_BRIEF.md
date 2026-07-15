# VN brief — Clean book + Round 30

Thời điểm: 2026-07-15 ~14:15 ICT
Lane: clean-book + discovery R30 NON-FADE structural/event/book. GOAL: chưa đạt.

## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`
PRIMARY PF@$12=1.184 tpw=3.241 verdict=`DIAGNOSTIC_PARTIAL__CAPS_OK__GOAL_SCREEN_FAIL`; EXTENDED PF@$12=1.044 tpw=6.382 verdict=`DIAGNOSTIC_FAIL_GOAL_SCREEN`; freeze_sha=F18FAB12ECCBD3FF…
- Model 0 book-level: **WITHHELD**.

## 2. Discovery Round 30 — Day-Open / IMM / SameDir-Cap2
| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-PRIOR-DAY-OPEN-BREAK-CONT-001` | 1579 | 1.0011 | 6.0564 | 0.9373 | KILL |
| `HYP-EURUSD-H1-IMM-WEDNESDAY-CONT-001` | 27 | 1.0405 | 0.1036 | 0.9592 | KILL |
| `HYP-FX3-H1-SAMEDIR-CAP2-ARCH-CONT-001` | 3896 | 0.9393 | 14.9436 | 0.8748 | KILL |
Receipt `DD7FE049B2D3B35F19C21F3649B99F3C750F747BE5647C463FFAD6866522F635` → `OFFLINE_ALL_KILL__NO_MODEL0`
Freeze `562C452F380A3303…`

## 3. QFSI 007 + cost
watcher_hb ts=2026-07-15T07:15:35.157419Z alive=True cap_pid=72320 wall_rem=254916; 007 accumulate hb=16560 quotes=13098 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline
Cost: autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R30 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

## Near-miss shelf (do not densify)
- R29 USDJPY OPEX Friday: PF≈1.35 x1.5≈1.26 nhưng N=76 / tpw≈0.29 — **cấm densify cửa sổ**.
- R25 USDJPY H4-engulf CONT: PF≈1.24 x1.5≈1.16 — **cấm densify**.
- R28 prior-week HL PF≈1.10 — không densify.

## Cấm
Densify R1–R30 / TA clones / OPEX-window / equal-HL / oneslot / week-HL / monthend / losscd / dayopen / IMM / samedircap / fade-session / unpark / RR2-exit / FRED / Phase-0 / H4-engulf.

## Next agent
Giữ QFSI; greenfield ngoài R30 (**NON-FADE, non-indicator**); cost autonomous.
Best shelf RR2 `194548`. GOAL unmet.
