# Readout — HYP-H4-ENGULF-REV-001

Date: 2026-07-14 ~23:20 ICT  
Run: `20260714_231537`  
EA: `EA_H4EngulfRev`  
State: **`KILLED_AT_MODEL_0`**

## Metrics (tester `current`, deposit 100000, USDJPY H4 2021–2025)

| Metric | Value |
|---|---:|
| Trades | 202 |
| PF | **1.131** |
| Net | **+$4886.45** |
| Exp $/trade | **+$24.19** |
| tpw (elapsed) | **~0.775** |
| Max DD | ~5.67% |

## Gate

KILL — tpw ~0.78 < 1.0 (cadence); PF 1.13 ≤ 1.30 (not HIT).

## Cost stress / Real partial reprice

Not run (no research HIT). Exp +$24 is thicker than MaxKZ friction books but
joint PF+cadence fail; ~$2.3 RT haircut would not create a GOAL survivor.

## Bans

Do not densify engulf body ATR / RR / day from this readout. Not M15 EngulfTrend reopen.
