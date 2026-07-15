# Probe — HYP-EMA-STRETCH-FADE-M15-001

Date: 2026-07-14  
State: `PROBE_PASS_TO_PREREG`

## Inputs

1. Dedup `readouts/20260714_EMA_STRETCH_FADE_VS_ADR_CHOPMR_DEDUP_CLEARANCE.md` → PASS.
2. STRATEGY_LOG: ADR exhaust dead; ChopMeanRevert dead; PivotBounce weak/low-N —
   none are EMA-stretch Europe MR with frozen 1.5 ATR.
3. Expected denser cadence than ORB books (≤2/day Mon–Thu Europe).

## Checks

| Check | Result |
|---|---|
| Independent vs ADR/ChopMR/ORB shelf | PASS |
| Cadence path toward 2–5/wk plausible | PASS |
| Closed-bar[1] EMA/ATR shift≥1 | PASS |
| Post-hoc threshold mining | Not done — frozen 1.50 |

## Decision

Proceed prereg → Model 0 USDJPY M15 2021–2025. Tester-`current` only; missing≠0.
