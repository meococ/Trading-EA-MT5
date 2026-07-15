# VN brief — Clean book + Round 31

Thời điểm: 2026-07-15 ~14:17 ICT
Lane: clean-book + discovery R31 NON-FADE structural/event/book. GOAL: chưa đạt.

## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`
PRIMARY PF@$12=1.184 tpw=3.241 verdict=`DIAGNOSTIC_PARTIAL__CAPS_OK__GOAL_SCREEN_FAIL`; EXTENDED PF@$12=1.044 tpw=6.382 verdict=`DIAGNOSTIC_FAIL_GOAL_SCREEN`; freeze_sha=F18FAB12ECCBD3FF…
- Model 0 book-level: **WITHHELD**.

## 2. Discovery Round 31 — Outside / FirstDOM / TimeStop-CD
| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-OUTSIDE-BAR-CONT-001` | 3278 | 0.9626 | 12.5732 | 0.9034 | KILL |
| `HYP-GBPUSD-H1-FIRST-DOM-CONT-001` | 17 | 0.3147 | 0.0652 | 0.2883 | KILL |
| `HYP-FX3-H1-POST-TIMESTOP-CD-ARCH-CONT-001` | 3896 | 0.9466 | 14.9436 | 0.881 | KILL |
Receipt `AAD9BA4043042D994B02AD9B1638C103C4FEE02000FEDC4232E8091D02527343` → `OFFLINE_ALL_KILL__NO_MODEL0`
Freeze `18DF2BC4645E5DC9…`

## 3. QFSI 007 + cost
watcher_hb ts=2026-07-15T07:17:52.726794Z alive=True cap_pid=72320 wall_rem=254779; 007 accumulate hb=17100 quotes=13475 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline
Cost: autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R31 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

## Near-miss shelf (do not densify)
- R29 USDJPY OPEX Friday: PF≈1.35 x1.5≈1.26 nhưng N=76 / tpw≈0.29 — **cấm densify cửa sổ**.
- R25 USDJPY H4-engulf CONT: PF≈1.24 x1.5≈1.16 — **cấm densify**.
- R28 prior-week HL PF≈1.10 — không densify.

## Cấm
Densify R1–R31 / TA clones / OPEX-window / dayopen / IMM / samedircap / outside / firstdom / tstopcd / fade-session / unpark / RR2-exit / FRED / Phase-0 / H4-engulf.

## Next agent
Giữ QFSI; greenfield ngoài R31 (**NON-FADE, non-indicator**); cost autonomous.
Best shelf RR2 `194548`. GOAL unmet.
