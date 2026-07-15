# Offline probes — Round 14 gap-cont / tvol / NAS-mom

Generated: 2026-07-15 ~13:21 ICT
Receipt SHA256: `CA59FCB51E833DCD65240DD19283C0EB8BEFF9391FEAF09B3282776FD1823E78`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T06:20:46.873306Z alive=True cap_pid=72320 wall_rem=258205; 007 accumulate hb=3900 quotes=2865 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-WEEKEND-GAP-CONT-001` | 34 | 0.3858 | 0.1304 | 0.36 | KILL |
| `HYP-FX3-H1-TICKVOL-IMBALANCE-CONT-001` | 1243 | 0.956 | 4.7677 | 0.8916 | KILL |
| `HYP-NAS100-H4-D1-TSMOM-THICK-001` | 88 | 1.2069 | 0.3375 | 1.1406 | KILL |

## Fail notes
- `HYP-FX3-H1-WEEKEND-GAP-CONT-001`: n_fail, pf_fail, cadence_fail, stress_fail
- `HYP-FX3-H1-TICKVOL-IMBALANCE-CONT-001`: pf_fail, stress_fail
- `HYP-NAS100-H4-D1-TSMOM-THICK-001`: pf_fail, cadence_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
