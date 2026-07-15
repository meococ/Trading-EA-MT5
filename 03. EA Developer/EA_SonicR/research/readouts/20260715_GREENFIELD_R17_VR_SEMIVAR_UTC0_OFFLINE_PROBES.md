# Offline probes — Round 17 VR / semivar / UTC0

Generated: 2026-07-15 ~13:30 ICT
Receipt SHA256: `90304CEAA0C0CCBDEFE63C61A552F49A8DF950C703E0F3EC948DCCF794D79BAD`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T06:29:57.417142Z alive=True cap_pid=72320 wall_rem=257654; 007 accumulate hb=6000 quotes=4401 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-ETHUSD-H4-VARIANCE-RATIO-MOM-CONT-001` | 87 | 1.9779 | 0.3337 | 1.7749 | KILL |
| `HYP-NZDUSD-H1-SIGNED-SEMIVAR-CONT-001` | 1286 | 0.9662 | 4.9326 | 0.9036 | KILL |
| `HYP-ETHUSD-H1-UTC0-OPEN-DRIVE-CONT-001` | 223 | 0.8937 | 0.8553 | 0.7277 | KILL |

## Fail notes
- `HYP-ETHUSD-H4-VARIANCE-RATIO-MOM-CONT-001`: cadence_fail
- `HYP-NZDUSD-H1-SIGNED-SEMIVAR-CONT-001`: pf_fail, stress_fail
- `HYP-ETHUSD-H1-UTC0-OPEN-DRIVE-CONT-001`: pf_fail, cadence_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
