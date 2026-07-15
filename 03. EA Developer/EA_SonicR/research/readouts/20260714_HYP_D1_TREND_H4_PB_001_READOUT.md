# Readout — HYP-D1-TREND-H4-PB-001 Model 0

Date: 2026-07-14 ~20:22 ICT  
EA: `EA_D1TrendH4PB`  
Run: `20260714_202048`  
Verdict: `PARK_WEAK_EDGE`

## Metrics (USDJPY H4 2021–2025, Deposit=100000, Model 0)

| Metric | Value |
|---|---:|
| Trades | **285** |
| PF | **1.11** |
| Net | +$5863 |
| Expectancy | +$20.57/trade |
| tpw (elapsed) | **~1.09** |
| Max DD | ~5.15% |

Cost: `UNVERIFIED_TESTER_DEFAULT`. Alpha `includes_sha256` closeout flake; artifacts kept.

## Gate

| Gate | Result |
|---|---|
| PF ≥ 1.00 | PASS |
| N ≥ 80 | PASS |
| tpw ∈ [1,6] | PASS (~1.09) |
| Research HIT | **FAIL** |
| Cost-stress | skipped |

## Non-repaint

Closed D1[1] EMA50 bias + closed H4[1] EMA20 reclaim — PASS by design.

## Banned

No EMA period / day / hour mine. Not H1-ATR-mom or EMA-stretch fade rescue.
