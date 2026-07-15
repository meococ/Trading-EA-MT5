# Probe — HYP-H1-ATR-REGIME-MOM-001

Date: 2026-07-14  
State: `PROBE_PASS_TO_PREREG`

## Inputs

1. Dedup `readouts/20260714_H1_ATR_REGIME_MOM_VS_VOLEXP_CHOP_DEDUP_CLEARANCE.md` → PASS.
2. STRATEGY_LOG: VolExp/Chop/Keltner/LinReg/HA/KAMA killed or weak on M15 —
   none are H1 ATR-ratio≥1.20 + EMA50 side continuation with frozen gates.
3. Cadence path: H1 + max 1/day Mon–Thu → theoretical ≤4/wk; elevated-vol
   gate should land nearer 1.5–3.5/wk (plausible for GOAL band).

## Checks

| Check | Result |
|---|---|
| Independent vs VolExp/Chop/Stretch/ORB shelf | PASS |
| Cadence path toward 2–5/wk plausible | PASS |
| Closed-bar[1] H1 only | PASS |
| Post-hoc threshold mining | Not done — frozen 1.20 / EMA50 |

## Decision

Proceed prereg → Model 0 USDJPY H1 2021–2025. Tester-`current` only; missing≠0.
