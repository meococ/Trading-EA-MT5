# Offline probes — Round 26 Heikin / Keltner / Supertrend

Generated: 2026-07-15 ~14:06 ICT
Receipt SHA256: `79F64DA0C028D3B6DA29F9FAE8CBEBCA634D8BD8E155895531C22DD9F3765A66`
Freeze SHA256: `7E3A4DE650EB83A2AC27A60EE5442C08ED91913182AA98DF3C5207C101A8904A`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T07:06:24.437351Z alive=True cap_pid=72320 wall_rem=255467; 007 accumulate hb=14460 quotes=11418 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline
Cost track: autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R26 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-HEIKIN-STREAK-CONT-001` | 3826 | 1.0347 | 14.6751 | 0.9685 | KILL |
| `HYP-EURUSD-H1-KELTNER-WALK-CONT-001` | 807 | 1.0591 | 3.0953 | 0.9913 | KILL |
| `HYP-USDJPY-H1-SUPERTREND-FLIP-CONT-001` | 626 | 1.0971 | 2.4011 | 1.0237 | KILL |

## Fail notes
- `HYP-FX3-H1-HEIKIN-STREAK-CONT-001`: pf_fail, stress_fail
- `HYP-EURUSD-H1-KELTNER-WALK-CONT-001`: pf_fail, stress_fail
- `HYP-USDJPY-H1-SUPERTREND-FLIP-CONT-001`: pf_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
