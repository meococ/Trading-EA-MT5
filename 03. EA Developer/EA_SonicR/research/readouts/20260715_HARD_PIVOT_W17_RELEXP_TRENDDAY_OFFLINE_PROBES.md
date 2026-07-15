# HARD PIVOT W17 offline probes — `OFFLINE_ALL_KILL__NO_MODEL0`

Receipt `1CBB0E989A2AE0EC03F57AACBB27EBBC9E2B06BC3DDF4D9D0E7342384AFADF4F`
QFSI spot-check: `QFSI_007_HEALTHY`; cost freeze GAP; login not headline

| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-FX3-H1-EURGBP-REL-EXPANSION-CONT-001` | 0 | None | 0.0 | None | None | KILL |
| `HYP-FX3-H1-D1-TRENDDAY-FOLLOWTHROUGH-CONT-001` | 690 | 0.9841 | 2.6466 | 0.9522 | 0.9369 | KILL |
| `HYP-BOOK-RELEXP-TRENDDAY-APRIORI-001` | 690 | 0.9841 | 2.6466 | 0.9522 | 0.9369 | KILL |

- Caps book: corr=None overlap=0.0 ok=True
- Model 0: WITHHELD (no survivor)

## Cost grade
- QFSI 007: watcher_alive=True cap_pid=72320 quotes=45557 hb=60000 tick_err=0
- quote_days=2/90 (gap=88); raw_deals=11; freeze_eligible=False
- commission unique days: {'EURUSD': '2/30', 'GBPUSD': '0/30', 'USDJPY': '0/30', 'XAUUSD': '0/30', 'BTCUSD': '3/30'}
- slip: MISSING_NE_0 — QFSI accumulate may grow fill rows but research freeze still needs verified side/ref/fill sample
- verdict: `COST_FREEZE_STILL_GAP__DEALS_STILL_~11__QUOTE_DAYS_CALENDAR_BOUND`
- Autonomous remaining: keep QFSI alive (calendar-bound days); retry deals (still ~11=exhausted); do NOT invent cost; Owner export optional only.
- W17 spot-check: `QFSI_007_HEALTHY` hb_alive=True proc_alive=True pid=72320 @ 2026-07-15T10:33:22.202672Z
