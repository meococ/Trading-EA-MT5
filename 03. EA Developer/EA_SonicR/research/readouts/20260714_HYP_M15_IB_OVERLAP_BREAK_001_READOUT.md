# Readout — HYP-M15-IB-OVERLAP-BREAK-001

Date: 2026-07-14  
Authoritative run: `20260714_223618`  
EA: `EA_M15IBOverlapBreak`  
Verdict: **`PARKED`** (weak PF; cadence OK; cost-stress FAIL)

## Metrics (tester `current`, deposit 100000)

| Metric | Value |
|---|---|
| Trades | **987** |
| PF | **1.05** |
| Net | +$5582.77 |
| Expectancy | +$5.66/trade |
| tpw elapsed | **~3.79**/wk |

Report SHA256: see `preflight/20260714_WAVE4_REPORT_SHA.json`.

## Gates

| Gate | Result |
|---|---|
| Kill PF&lt;1.00 / tpw∉[1,6] / N&lt;80 | PASS |
| Research HIT PF&gt;1.30 ∧ tpw∈[2,5] | **FAIL** (PF 1.05) |
| A priori +$12 cost-stress (diag; PF&lt;1.20) | x1 **0.94** / x1.5 **0.89** / x2 **0.84** → **FAIL** |

## Non-repaint

Closed M15 bar[1]; IB locked after hour-07 auction; overlap break hours [13,16).

## Ban

Do **not** densify IB hours, overlap window, MinBodyATR, RR, or Mon/day from this readout.

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Not Real QFSI. Not GOAL.
