# Readout — HYP-H1-RV-COMPRESS-BREAK-001

Date: 2026-07-14  
Authoritative run: `20260714_223714`  
EA: `EA_H1RVCompressBreak`  
Verdict: **`KILLED_AT_MODEL_0`** (cadence; thick friction diagnostic only)

## Metrics (tester `current`, deposit 100000)

| Metric | Value |
|---|---|
| Trades | **84** |
| PF | **1.61** |
| Net | +$4825.99 |
| Expectancy | +$57.45/trade |
| Equity DD relative | ~1.23% |
| tpw elapsed | **~0.32**/wk |

Report SHA256: see `preflight/20260714_WAVE4_REPORT_SHA.json`.

## Gates

| Gate | Result |
|---|---|
| Kill PF&lt;1.00 | PASS |
| Kill tpw∉[1.0, 6.0] | **FAIL** (~0.32) → **KILL** |
| Kill N&lt;80 | PASS (84) |
| Research HIT | **FAIL** |

## A priori +$12 cost-stress (diagnostic; thick)

Artifact: `runs/EA_H1RVCompressBreak/20260714_223714/analysis/cost_stress_base12.json`

| Scenario | PF |
|---|---|
| base report | ~1.62 |
| x1 (+$12) | **1.46** |
| x1.5 | **1.38** PASS ≥1.25 |
| x2 | **1.32** PASS ≥1.00 |

Friction architecture survives +$12 stress, but **cadence is dead** — same thick/sparse failure mode as LNY DualWin / H4 Engulf. Not a sole GOAL book. Do **not** densify compress ratio / Donchian / RR to buy trades.

## Ban

No compress-ratio / Donchian-length / RR / hour/day mining from this kill.

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Not Real QFSI. Not GOAL.
