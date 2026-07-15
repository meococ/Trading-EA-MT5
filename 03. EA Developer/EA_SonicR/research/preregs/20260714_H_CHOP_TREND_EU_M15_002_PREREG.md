# Prereg — HYP-CHOP-TREND-EU-M15-002

Date: 2026-07-14  
State on freeze: `preregistered` (child of near-miss 001; seed-faithful Europe hours)  
Author: local self-research (no ChatGPT; Grok lane)

## Identity

- Hypothesis ID: `HYP-CHOP-TREND-EU-M15-002`
- EA name: `EA_M15ChopTrend` (same source as 001)
- Parent: `HYP-CHOP-TREND-M15-001` near-miss Model 0 `20260714_000557` (PF 1.08, 5.37/week)
- Seed: `S630 / EA_ChopRegime` Europe h10-14 (PF~1.26) — this child restores **only** the a priori Europe hour window from the seed; **not** day-subset mining (Mon+Wed+Thu) and **not** CI/EMA retune from 001 losers

## Thesis

Parent 001 used a broad `[08,17)` window and delivered weak-positive PF 1.08 with slightly high cadence. S630’s documented near-miss used Europe `[10,14)`. This child tests whether the seed-faithful Europe window improves PF toward GOAL while keeping Mon–Thu all-on and weekend flat — one frozen change only.

## Locked Design (zero post-result edit)

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 |
| Decision bar | closed `bar[1]` (unchanged from 001) |
| Chop / EMA | defaults identical to 001 (CI≤50, EMA 8/21/50) |
| Session | entry **`[10,14)`**, exit hour `21`, Fri flat |
| Days | Mon–Thu only (**no** Mon/Wed/Thu subset from S630) |
| Risk / SL / TP | identical to 001 |
| Overrides | `InpStartHour=10;InpEndHour=14` only |
| Cost policy | missing cost ≠ 0; research-proxy |

Banned: further hour/day mining from this child’s readout; CI/EMA threshold mining; symbol switch rescue.

## Test Plan

- Screen: Model 0
- Window: `2021.01.01`–`2025.12.31`
- Deposit / leverage: `10000` / `100`
- Kill if: trades/week outside `[1.5, 6.0]`, or PF < 1.00, or sample < 80
- Success toward GOAL research bar: PF > 1.30 with cadence in 2–5 (still research-proxy until cost provenance)

## Independence

Differs from 001 by **one** a priori parameter: Europe hours from S630 seed. Differs from S630 by unsuffixed USDJPY, Mon–Thu all-on (no day skip), weekend flat, 2021–2025 window, CTrade contract.
