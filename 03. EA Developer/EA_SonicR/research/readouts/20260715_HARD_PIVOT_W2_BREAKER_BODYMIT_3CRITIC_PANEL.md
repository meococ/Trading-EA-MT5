# 3-critic panel — HARD PIVOT W2 (breaker + body-mit)

Date: 2026-07-15
Nested critics: trader / quant / MQL5 (lead self-merge).
Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` (unchanged).

## Diagnosis carry
Auction-persist ALL_KILL: dense tpw≈12, thin PF.
FVG-retest ALL_KILL near-miss: thick exp≈$53 PF@$12≈1.21 but tpw≈1.15.
**FORBIDDEN** to densify either. Need NEW location/acceptance classes
aimed at joint thick $/trade AND tpw∈[2,5].

| Critic | Stance |
|---|---|
| Sonic trader | GO breaker retest-accept; GO body-mitigation (FVG lesson, new zone) |
| Quant | GO both; target mid-cadence; no FVG/auction knob mining |
| MQL5/MT5 | GO — H1 pivot FSM + M15 body FSM closed-bar probeable |

## Named children
1. `HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001` — GO
2. `HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001` — GO

Merge: **GO offline**. Model 0 WITHHELD until PROBE_SURVIVOR.
Forbidden: FVG densify, auction densify, R-series densify, exit/MaxKZ/ORB.
