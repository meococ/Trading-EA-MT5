# Offline probes — Round 13 event / CUSUM / XAU-mom

Generated: 2026-07-15 ~13:19 ICT
Receipt SHA256: `3D638ABC311BDEF6D3CC2E7113FE41431355EAA4D4484D20735BED4CD9649721`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T06:18:59.663021Z alive=True cap_pid=72320 wall_rem=258312; 007 accumulate hb=3480 quotes=2563 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-NFP-IMPULSE-CONT-001` | 59 | 0.5301 | 0.2263 | 0.4995 | KILL |
| `HYP-FX3-H1-CUSUM-BREAK-PERSIST-001` | 776 | 1.1293 | 2.9764 | 1.0515 | KILL |
| `HYP-XAUUSD-H4-D1-TSMOM-THICK-001` | 78 | 1.4331 | 0.2992 | 1.1341 | KILL |

## Fail notes
- `HYP-FX3-H1-NFP-IMPULSE-CONT-001`: n_fail, pf_fail, cadence_fail, stress_fail
- `HYP-FX3-H1-CUSUM-BREAK-PERSIST-001`: pf_fail, stress_fail
- `HYP-XAUUSD-H4-D1-TSMOM-THICK-001`: n_fail, cadence_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
