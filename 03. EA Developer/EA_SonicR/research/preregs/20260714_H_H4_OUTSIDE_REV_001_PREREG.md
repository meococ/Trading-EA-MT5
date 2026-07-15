# Prereg — HYP-H4-OUTSIDE-REV-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner post-cost rebuild after MaxKZ2 Real-P50 FAIL; GPT waived  
Parent stub: `THICK_EDGE_WAVE_EMPTY` next-legal idea

## Identity

- Hypothesis ID: `HYP-H4-OUTSIDE-REV-001`
- EA: `EA_H4OutsideRev`
- Path: `03. EA Developer/EA_H4OutsideRev/EA_H4OutsideRev.mq5`
- Explicitly **not**: NR7 densify / RR retune / multi-sym rescue

## Thesis

H4 **outside bar** that is also the **widest range of 7** (WR7 — opposite of
NR7 compression) is a failed-expansion candidate. When the next closed H4
closes back inside that outside range and rejects the mid relative to the
outside close, fade. Pre-registered RR=3.0 for thicker post-haircut
expectancy than MaxKZ2/RR2 friction books.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY H4 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Signal | outside vs prior + WR7; fade on bar[1] inside + mid reject |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 3.0 |
| Max/day | 1 |
| Flat | hour≥22 / weekend; max hold 20 H4 bars |
| Magic | 880991 |
| Overrides | (none — defaults frozen) |

## Kill / Park / HIT

| Gate | Rule |
|---|---|
| KILL | PF < 1.00 or tpw ∉ [1.0, 6.0] or N < 80 |
| PARK | Survives kill but PF ≤ 1.30 or tpw ∉ [2, 5] |
| HIT | PF > 1.30 ∧ tpw ∈ [2, 5] under tester `current` |

Cost screen **baked from Model 0** (a priori; not post-hoc):
- Always run `sonic_cost_stress` report-only base+$12 on Model 0 trades.
- On PF≥1.20: require diagnostic x1.5 PF≥1.25 and x2 PF≥1.00 to keep HIT;
  else PARK/KILL thin-expectancy under friction.
- Optional Real-P50 ~$2.62 haircut is diagnostic only — never claim verified.

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Not Real QFSI. Not GOAL.
