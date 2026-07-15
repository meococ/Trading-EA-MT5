# 3-critic panel — HARD PIVOT entry-state rebuild

Date: 2026-07-15
Nested critics: trader / quant / MQL5 (cursor-grok-4.5-high-fast).
Lead merge: **PAUSE R-series densify**; implement ≤2 entry-state children.

## Diagnosis (merged)
RR2/Spark die under +$12 because expectancy/trade is friction-thin
(~$19 raw vs $12 RT), not because cadence or exits are broken.
Exit densify ALL_KILL; MaxKZ densify banned; R10–R31 entry templates
ALL_KILL. Need higher $/trade via entry location / acceptance, not more signals.
Quant: RR2 needs ~+$8.7/trade for PF@$12≥1.30; binding x1.5 ~+$12.4.
PRIMARY book equal-lift ~+$6.5 / +$9.8.

| Critic | Stance |
|---|---|
| Sonic trader | CONDITIONAL GO — Retest-Accept SB #1; FX persist sleeve #2; Asia-break NO-GO |
| Quant | GO persist cadence sleeve first; CONDITIONAL retest-accept; Asia-break NO-GO |
| MQL5/MT5 | B probeable from H1 OHLC now; A needs M15 FSM (not RR2 trade filter); C NO-GO |

## Named children (≤2)
1. `HYP-FX3-H1-AUCTION-PERSIST-CADENCE-CONT-001` — GO
2. `HYP-SB-FVG-RETEST-ACCEPT-DELAY-001` — CONDITIONAL GO

Merge: **GO offline**. Model 0 WITHHELD until PROBE_SURVIVOR.
Forbidden: R-series densify, exit densify, MaxKZ densify, ETH VR densify, ORB/IB.
