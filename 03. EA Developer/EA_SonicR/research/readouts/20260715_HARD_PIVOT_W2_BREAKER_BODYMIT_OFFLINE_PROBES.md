# Offline probes — HARD PIVOT W2 breaker + body-mitigation

Generated: 2026-07-15 ~14:29 ICT
Receipt SHA256: `F9B52AAAFE0A981431BA02DF91D8BB409E473F81BC2642D516080142B8ED844D`
Freeze SHA256: `11D25A7AFB478C6F46151EC2A5CB85A38A606AB7C110BAC1ECD745F3009E39DA`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: QFSI 007 parallel accumulate; cost freeze still GAP (raw_deals≈11; freeze_eligible=False); login not headline

| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001` | 2096 | 1.1131 | 8.0395 | 1.0599 | 1.0345 | KILL |
| `HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001` | 785 | 1.0306 | 3.011 | 0.9772 | 0.9517 | KILL |

## Fail notes
- `HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001`: pf_fail, cadence_fail, pf12_fail, stress_fail
- `HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001`: pf_fail, pf12_fail, stress_fail, no_lift_vs_rr2_pf12, no_lift_vs_rr2_x15

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
Do **not** densify FVG / auction / breaker / body-mit knobs from readout.
