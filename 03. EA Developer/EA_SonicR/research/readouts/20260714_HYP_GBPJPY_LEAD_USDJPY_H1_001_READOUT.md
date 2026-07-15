# Readout — HYP-GBPJPY-LEAD-USDJPY-H1-001

Date: 2026-07-14  
Authoritative run: `20260714_223748`  
EA: `EA_H1GBPJPYLead`  
Verdict: **`PARKED`** (weak PF; cadence near-band; cost-stress FAIL)

## Metrics (tester `current`, deposit 100000)

| Metric | Value |
|---|---|
| Trades | **1337** |
| PF | **1.10** |
| Net | +$12638.81 |
| Expectancy | +$9.45/trade |
| tpw elapsed | **~5.13**/wk |

Report SHA256: see `preflight/20260714_WAVE4_REPORT_SHA.json`.

## Gates

| Gate | Result |
|---|---|
| Kill PF&lt;1.00 / tpw∉[1,6] / N&lt;80 | PASS |
| Research HIT PF&gt;1.30 ∧ tpw∈[2,5] | **FAIL** (PF 1.10; tpw 5.13) |
| A priori +$12 (diag; PF&lt;1.20) | x1 **0.98** / x1.5 **0.92** / x2 **0.87** → **FAIL** |

## Non-repaint / lag

Lead impulse on GBPJPY bar[2]; follower decision after USDJPY bar[1] close (`leadT2 < followT1`).

## Ban

Do **not** densify lead ATR thresh, session hours, RR, or flip to inverse from this readout. Not GOLDJPY M15 reopen.

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Not Real QFSI. Not GOAL.
