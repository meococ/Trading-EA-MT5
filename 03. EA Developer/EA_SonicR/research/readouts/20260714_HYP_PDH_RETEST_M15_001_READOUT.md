# Readout — HYP-PDH-RETEST-M15-001 Model 0

Date: 2026-07-14 ~20:09 ICT  
EA: `EA_M15PDHRetest`  
Run: `20260714_200819`  
Verdict: `KILLED_AT_MODEL_0`

## Metrics (USDJPY M15 2021–2025, Deposit=100000, Model 0)

| Metric | Value |
|---|---:|
| Trades | 279 |
| PF | **0.83** |
| Net | −$2173 |
| Expectancy | −$7.79 |
| tpw (elapsed) | ~1.07 |
| Max DD | ~3.48% |

Cost: `UNVERIFIED_TESTER_DEFAULT`. Alpha `includes_sha256` closeout flake after report ready; artifacts kept.

## Gate

| Gate | Result |
|---|---|
| PF ≥ 1.00 | **FAIL** |
| tpw ∈ [1,6] | PASS (~1.07) |
| N ≥ 80 | PASS |
| Research HIT PF>1.30 ∧ 2–5/wk | FAIL |
| Cost-stress | Skipped (no HIT) |

## Independence note

Not a PDH-BREAK retune: break-arm then later retest+reject. Edge falsified.

## Banned

No buffer/body/retest ATR mining; no day/hour veto; no fade flip.
