# HARD PIVOT W15 offline probes — `OFFLINE_ALL_KILL__NO_MODEL0`

Receipt `2083ACD337D36B06E7995BF435BE8CFD8FCD551EEE1E782B4AA978449CECF6B0`
QFSI spot-check: `QFSI_007_HEALTHY`; cost freeze GAP; login not headline

| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-FX3-H1-LONDON-RANGE-NY-BREAK-CONT-001` | 1528 | 1.033 | 5.8608 | 0.9889 | 0.9677 | KILL |
| `HYP-FX3-H1-PRIOR-DAY-PIVOT-R1S1-BREAK-CONT-001` | 1434 | 1.0006 | 5.5003 | 0.9639 | 0.9462 | KILL |
| `HYP-BOOK-LRANGE-NYBREAK-PIVOT-APRIORI-001` | 2733 | 1.005 | 10.4827 | 0.9652 | 0.946 | KILL |

- Caps book: corr=0.3079 overlap=0.0575 ok=False
- Model 0: WITHHELD (no survivor)

## Cost grade
- QFSI 007: watcher_alive=True cap_pid=72320 quotes=45557 hb=60000 tick_err=0
- quote_days=2/90 (gap=88); raw_deals=11; freeze_eligible=False
- commission unique days: {'EURUSD': '2/30', 'GBPUSD': '0/30', 'USDJPY': '0/30', 'XAUUSD': '0/30', 'BTCUSD': '3/30'}
- slip: MISSING_NE_0 — QFSI accumulate may grow fill rows but research freeze still needs verified side/ref/fill sample
- verdict: `COST_FREEZE_STILL_GAP__DEALS_STILL_~11__QUOTE_DAYS_CALENDAR_BOUND`
- Autonomous remaining: keep QFSI alive (calendar-bound days); retry deals (still ~11=exhausted); do NOT invent cost; Owner export optional only.
- W15 spot-check: `QFSI_007_HEALTHY` hb_alive=True proc_alive=True pid=72320 @ 2026-07-15T10:30:07.071839Z
