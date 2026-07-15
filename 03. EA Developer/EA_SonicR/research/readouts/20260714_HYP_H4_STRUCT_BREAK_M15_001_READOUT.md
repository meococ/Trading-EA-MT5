# Readout — HYP-H4-STRUCT-BREAK-M15-001 Model 0

Date: 2026-07-14 ~20:10 ICT  
EA: `EA_H4StructBreak_M15`  
Run: `20260714_200944`  
Verdict: `KILLED_AT_MODEL_0`

## Metrics (USDJPY M15 2021–2025, Deposit=100000, Model 0)

| Metric | Value |
|---|---:|
| Trades | 817 |
| PF | **0.91** |
| Net | −$5934 |
| Expectancy | −$7.26 |
| tpw (elapsed) | ~3.13 |
| Max DD | ~10.2% |

Cost: `UNVERIFIED_TESTER_DEFAULT`. Alpha `includes_sha256` flake after report ready; artifacts kept.

## Gate

| Gate | Result |
|---|---|
| PF ≥ 1.00 | **FAIL** |
| tpw ∈ [1,6] | PASS |
| N ≥ 80 | PASS |
| Research HIT | FAIL |
| Cost-stress | Skipped |

## Independence note

H4 swing BOS + M15 acceptance — not H1-BOS EMA pullback densify. Cadence OK; edge fails.

## Banned

No SwingL / hour / Asia-session mine from this readout (Asia heavy but post-hoc veto banned).
