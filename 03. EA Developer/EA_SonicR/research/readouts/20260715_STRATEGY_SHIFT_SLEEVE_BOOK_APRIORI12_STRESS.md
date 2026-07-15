# STRATEGY SHIFT — Track A offline a priori +$12 sleeve stress

Date: 2026-07-15 13:03:56 ICT  
Status: `DIAGNOSTIC_OFFLINE_NOT_PHASE0`  
Result SHA256: `B2286CB3C3BBDE52C9ED5FE530AA5BFD45C6983124276FCF198A1CD1D2593254`  
Freeze: `20260715_STRATEGY_SHIFT_PHASE0_SLEEVE_UNIVERSE_FREEZE.md` (SHA `9707ABE2B95D8D33…`)

## Exclusions (a priori; pre-metrics)

- MaxKZ2 `20260714_192304` — `MAXKZ2_REAL_PATH_FAIL_CLOSED`
- Spark twin `20260714_193732` — Phase-0 named `193358`

## Results

### PRIMARY_BOOK

| Sleeve | run_id | N | PF raw | PF @$12 | tpw |
|---|---|---:|---:|---:|---:|
| A_RR2 | `20260714_194548` | 524 | 1.3783 | 1.1197 | 2.010 |
| B_SPARK | `20260714_193358` | 325 | 1.3804 | 1.2071 | 1.247 |

- Pooled N (after heat): **845** (dropped 4)
- Pooled PF @$12: **1.1841**
- Pooled tpw: **3.241**
- Caps pass: **True** (corr_fail=False, overlap_fail=False)
- Verdict: `DIAGNOSTIC_PARTIAL__CAPS_OK__GOAL_SCREEN_FAIL`

Pair caps:

| Pair | weekly corr | overlap frac |
|---|---:|---:|
| A_RR2×B_SPARK | 0.0307 | 0.0000 |

### EXTENDED_BOOK

| Sleeve | run_id | N | PF raw | PF @$12 | tpw |
|---|---|---:|---:|---:|---:|
| A_RR2 | `20260714_194548` | 524 | 1.3783 | 1.1197 | 2.010 |
| B_SPARK | `20260714_193358` | 325 | 1.3804 | 1.2071 | 1.247 |
| C_ITSM | `20260714_003920` | 852 | 1.1567 | 0.7985 | 3.268 |

- Pooled N (after heat): **1664** (dropped 37)
- Pooled PF @$12: **1.0435**
- Pooled tpw: **6.382**
- Caps pass: **True** (corr_fail=False, overlap_fail=False)
- Verdict: `DIAGNOSTIC_FAIL_GOAL_SCREEN`

Pair caps:

| Pair | weekly corr | overlap frac |
|---|---:|---:|
| A_RR2×B_SPARK | 0.0307 | 0.0000 |
| A_RR2×C_ITSM | 0.1457 | 0.0000 |
| B_SPARK×C_ITSM | 0.1454 | 0.0000 |


## Non-claims

Not Phase-0 clearance. Not confirmed. Not GOAL. No Model 0. Tester +$12 proxy ≠ QFSI.
No sleeve cherry-pick after seeing these numbers.
