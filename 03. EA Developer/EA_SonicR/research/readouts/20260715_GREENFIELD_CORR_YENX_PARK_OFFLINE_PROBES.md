# Offline probes — Round 8 corr / yen-cross / Parkinson

Generated: 2026-07-15 ~12:57 ICT
Receipt SHA256: `E6A2A2090F64C63E18F9CE2EA37599AD1C0F6C3EB466CF4902042365A9774ADF`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: 007 accumulate hb=9480 quotes=6586 deadline=2026-07-15T07:39:26.186865Z; cost freeze still GAP; login not headline.

| Object | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-EURJPY-H1-USDJPY-BETA-RESID-FADE-001` | 134 | 0.8521 | 0.514 | 0.8043 | KILL |
| `HYP-EURGBP-H1-CORR-BREAK-RECOUPLE-001` | 15 | 0.448 | 0.0575 | 0.423 | KILL |
| `HYP-FX3-H1-PARKINSON-COMPRESS-EXPAND-CONT-001` | 229 | 0.8419 | 0.8784 | 0.7937 | KILL |

## Fail notes
- `HYP-EURJPY-H1-USDJPY-BETA-RESID-FADE-001`: pf_fail, cadence_fail, stress_fail
- `HYP-EURGBP-H1-CORR-BREAK-RECOUPLE-001`: n_fail, pf_fail, cadence_fail, stress_fail
- `HYP-FX3-H1-PARKINSON-COMPRESS-EXPAND-CONT-001`: pf_fail, cadence_fail, stress_fail

## Beta freeze (EURJPY ~ USDJPY)
- α=3.81949e-06 β=0.643058 n=12421 R²=0.359421

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
