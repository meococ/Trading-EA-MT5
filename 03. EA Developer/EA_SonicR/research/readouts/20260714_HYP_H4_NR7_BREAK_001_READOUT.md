# Readout — HYP-H4-NR7-BREAK-001 Model 0

Date: 2026-07-14 ~20:20 ICT  
EA: `EA_H4NR7Break`  
Run: `20260714_201923`  
Verdict: `PARK_NEAR_MISS_RESEARCH_BAR`

## Metrics (USDJPY H4 2021–2025, Deposit=100000, Model 0)

| Metric | Value |
|---|---:|
| Trades | **378** |
| PF | **1.28** |
| Net | +$18761 |
| Expectancy | **+$49.63**/trade |
| tpw (elapsed) | **~1.45** |
| Max DD | ~7.62% |

Cost: `UNVERIFIED_TESTER_DEFAULT`. Alpha `includes_sha256` closeout flake after report ready; artifacts kept.

## Gate

| Gate | Result |
|---|---|
| PF ≥ 1.00 | PASS |
| N ≥ 80 | PASS |
| tpw ∈ [1,6] | PASS (~1.45) |
| Research HIT PF>1.30 ∧ 2–5/wk | **FAIL** (PF 1.28; tpw 1.45) |
| Cost-stress x1.5/x2 | skipped (not HIT) |

## Non-repaint

Closed-bar[1] NR7 on bar[2] + breakout close on bar[1] — PASS by design.

## Banned

No NR-length / RR / day / hour mine from this readout. Not VolExp/Keltner rescue.
