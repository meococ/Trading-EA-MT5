# Prereg — HYP-GBPJPY-LEAD-USDJPY-H1-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner Discovery Wave4 — thick expectancy + cadence joint  
GPT: waived

## Identity

- Hypothesis ID: `HYP-GBPJPY-LEAD-USDJPY-H1-001`
- EA: `EA_H1GBPJPYLead`
- Path: `03. EA Developer/EA_H1GBPJPYLead/EA_H1GBPJPYLead.mq5`
- Explicitly **not**: GOLDJPY M15 inverse densify; EURJPY CrossLead M15 range-break reopen; USBILL/carry

## Thesis

Closed **GBPJPY** H1 ATR-impulse (|Δclose| ≥ 1.0×ATR on lead bar[2]) leads
USDJPY in the same direction via shared JPY / risk-on flow, with **legal lag**:
signal fully closed before follower bar[1] decision. A priori **RR=2.5** for
thick post-cost path; MaxPerDay=2 for cadence band.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY H1 (lead GBPJPY H1) |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Signal | lead bar[2] |close−prior| ≥ 1.0 ATR_lead; enter USDJPY same dir after follower bar[1] |
| Session | server hours [7,20) |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 2.5 |
| SL | 1.25×ATR follower |
| Max/day | 2 |
| Flat | hour≥22 / weekend; max hold 24 H1 bars |
| Magic | 880995 |
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
