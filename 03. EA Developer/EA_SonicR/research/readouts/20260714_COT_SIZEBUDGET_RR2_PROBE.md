# COT Size-Budget RR2 Probe Readout

**Hypothesis:** `HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001`
**Verdict:** `KILLED_AT_OFFLINE_PROBE`
**Notes:** ['stress_fail']

## Semantics
SIZE BUDGET (scale risk/PnL). Keep all RR2 trades. No skip-by-z.

## Metrics

| Set | N | PF | TPW | Net | x1 PF | x1.5 PF | x2 PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 524 | 1.3794 | 2.0099 | 9851.14 | 1.1205 | 1.0134 | 0.9179 |
| Sized | 524 | 1.4134 | 2.0099 | 6884.27 | 1.1509 | 1.0421 | 0.945 |

Stress lift (sized x1.5 − baseline x1.5): `0.0287`
Size mult histogram: `{'0.50': 313, '0.67': 97, '1.00': 114}`
Missing crowd (fail-open size=1.0): `0`
Panel SHA: `93D69F957A503B38C729F41D2E6B6D714A25EB330147383867C65A5EFC19AE54`
Receipt SHA: `ED98F1FAD2A2E38E2726F9C636C913790EE79E362BD8FD514E3ED9DB477470B7`

A priori thresholds frozen in probe script; not mined from this readout.
