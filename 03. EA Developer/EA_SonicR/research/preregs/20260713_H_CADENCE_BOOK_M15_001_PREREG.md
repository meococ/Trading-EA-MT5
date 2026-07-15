# Prereg — HYP-CADENCE-BOOK-M15-001

Date: 2026-07-13  
State on freeze: `preregistered` (first Model 0/1 screen authorized under Owner unlimited-GOAL)  
Author: local self-research (no ChatGPT; Grok lane)

## Identity

- Hypothesis ID: `HYP-CADENCE-BOOK-M15-001`
- EA name: `EA_M15HourOpenBreak`
- Parent / near-miss seed: AlphaFactory `S678 / EA_H1OpenBreak` (USDJPY M5, PF ~1.21, high N, WFA 4/5) — cadence-adjacent near-miss with PF ≤ 1.30 GOAL bar; **not** a post-hoc rescue of that exact config
- Explicitly **not** in locked V2–V8 surfaces: carry/public-rates, fix/benchmark fade, news/macro surprise, impact-pressure/flow/spread proxies, H4/D1 price-only exhaustion, Sonic rescue filters

## Thesis

First closed M15 bar of each clock hour defines a micro opening range. A later **closed** M15 break of that range, in the direction of H1 EMA50 and only when H1 choppiness is trending (CI < 50), continues through stop cascades / pending-order momentum inside the same hour. Structural trade budget: ≤1 trade/hour, ≤2/day, London daytime only, weekend flat → expected calendar cadence near 2–5 trades/week on EURUSD M15 without needing exogenous series.

## Locked Design (zero post-result edit)

| Item | Frozen value |
|---|---|
| Symbol / TF | EURUSD M15 (unsuffixed) |
| Decision bar | closed `bar[1]` only |
| Range | high/low of the first completed M15 whose open is the H1 open |
| Break buffer | `0.30 × ATR(14,H1)` beyond range |
| Trend | H1 EMA50; long only if close > EMA; short only if close < EMA |
| Chop filter | H1 CI(14) < 50 |
| Session (server hour) | entry `[08,17)`, flat/exit from hour `21`, Fri flat |
| Days | Mon–Thu only (Fri reserved for weekend flat; no Fri entries) |
| Risk | 0.50% equity per trade; max lot 1.0 |
| SL / TP | `1.5 × ATR(H1)` / `1.5R` |
| Caps | max 1 trade per H1; max 2 trades per calendar day |
| Cost policy | missing cost ≠ 0; tester report PF is **not** verified broker cost |

Banned after first readout: hour/day vetoes, threshold mining on CI/buffer/ATR, symbol switch as rescue, adding filters from this run’s losers.

## Test Plan

- Screen: Model 0 preferred; Model 1 acceptable if Model 0 ceremony blocks and is documented
- Window: `2021.01.01`–`2025.12.31`
- Deposit / leverage: `10000` / `100`
- Kill if: trades/week outside `[1.5, 6.0]` on elapsed calendar weeks, or PF < 1.00, or sample < 80 trades
- Iterate only via **new** hypothesis ID if kill; do not tune this ID

## Independence / De-dup

- Differs from S678: M15 closed-bar (not M5 intrabar 10-min range), EURUSD (not USDJPY+), weekend-flat + Fri-off, no Tue skip, broader London window for cadence book target
- Differs from ChopRegime family (KILL_FAMILY): chop is a gate only; entry is hour-open range break, not EMA cross under CI
- Differs from ORB/Asian-manip/Sonic Asian reclaim: clock-hour micro-range, not Asian session range or ICT FVG
