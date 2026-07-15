# Offline probes — Round 27 Marubozu / Ichimoku / ROC

Generated: 2026-07-15 ~14:07 ICT
Receipt SHA256: `2B11B74AF40066A9D78649B54836442EAB135DE4D9EAEAC741354727BFB0F8C0`
Freeze SHA256: `22740ADE82A25A813324925645667A8D16A94D56C4330432A8F5B0B87ED6FF93`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T07:07:40.818363Z alive=True cap_pid=72320 wall_rem=255391; 007 accumulate hb=14760 quotes=11650 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline
Cost track: autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R27 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-MARUBOZU-CONT-001` | 3846 | 0.9624 | 14.7518 | 0.8996 | KILL |
| `HYP-GBPUSD-H1-ICHIMOKU-TK-CONT-001` | 472 | 0.9292 | 1.8104 | 0.868 | KILL |
| `HYP-USDJPY-H1-ROC-BAND-CONT-001` | 1257 | 1.0795 | 4.8214 | 1.006 | KILL |

## Fail notes
- `HYP-FX3-H1-MARUBOZU-CONT-001`: pf_fail, stress_fail
- `HYP-GBPUSD-H1-ICHIMOKU-TK-CONT-001`: pf_fail, cadence_fail, stress_fail
- `HYP-USDJPY-H1-ROC-BAND-CONT-001`: pf_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
