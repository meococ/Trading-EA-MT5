# Offline probes — Round 30 Day-Open / IMM / SameDir-Cap2

Generated: 2026-07-15 ~14:15 ICT
Receipt SHA256: `DD7FE049B2D3B35F19C21F3649B99F3C750F747BE5647C463FFAD6866522F635`
Freeze SHA256: `562C452F380A33038FA91EC587B434947570C2553E76DA90E6F435764A4F3347`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T07:15:35.157419Z alive=True cap_pid=72320 wall_rem=254916; 007 accumulate hb=16560 quotes=13098 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline
Cost track: autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R30 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-PRIOR-DAY-OPEN-BREAK-CONT-001` | 1579 | 1.0011 | 6.0564 | 0.9373 | KILL |
| `HYP-EURUSD-H1-IMM-WEDNESDAY-CONT-001` | 27 | 1.0405 | 0.1036 | 0.9592 | KILL |
| `HYP-FX3-H1-SAMEDIR-CAP2-ARCH-CONT-001` | 3896 | 0.9393 | 14.9436 | 0.8748 | KILL |

## Fail notes
- `HYP-FX3-H1-PRIOR-DAY-OPEN-BREAK-CONT-001`: pf_fail, stress_fail
- `HYP-EURUSD-H1-IMM-WEDNESDAY-CONT-001`: n_fail, pf_fail, cadence_fail, stress_fail
- `HYP-FX3-H1-SAMEDIR-CAP2-ARCH-CONT-001`: pf_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
