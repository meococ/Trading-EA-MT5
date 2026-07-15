# Readout — HYP-SPARK-CAPACITY-3PD-001 Model 0

Date: 2026-07-14  
Status: `PARKED` / GOAL unmet  
Parent: `HYP-SPARK-ASIAN-M15-001`

## Thesis test

Raise `InpMaxPerDay` 2→3 only (Tue–Wed unchanged). Expect more second-break
fills without Mon/Thu densify (banned S223).

## Runs

| Role | run_id | Deposit | Overrides | N | tpw | PF | Net | DD% |
|---|---|---:|---|---:|---:|---:|---:|---:|
| Control (parked) | `20260714_002821` | 10000 | defaults MaxPerDay=2 | 325 | 1.25 | 1.31 | 1099 | ~3.2 |
| Capital twin (defaults) | `20260714_193358` | 100000 | none | 325 | 1.25 | **1.38** | 9351 | 1.78 |
| Challenger capacity | `20260714_193732` | 100000 | `InpMaxPerDay=3` | **327** | **1.25** | **1.37** | 9184 | 1.79 |

Elapsed weeks: 260.7143. Tester `current` only. Cost grade
`UNVERIFIED_TESTER_DEFAULT`.

## Verdict

- Kill screen: **PASS** (PF≥1.00, N≥80, tpw∈[1.0,6.0]).
- Research HIT bar PF>1.30 ∧ tpw∈[2.0,5.0]: **FAIL** (cadence still ~1.25).
- Capacity effect vs capital twin: **+2 trades / PF −0.01** → **null**.
  MaxPerDay is not the binding constraint; days rarely hit the old cap of 2.
- Decision: **PARK**. Do **not** raise MaxPerDay further. Do **not** enable
  Mon/Thu/Fri from this readout.

## Cost stress (report-only, base $12/trade extra)

Artifact:
`02. AlphaFactory/runs/EA_M15SparkAsian/20260714_193732/analysis/sonic_cost_stress_report_only_1200.json`

| Scenario | PF | Net |
|---|---:|---:|
| base_report | 1.370 | +9184 |
| cost x1.5 ($18) | 1.120 | +3298 |
| cost x2 ($24) | 1.047 | +1336 |

Fails GOAL x1.5 PF≥1.25; x2 PF≥1.00 passes on this proxy only. Not Real QFSI.

## Explicit non-rescues

No Mon–Thu expansion. No hour-11 mine (weakness tag is post-hoc). No body/ATR
retune.
