# Offline probes — Round 31 Outside / FirstDOM / TimeStop-CD

Generated: 2026-07-15 ~14:17 ICT
Receipt SHA256: `AAD9BA4043042D994B02AD9B1638C103C4FEE02000FEDC4232E8091D02527343`
Freeze SHA256: `18DF2BC4645E5DC9751C719DE0F0B22AC0CB49EF3EC24744246E30446C138BE1`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T07:17:52.726794Z alive=True cap_pid=72320 wall_rem=254779; 007 accumulate hb=17100 quotes=13475 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline
Cost track: autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R31 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-OUTSIDE-BAR-CONT-001` | 3278 | 0.9626 | 12.5732 | 0.9034 | KILL |
| `HYP-GBPUSD-H1-FIRST-DOM-CONT-001` | 17 | 0.3147 | 0.0652 | 0.2883 | KILL |
| `HYP-FX3-H1-POST-TIMESTOP-CD-ARCH-CONT-001` | 3896 | 0.9466 | 14.9436 | 0.881 | KILL |

## Fail notes
- `HYP-FX3-H1-OUTSIDE-BAR-CONT-001`: pf_fail, stress_fail
- `HYP-GBPUSD-H1-FIRST-DOM-CONT-001`: n_fail, pf_fail, cadence_fail, stress_fail
- `HYP-FX3-H1-POST-TIMESTOP-CD-ARCH-CONT-001`: pf_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
