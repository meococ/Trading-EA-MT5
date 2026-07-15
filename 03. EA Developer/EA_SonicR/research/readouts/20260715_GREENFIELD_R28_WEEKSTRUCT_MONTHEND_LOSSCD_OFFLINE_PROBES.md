# Offline probes — Round 28 Week-struct / Month-end / Loss-CD

Generated: 2026-07-15 ~14:10 ICT
Receipt SHA256: `C9EA5C7345FB2ED0CA097E2DA877BBD59923A70134F00901F1F1EC5E48F5E733`
Freeze SHA256: `70BC7D16A56CB86B4405D2D2421B8320E42D0971C3CE3262E41705E3C5C4CC29`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T07:10:28.766498Z alive=True cap_pid=72320 wall_rem=255223; 007 accumulate hb=15420 quotes=12166 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline
Cost track: autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R28 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-PRIOR-WEEK-HL-BREAK-CONT-001` | 696 | 1.0955 | 2.6696 | 1.025 | KILL |
| `HYP-EURUSD-H1-MONTHEND-REBAL-CONT-001` | 236 | 0.8552 | 0.9052 | 0.7933 | KILL |
| `HYP-FX3-H1-LOSS-COOLDOWN-ARCH-CONT-001` | 3528 | 0.9636 | 13.5321 | 0.8994 | KILL |

## Fail notes
- `HYP-FX3-H1-PRIOR-WEEK-HL-BREAK-CONT-001`: pf_fail, stress_fail
- `HYP-EURUSD-H1-MONTHEND-REBAL-CONT-001`: pf_fail, cadence_fail, stress_fail
- `HYP-FX3-H1-LOSS-COOLDOWN-ARCH-CONT-001`: pf_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
