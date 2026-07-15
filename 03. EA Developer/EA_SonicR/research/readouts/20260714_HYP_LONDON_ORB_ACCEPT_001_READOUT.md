# Readout — HYP-LONDON-ORB-ACCEPT-001

Date: 2026-07-14  
Run: `20260714_193852`  
EA: `EA_M15LondonORBAccept`  
Verdict: **`PARKED`** (GOAL unmet)

## Metrics (tester `current`)

| Metric | Value |
|---|---|
| Trades | 342 |
| PF | **1.08** |
| Net | +$2888 |
| Max DD | ~2.53% |
| Expectancy | +$8.44 |
| tpw elapsed | **~1.31**/wk |

Survives kill floor (PF≥1.00, N≥80, tpw∈[1,6]) but fails research bar PF>1.30 and
cadence 2–5/wk. Acceptance filter did **not** lift parent LondonORB PF~1.17 toward GOAL.

## Process

`includes_sha256` closeout flake after report ready; artifacts + manual analyze kept.

## Do not

Mine hour/day/session subgroups from this readout. Do not flip to FailedORB fade.
Do not densify ORB minutes.

## Cost

`UNVERIFIED_TESTER_DEFAULT`. Not confirmed / not GOAL.
