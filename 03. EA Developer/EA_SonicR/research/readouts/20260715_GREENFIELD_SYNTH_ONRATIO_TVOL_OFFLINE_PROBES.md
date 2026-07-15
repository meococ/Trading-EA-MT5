# Offline probes — Round 9 yen-synth / ON-ratio / tickvol

Generated: 2026-07-15 ~12:59 ICT
Receipt SHA256: `848848D26CC00D234F694B4342F6D1E3846C66B422A8EEEDF56995204C972744`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: 007 accumulate hb=9480 quotes=6586 deadline=2026-07-15T07:39:26.186865Z; cost freeze still GAP; login not headline.

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-EURUSD-H1-YENCROSS-SYNTH-RESID-FADE-001` | 13 | 1.874 | 0.0499 | 1.7676 | KILL |
| `HYP-FX3-H1-OVERNIGHT-RATIO-CONT-001` | 1159 | 0.8705 | 4.4455 | 0.8216 | KILL |
| `HYP-FX3-H1-TICKVOL-CLIMAX-FADE-001` | 15 | 0.9998 | 0.0575 | 0.9417 | KILL |

## Fail notes
- `HYP-EURUSD-H1-YENCROSS-SYNTH-RESID-FADE-001`: n_fail, cadence_fail
- `HYP-FX3-H1-OVERNIGHT-RATIO-CONT-001`: pf_fail, stress_fail
- `HYP-FX3-H1-TICKVOL-CLIMAX-FADE-001`: n_fail, pf_fail, cadence_fail, stress_fail

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
