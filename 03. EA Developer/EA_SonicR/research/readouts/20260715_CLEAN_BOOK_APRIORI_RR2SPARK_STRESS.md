# CLEAN BOOK — offline a priori +$12 stress

Hypothesis: `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`  
Date: 2026-07-15 13:10:32 ICT  
Status: `DIAGNOSTIC_OFFLINE_CLEAN_BOOK__NOT_PHASE0`  
Result SHA256: `5630D1DB90EB9C2E09A1CCF6D3A271B97B4746C760F3AEB14A430D7D4ABADA0E`  
Freeze: `20260715_CLEAN_BOOK_APRIORI_UNIVERSE_FREEZE.md` (SHA `F18FAB12ECCBD3FF…`)

## Exclusions (a priori; pre-metrics)

- MaxKZ2 `20260714_192304` — `MAXKZ2_REAL_PATH_FAIL_CLOSED`
- Spark twin `20260714_193732` — shelf names `193358`

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


## Model 0

`WITHHELD_BOOK_LEVEL_OFFLINE_NOT_EA_CHALLENGER` — book pooling of tester trades
is not an EA Model 0 matched challenger. No portfolio EA coded this session.

## Non-claims

Not Phase-0 clearance (attestation still CONTAMINATED). Not confirmed. Not GOAL.
Tester +$12 proxy ≠ QFSI. No sleeve cherry-pick after seeing these numbers.

## Freeze immutability

Freeze memo SHA must remain `F18FAB12ECCBD3FF09A4FA03317AB13A59DFCAE00BA9491B640D69D2B728931C`.
Do not edit `20260715_CLEAN_BOOK_APRIORI_UNIVERSE_FREEZE.md` after this binding.
