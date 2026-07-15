# Probe — HYP-FAILED-ORB-FADE-M15-001

Date: 2026-07-14  
State: `PROBE_PASS_TO_PREREG`

## Inputs

1. Dedup `readouts/20260714_FAILED_ORB_FADE_VS_LONDONORB_DEDUP_CLEARANCE.md` → PASS.
2. LondonORB Model 0 park proves OR object exists with cadence path; this ID
   tests the **failed-auction** opposite.
3. Owner ban: do not retune ORB window from readout; window frozen a priori.

## Checks

| Check | Result |
|---|---|
| Independent vs break-continuation ORB | PASS |
| Cadence path ~[1,4]/wk structural (≤1/day Mon–Thu) | PASS |
| Closed-bar[1] feasible | PASS |
| Cosmetic LondonORB twin | FAIL if claimed — **not claimed** |
| GPT required | No |

## Decision

Proceed prereg → Model 0 USDJPY M15 2021–2025. Tester-`current` only; missing≠0.
