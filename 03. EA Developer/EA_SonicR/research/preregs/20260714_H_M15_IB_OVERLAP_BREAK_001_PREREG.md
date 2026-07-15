# Prereg — HYP-M15-IB-OVERLAP-BREAK-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner Discovery Wave4 — thick expectancy + cadence joint  
GPT: waived

## Identity

- Hypothesis ID: `HYP-M15-IB-OVERLAP-BREAK-001`
- EA: `EA_M15IBOverlapBreak`
- Path: `03. EA Developer/EA_M15IBOverlapBreak/EA_M15IBOverlapBreak.mq5`
- Explicitly **not**: LondonORB Asian-range densify; NYOpenDrive; LNY DualWin; MaxKZ/RR

## Thesis

London **Initial Balance** (first server hour 07–08) is a liquidity auction
range. A closed-M15 break of that range during London–NY overlap [13,16), with
IB-width and break-body ATR quality filters, captures session microstructure
continuation with a priori **RR=2.5** so winners can absorb +$8–$12 RT stress
while M15 + MaxPerDay=2 target GOAL cadence band.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Signal | Lock IB Hi/Lo in hour 07; break close beyond IB in hours [13,16); body≥0.35 ATR; IB width≥0.40 ATR |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 2.5 |
| Max/day | 2 (one break direction flag/day) |
| Flat | hour≥21 / weekend; max hold 32 M15 bars |
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
