# Offline probes — Round 16 HL-break / CPI / US30-lead

Generated: 2026-07-15 ~13:27 ICT
Receipt SHA256: `10169CA6ED75319D1616ECAA901D77F3A53FC275056E060730F3D6D4B534E77A`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T06:26:54.057173Z alive=True cap_pid=72320 wall_rem=257837; 007 accumulate hb=5340 quotes=3927 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-US30-H4-D1-HL-BREAK-CONT-001` | 37 | 1.1296 | 0.1419 | 1.0608 | KILL |
| `HYP-USDJPY-H1-CPI-IMPULSE-CONT-001` | 7 | 0.393 | 0.0268 | 0.3701 | KILL |
| `HYP-EURJPY-H1-US30-LEAD-CONT-001` | 1289 | 1.0893 | 4.9441 | 1.0204 | KILL |

## Fail notes
- `HYP-US30-H4-D1-HL-BREAK-CONT-001`: n_fail, pf_fail, cadence_fail, stress_fail
- `HYP-USDJPY-H1-CPI-IMPULSE-CONT-001`: n_fail, pf_fail, cadence_fail, stress_fail
- `HYP-EURJPY-H1-US30-LEAD-CONT-001`: pf_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
