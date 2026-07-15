# Offline probes — Round 29 Equal-HL / OPEX / One-slot

Generated: 2026-07-15 ~14:12 ICT
Receipt SHA256: `4DCC400EA3A2E5CA7A735C31E29AB7F097B4036976381FCF09E3FC7204D28885`
Freeze SHA256: `50FF0546E011289FD448547F0503DF57C2FB645933799EDE66AD0A4AB93C4BDF`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T07:12:16.478579Z alive=True cap_pid=72320 wall_rem=255115; 007 accumulate hb=15840 quotes=12502 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline
Cost track: autonomous live import `IMPORTED_LIVE_HISTORY_PARTIAL` raw_deals=11 comm EURUSD=2/30 USDJPY=0/30 slip=0 MISSING≠0; multiday_table quote_days=2/90 freeze_eligible=False; R29 retry history_deals_get raw_deals=11 comm_unique={'BTCUSD': 3, 'EURUSD': 2}; freeze_eligible=False

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-EQUAL-HL-BREAK-CONT-001` | 3566 | 1.0064 | 13.6778 | 0.9458 | KILL |
| `HYP-USDJPY-H1-OPEX-FRIDAY-CONT-001` | 76 | 1.3487 | 0.2915 | 1.2578 | KILL |
| `HYP-FX3-H1-ONESLOT-BOOK-ARCH-CONT-001` | 1299 | 0.8045 | 4.9825 | 0.7447 | KILL |

## Fail notes
- `HYP-FX3-H1-EQUAL-HL-BREAK-CONT-001`: pf_fail, stress_fail
- `HYP-USDJPY-H1-OPEX-FRIDAY-CONT-001`: n_fail, cadence_fail
- `HYP-FX3-H1-ONESLOT-BOOK-ARCH-CONT-001`: pf_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
