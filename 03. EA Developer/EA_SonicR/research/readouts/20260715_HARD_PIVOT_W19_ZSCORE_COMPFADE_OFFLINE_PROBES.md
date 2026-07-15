# HARD PIVOT W19 offline probes — `OFFLINE_ALL_KILL__NO_MODEL0`

Receipt `66E7D980FACBF3F7DD894B3CF6164980CA3DBC3129337D5ABEDBA8F550063D2B`
QFSI spot-check: `QFSI_007_HEALTHY`; cost freeze GAP; login not headline

| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-FX3-H1-H4-EMA-ZSCORE-FADE-001` | 882 | 1.0245 | 3.383 | 0.9881 | 0.9706 | KILL |
| `HYP-FX3-H1-COMPRESSION-FALSEBREAK-FADE-001` | 57 | 1.0018 | 0.2186 | 0.9599 | 0.9397 | KILL |
| `HYP-BOOK-ZSCORE-COMPFADE-APRIORI-001` | 931 | 1.0233 | 3.571 | 0.9866 | 0.9689 | KILL |

- Caps book: corr=-0.0908 overlap=0.0238 ok=True
- Model 0: WITHHELD (no survivor)

## Cost grade
- QFSI 007: watcher_alive=True cap_pid=72320 quotes=45557 hb=60000 tick_err=0
- quote_days=2/90 (gap=88); raw_deals=11; freeze_eligible=False
- commission unique days: {'EURUSD': '2/30', 'GBPUSD': '0/30', 'USDJPY': '0/30', 'XAUUSD': '0/30', 'BTCUSD': '3/30'}
- slip: MISSING_NE_0 — QFSI accumulate may grow fill rows but research freeze still needs verified side/ref/fill sample
- verdict: `COST_FREEZE_STILL_GAP__DEALS_STILL_~11__QUOTE_DAYS_CALENDAR_BOUND`
- Autonomous remaining: keep QFSI alive (calendar-bound days); retry deals (still ~11=exhausted); do NOT invent cost; Owner export optional only.
- W19 spot-check: `QFSI_007_HEALTHY` hb_alive=True proc_alive=True pid=72320 @ 2026-07-15T10:38:09.185473Z
