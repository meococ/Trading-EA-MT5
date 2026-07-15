# HARD PIVOT W13 offline probes — `OFFLINE_ALL_KILL__NO_MODEL0`

Receipt `458A9E31285183A08288A4999FC0F4A8995EC45E8DA9087F9862C0FCA461B34F`
QFSI: QFSI 007 parallel; cost freeze GAP; login not headline

| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-FX3-H1-PRIOR2D-RANGE-BREAK-CONT-001` | 2021 | 1.0377 | 7.7518 | 1.0032 | 0.9866 | KILL |
| `HYP-FX3-H1-USD-CONSENSUS-IMPULSE-CONT-001` | 3950 | 1.0609 | 15.1507 | 1.0237 | 1.0058 | KILL |
| `HYP-BOOK-PRIOR2D-USDCONSENSUS-APRIORI-001` | 5780 | 1.0455 | 22.1699 | 1.0097 | 0.9924 | KILL |

- Caps book: corr=0.1394 overlap=0.1393 ok=False
- Model 0: WITHHELD (no survivor)

## Cost grade
- QFSI 007: watcher_alive=True cap_pid=72320 quotes=45557 hb=60000 tick_err=0
- quote_days=2/90 (gap=88); raw_deals=11; freeze_eligible=False
- commission unique days: {'EURUSD': '2/30', 'GBPUSD': '0/30', 'USDJPY': '0/30', 'XAUUSD': '0/30', 'BTCUSD': '3/30'}
- slip: MISSING_NE_0 — QFSI accumulate may grow fill rows but research freeze still needs verified side/ref/fill sample
- verdict: `COST_FREEZE_STILL_GAP__DEALS_STILL_~11__QUOTE_DAYS_CALENDAR_BOUND`
- Autonomous remaining: keep QFSI alive (calendar-bound days); retry deals (still ~11=exhausted); do NOT invent cost; Owner export optional only.
