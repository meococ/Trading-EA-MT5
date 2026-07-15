# Prereg — HYP-H1-ATR-PCTILE-BREAK-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner Discovery Wave5 — joint thick + cadence  
GPT: waived

## Identity

- Hypothesis ID: `HYP-H1-ATR-PCTILE-BREAK-001`
- EA: `EA_H1ATRPctileBreak`
- Path: `03. EA Developer/EA_H1ATRPctileBreak/EA_H1ATRPctileBreak.mq5`
- Explicitly **not**: elevated ATR-ratio mom; LowVol Donchian fade; RV-compress retune

## Thesis

Closed-H1 Donchian(20) break taken **only** when ATR(14) percentile over
lookback 100 sits in **[40, 70]** (mid-vol). Mid-vol gate targets thicker
post-cost expectancy than raw break spam; MaxPerDay=2 + RR=2.5 targets
joint cadence 2–5/wk.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY H1 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Signal | ATR%ile-100 ∈ [40,70] on bar[1]; close beyond Donchian(20) of shifts 2..21; body≥0.40 ATR |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 2.5 |
| SL | 1.25×ATR |
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

## Independence

`readouts/20260714_DISCOVERY_WAVE5_DEDUP_CLEARANCE.md`
