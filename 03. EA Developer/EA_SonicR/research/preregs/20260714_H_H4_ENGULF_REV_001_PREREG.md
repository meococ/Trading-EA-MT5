# Prereg — HYP-H4-ENGULF-REV-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner Discovery Wave3 — independent thick expectancy/trade  
GPT: waived

## Identity

- Hypothesis ID: `HYP-H4-ENGULF-REV-001`
- EA: `EA_H4EngulfRev`
- Path: `03. EA Developer/EA_H4EngulfRev/EA_H4EngulfRev.mq5`
- Explicitly **not**: M15 EngulfTrend retune; Outside+WR7 densify; MaxKZ/RR spam

## Thesis

Closed H4 **body engulf** of the prior H4 body is a higher-timeframe reversal
commitment candle. Enter in the engulf direction on the next closed H4 if it
holds the engulf mid (acceptance), with a priori **RR=3.0** so winners can
absorb +$8–$12 round-trip stress while targeting GOAL cadence band via H4
selectivity (MaxPerDay=1, Mon–Thu).

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY H4 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Signal | bar[2] body engulfs bar[3] body; bar[1] closes on engulf side of mid |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 3.0 |
| Max/day | 1 |
| Flat | hour≥22 / weekend; max hold 20 H4 bars |
| Magic | 880992 |
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
