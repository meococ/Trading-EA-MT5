# HARD PIVOT W18 offline probes — `OFFLINE_ALL_KILL__NO_MODEL0`

Receipt `09662DB35C2E113E4995AAF53F41975854F043005D1F2B2F2CD0433B98283DDE`
QFSI spot-check: `QFSI_007_HEALTHY`; cost freeze GAP; login not headline

| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-FX3-H1-ADR-COMPLETE-NY-FADE-001` | 241 | 1.1051 | 0.9244 | 1.0609 | 1.0396 | KILL |
| `HYP-FX3-H1-IMPULSE-DECAY-REVERSE-001` | 804 | 1.0604 | 3.0838 | 1.0238 | 1.0061 | KILL |
| `HYP-BOOK-ADRFADE-IMPULSEDECAY-APRIORI-001` | 1027 | 1.0678 | 3.9392 | 1.0297 | 1.0113 | KILL |

- Caps book: corr=0.0177 overlap=0.045 ok=True
- Model 0: WITHHELD (no survivor)

## Cost grade
- QFSI 007: watcher_alive=True cap_pid=72320 quotes=45557 hb=60000 tick_err=0
- quote_days=2/90 (gap=88); raw_deals=11; freeze_eligible=False
- commission unique days: {'EURUSD': '2/30', 'GBPUSD': '0/30', 'USDJPY': '0/30', 'XAUUSD': '0/30', 'BTCUSD': '3/30'}
- slip: MISSING_NE_0 — QFSI accumulate may grow fill rows but research freeze still needs verified side/ref/fill sample
- verdict: `COST_FREEZE_STILL_GAP__DEALS_STILL_~11__QUOTE_DAYS_CALENDAR_BOUND`
- Autonomous remaining: keep QFSI alive (calendar-bound days); retry deals (still ~11=exhausted); do NOT invent cost; Owner export optional only.
- W18 spot-check: `QFSI_007_HEALTHY` hb_alive=True proc_alive=True pid=72320 @ 2026-07-15T10:36:12.570644Z
