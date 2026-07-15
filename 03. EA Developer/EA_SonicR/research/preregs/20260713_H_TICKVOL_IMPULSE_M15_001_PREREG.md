# Prereg — HYP-TICKVOL-IMPULSE-M15-001

Date: 2026-07-13  
State on freeze: `preregistered` (first Model 0 screen authorized under Owner unlimited-GOAL)  
Author: local self-research (no ChatGPT; Grok lane)

## Identity

- Hypothesis ID: `HYP-TICKVOL-IMPULSE-M15-001`
- EA name: `EA_M15TickVolImpulse`
- Parent / near-miss seed: AlphaFactory `S679 / EA_TickVolAccel` (USDJPY+ M15, PF ~1.25 Mon+Thu Europe, WFA 4/5, Robust 7/7) — PF>1.20 near-miss with some cadence; **not** a post-hoc rescue of that exact day/hour filter set
- Explicitly **not**: hour-open-break (S678 / HYP-CADENCE-BOOK-M15-001 killed), carry/public-rates, fix/benchmark/session Gotobi, Sonic Classic rescue, COT/bill-slope exogenous

## Thesis

A closed M15 bar with tick-volume acceleration (volume ≥ 1.8× 20-bar average) and a body ≥ 0.5× ATR(14), occurring in a trending chop regime (CI < 50) and aligned with EMA50, marks institutional impulse continuation rather than absorption. Structural trade budget: ≤2 trades/day, Mon–Thu liquidity window, weekend flat → target calendar cadence near 2–5 trades/week on USDJPY M15 without exogenous series.

## Locked Design (zero post-result edit)

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 (unsuffixed) |
| Decision bar | closed `bar[1]` only |
| Volume spike | `tick_vol[1] ≥ 1.8 × mean(tick_vol[2..21])` |
| Body gate | `\|close-open\| ≥ 0.5 × ATR(14)` |
| Trend | EMA50; long only if close > EMA; short only if close < EMA |
| Chop filter | CI(14) < 50 |
| Session (server hour) | entry `[08,17)`, flat/exit from hour `21`, Fri flat |
| Days | Mon–Thu only (Fri reserved for weekend flat; **no Tue/Wed skip mining**) |
| Risk | 0.50% equity per trade; max lot 1.0 |
| SL / TP | `1.5 × ATR` / `1.5R` |
| Caps | max 2 trades per calendar day; one position at a time |
| Cost policy | missing cost ≠ 0; tester report PF is **not** verified broker cost |

Banned after first readout: hour/day vetoes, VolMult/BodyATR/CI threshold mining, symbol switch as rescue, adding filters from this run’s losers.

## Test Plan

- Screen: Model 0 preferred
- Window: `2021.01.01`–`2025.12.31`
- Deposit / leverage: `10000` / `100`
- Kill if: trades/week outside `[1.5, 6.0]` on elapsed calendar weeks, or PF < 1.00, or sample < 80 trades
- Iterate only via **new** hypothesis ID if kill; do not tune this ID

## Independence / De-dup

- Differs from S679: Mon–Thu all days (no Tue skip), session `[08,17)` not Europe-only `[10,14)`, weekend flat + Fri-off, unsuffixed USDJPY, 2021–2025 GOAL window, CTrade retry fill contract
- Differs from killed HYP-CADENCE-BOOK-M15-001: volume-impulse continuation, not clock-hour open-range break
- Differs from S624/S625 FlowType: uses M15 tick volume + body + CI/EMA gates, not M1 bar-count flow proxy
- Differs from ChopRegime: entry is volume+body impulse, not EMA cross under CI alone
