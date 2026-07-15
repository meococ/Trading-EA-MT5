# Prereg — HYP-H1-THREEBAR-REV-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Post `HYP-H1-PIN-PDLEVEL-001` KILL — independent thick-edge structure  
GPT: waived

## Identity

- Hypothesis ID: `HYP-H1-THREEBAR-REV-001`
- EA: `EA_H1ThreeBarRev`
- Path: `03. EA Developer/EA_H1ThreeBarRev/EA_H1ThreeBarRev.mq5`
- Explicitly **not**: PIN-PDLEVEL densify; Outside/Engulf retune; H1SwingFailure;
  M15 EngulfTrend

## Thesis

Classic **three-bar reversal** on H1: bar[2] extends a directional extreme
relative to bar[3] (lower-low for bullish setup / higher-high for bearish),
then closed bar[1] **closes through** the opposite extreme of bar[2]
(above bar[2] high for long / below bar[2] low for short). This is a
structure-accept reversal with a priori **RR=3.0** for thicker post-haircut
$/trade while H1 cadence + MaxPerDay=2 targets ~2–5/wk elapsed.

Mechanism differs from pin-at-PD (wick + D1 level), single-bar engulf, and
outside-bar containment.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY H1 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Signal | closed bar[1] only; 3-bar rev as above; MinBodyFrac bar[1] ≥ 0.35 |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 3.0 |
| Max/day | 2 |
| Flat | hour≥22 / weekend; max hold 12 H1 bars |
| SL | beyond bar[2] extreme + 0.10 ATR |
| Magic | 880994 |
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
