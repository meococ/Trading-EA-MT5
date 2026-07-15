# Prereg — HYP-H1-PIN-PDLEVEL-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner Discovery Wave3 — independent thick expectancy/trade  
GPT: waived

## Identity

- Hypothesis ID: `HYP-H1-PIN-PDLEVEL-001`
- EA: `EA_H1PinPDLevel`
- Path: `03. EA Developer/EA_H1PinPDLevel/EA_H1PinPDLevel.mq5`
- Explicitly **not**: PDH-break / PDH-retest continuation; H1SwingFailure densify; VWAP

## Thesis

H1 **pin / rejection wick** (≥60% of bar range) that **touches prior D1
high or low** is a liquidity-grab fade candidate. Enter opposite the wick on
the closed H1 with a priori **RR=3.0** for thicker post-haircut $/trade while
keeping H1 cadence inside ~2–5/wk via MaxPerDay=2 and Mon–Thu.

Mechanism differs from PDH M15 break/retest (those arm on level break then
accept) and from H1 swing-failure (pivot pierce+close-inside without PD
level object).

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY H1 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Signal | closed bar[1] wick≥0.60 range; touches prior D1 HL; fade wick |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 3.0 |
| Max/day | 2 |
| Flat | hour≥22 / weekend; max hold 12 H1 bars |
| Magic | 880993 |
| Overrides | (none — defaults frozen) |

## Kill / Park / HIT

| Gate | Rule |
|---|---|
| KILL | PF < 1.00 or tpw ∉ [1.0, 6.0] or N < 80 |
| PARK | Survives kill but PF ≤ 1.30 or tpw ∉ [2, 5] |
| HIT | PF > 1.30 ∧ tpw ∈ [2, 5] under tester `current` |

On PF≥1.20: a priori `sonic_cost_stress` base+$12 x1.5/x2 diagnostic.

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Not Real QFSI. Not GOAL.
