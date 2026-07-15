# Offline probes — Round 25 RangeP80 / H4-engulf / VWAP

Generated: 2026-07-15 ~14:03 ICT
Receipt SHA256: `BE1AAE2C0DDA91CA534F8D36ED3C896A93360696BDF4DC89F7F5CC2D8D9940D3`
Freeze SHA256: `EAA8606A61B8C0E93BAD33DB45D80B5A7D7103C132743D8DD0402AC9242F1060`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T07:03:21.090478Z alive=True cap_pid=72320 wall_rem=255650; 007 accumulate hb=13740 quotes=10792 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline
Cost track: autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; freeze_eligible=False

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-RANGE-P80-EXPAND-CONT-001` | 3783 | 1.0517 | 14.5101 | 0.9874 | KILL |
| `HYP-USDJPY-H4-ENGULF-CONT-001` | 764 | 1.2409 | 2.9304 | 1.1578 | KILL |
| `HYP-GBPUSD-H1-LONDON-VWAP-RECLAIM-CONT-001` | 1297 | 0.8783 | 4.9748 | 0.8309 | KILL |

## Fail notes
- `HYP-FX3-H1-RANGE-P80-EXPAND-CONT-001`: pf_fail, stress_fail
- `HYP-USDJPY-H4-ENGULF-CONT-001`: pf_fail, stress_fail
- `HYP-GBPUSD-H1-LONDON-VWAP-RECLAIM-CONT-001`: pf_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
