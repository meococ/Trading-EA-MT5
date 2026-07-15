# HARD PIVOT W16 offline probes — `OFFLINE_ALL_KILL__NO_MODEL0`

Receipt `5A2214A62A93B7AB867C0B0A0F47139C9BE2C2FDECD0B6DC71ABA6AC0077F774`
QFSI spot-check: `QFSI_007_HEALTHY`; cost freeze GAP; login not headline

| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-FX3-H4-PRIOR-WEEK-HL-H1-RETEST-CONT-001` | 1216 | 1.0459 | 4.6641 | 1.0107 | 0.9937 | KILL |
| `HYP-FX3-H1-LONDON-FAILBREAK-NY-REVERSE-001` | 1142 | 1.0466 | 4.3803 | 1.01 | 0.9923 | KILL |
| `HYP-BOOK-WEEKHL-FAILBREAK-APRIORI-001` | 2333 | 1.0487 | 8.9485 | 1.0127 | 0.9954 | KILL |

- Caps book: corr=0.05 overlap=0.0357 ok=True
- Model 0: WITHHELD (no survivor)

## Cost grade
- QFSI 007: watcher_alive=True cap_pid=72320 quotes=45557 hb=60000 tick_err=0
- quote_days=2/90 (gap=88); raw_deals=11; freeze_eligible=False
- commission unique days: {'EURUSD': '2/30', 'GBPUSD': '0/30', 'USDJPY': '0/30', 'XAUUSD': '0/30', 'BTCUSD': '3/30'}
- slip: MISSING_NE_0 — QFSI accumulate may grow fill rows but research freeze still needs verified side/ref/fill sample
- verdict: `COST_FREEZE_STILL_GAP__DEALS_STILL_~11__QUOTE_DAYS_CALENDAR_BOUND`
- Autonomous remaining: keep QFSI alive (calendar-bound days); retry deals (still ~11=exhausted); do NOT invent cost; Owner export optional only.
- W16 spot-check: `QFSI_007_HEALTHY` hb_alive=True proc_alive=True pid=72320 @ 2026-07-15T10:31:49.825108Z
