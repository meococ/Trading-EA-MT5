# Offline probes — Round 11 fix / weekly-open / closeloc

Generated: 2026-07-15 ~13:14 ICT
Receipt SHA256: `997D65CD46FA1534ACD90F373A060261A5BE5F0A27C60F5D4EEC1D4115FF87C1`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: watcher_hb ts=2026-07-15T06:14:08.948862Z alive=True cap_pid=72320 wall_rem=258603; 007 accumulate hb=2340 quotes=1724 deadline=2026-07-15T12:04:12.715855Z; cost freeze still GAP; login not headline

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-LONDON-FIX-REVERSION-001` | 773 | 0.9854 | 2.9649 | 0.9179 | KILL |
| `HYP-FX3-H1-WEEKLY-OPEN-DIST-FADE-001` | 261 | 0.9517 | 1.0011 | 0.8857 | KILL |
| `HYP-FX3-H1-CLOSELOC-PRESSURE-CONT-001` | 2600 | 0.9541 | 9.9726 | 0.8922 | KILL |

## Fail notes
- `HYP-FX3-H1-LONDON-FIX-REVERSION-001`: pf_fail, stress_fail
- `HYP-FX3-H1-WEEKLY-OPEN-DIST-FADE-001`: pf_fail, cadence_fail, stress_fail
- `HYP-FX3-H1-CLOSELOC-PRESSURE-CONT-001`: pf_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
