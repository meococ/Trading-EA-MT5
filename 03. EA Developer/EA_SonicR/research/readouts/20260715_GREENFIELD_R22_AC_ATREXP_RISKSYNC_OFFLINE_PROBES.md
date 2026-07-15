# Offline probes — Round 22 AC / ATR-exp / FX3-risksync

Generated: 2026-07-15 ~13:52 ICT
Receipt SHA256: `B1FB8A0794AA0216C39B1EDB79EF461D2C204ACE72549A70B19917035AFC784D`
Freeze SHA256: `77E558AD57F671F187E1760001FF15EC93162D379BA51113C4CB373DD175844C`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T06:52:39.869428Z alive=True cap_pid=72320 wall_rem=256292; 007 accumulate hb=11280 quotes=8577 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-LAG1AC-REGIME-BODY-CONT-001` | 1793 | 1.0754 | 6.8773 | 1.0045 | KILL |
| `HYP-GBPUSD-H1-ATREXP-BURST-CONT-001` | 372 | 0.9309 | 1.4268 | 0.8382 | KILL |
| `HYP-AUDUSD-H1-FX3-RISKSYNC-CONT-001` | 1285 | 0.9602 | 4.9288 | 0.8987 | KILL |

## Fail notes
- `HYP-FX3-H1-LAG1AC-REGIME-BODY-CONT-001`: pf_fail, stress_fail
- `HYP-GBPUSD-H1-ATREXP-BURST-CONT-001`: pf_fail, cadence_fail, stress_fail
- `HYP-AUDUSD-H1-FX3-RISKSYNC-CONT-001`: pf_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
