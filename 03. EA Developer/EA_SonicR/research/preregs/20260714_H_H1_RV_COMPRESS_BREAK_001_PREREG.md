# Prereg — HYP-H1-RV-COMPRESS-BREAK-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner Discovery Wave4 — thick expectancy + cadence joint  
GPT: waived

## Identity

- Hypothesis ID: `HYP-H1-RV-COMPRESS-BREAK-001`
- EA: `EA_H1RVCompressBreak`
- Path: `03. EA Developer/EA_H1RVCompressBreak/EA_H1RVCompressBreak.mq5`
- Explicitly **not**: VolExp expansion cont; KeltnerSqueeze; NR7 densify; LowVol Donchian fade

## Thesis

Closed-H1 **range-RV compression** (mean range short6 / long48 ≤ 0.55) marks a
volatility coiled state. A subsequent closed-H1 Donchian20 break with body
quality ≥0.40 ATR is a volatility-normalized breakout with a priori quality
gate (not readout-mined). **RR=2.5** targets thick post-cost expectancy;
MaxPerDay=2 targets cadence 2–5/wk.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY H1 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Signal | compress on bars ending shift2; break on bar[1] close beyond Donchian(20) of shifts 2..21; body≥0.40 ATR |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 2.5 |
| SL | 1.25×ATR |
| Max/day | 2 |
| Flat | hour≥22 / weekend; max hold 24 H1 bars |
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
