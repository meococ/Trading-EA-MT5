# Readout — HYP-WEEKLY-HL-BREAK-H4-001 Model 0

Date: 2026-07-14 ~20:23 ICT  
EA: `EA_WeeklyHLBreak_H4`  
Run: `20260714_202237`  
Verdict: `KILLED_AT_MODEL_0` (cadence)

## Metrics (USDJPY H4 2021–2025, Deposit=100000, Model 0)

| Metric | Value |
|---|---:|
| Trades | **208** |
| PF | **1.10** |
| Net | +$4676 |
| Expectancy | +$22.48/trade |
| tpw (elapsed) | **~0.80** |
| Max DD | ~5.60% |

Cost: `UNVERIFIED_TESTER_DEFAULT`. Alpha `includes_sha256` closeout flake; artifacts kept.

## Gate

| Gate | Result |
|---|---|
| PF ≥ 1.00 | PASS |
| N ≥ 80 | PASS |
| tpw ∈ [1,6] | **FAIL** (~0.80) |
| Research HIT | **FAIL** |
| Cost-stress | skipped |

## Non-repaint

Prior W1[1] HL + first closed H4 beyond with prior bar inside — PASS by design.

## Banned

No multi-symbol densify from this kill readout; no day/session mine (Europe PF 0.82 is post-hoc). Not PDH rescue.
