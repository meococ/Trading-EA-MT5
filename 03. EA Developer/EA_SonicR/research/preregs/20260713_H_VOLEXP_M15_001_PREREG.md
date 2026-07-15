# Prereg — HYP-VOLEXP-M15-001

Date: 2026-07-13  
State on freeze: `preregistered` (first Model 0 screen authorized under Owner unlimited-GOAL)  
Author: local self-research (no ChatGPT; Grok lane)

## Identity

- Hypothesis ID: `HYP-VOLEXP-M15-001`
- EA name: `EA_M15VolExpansion`
- Parent / near-miss seed: AlphaFactory `S639 / EA_VolCluster` (USDJPY M15, PF ~1.21, Type #86 vol-expansion). Cadence-adjacent near-miss under GOAL PF>1.30 bar; **not** a post-hoc rescue of S639 day filters.
- Explicitly **not**: hour-open-break (killed `HYP-CADENCE-BOOK-M15-001`), carry/COT/bill-slope, fix/benchmark/session-timing V2–V3 family, Sonic Classic rescue.

## Thesis

GARCH-style volatility clustering: when short realized vol / long realized vol exceeds a frozen expansion threshold on closed M15 bars, the recent closed-body direction tends to continue if aligned with EMA50. Structural budget ≤2 trades/day, London daytime Mon–Thu, weekend flat → expected calendar cadence near 2–5 trades/week on USDJPY M15 without exogenous series.

## Locked Design (zero post-result edit)

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 (unsuffixed; seed thesis symbol) |
| Decision bar | closed `bar[1]` only |
| RV windows | short=5, long=20 log-return stdev |
| Expansion gate | short/long RV ≥ 1.50 |
| Direction | sum of last 3 closed bodies; long if >0 and close>EMA50; short if <0 and close<EMA50 |
| Session (server hour) | entry `[08,17)`, flat/exit from hour `21`, Fri flat |
| Days | Mon–Thu only (Fri reserved for weekend flat; **no** Tue skip from S639 defaults) |
| Risk | 0.50% equity per trade; max lot 1.0 |
| SL / TP | `1.5 × ATR(14,M15)` / `1.5R` |
| Caps | max 2 trades per calendar day; one position at a time |
| Cost policy | missing cost ≠ 0; tester report PF is **not** verified broker cost |

Banned after first readout: hour/day vetoes, RV threshold mining, symbol switch as rescue, adding filters from this run's losers.

## Test Plan

- Screen: Model 0 preferred
- Window: `2021.01.01`–`2025.12.31`
- Deposit / leverage: `10000` / `100`
- Kill if: trades/week outside `[1.5, 6.0]` on elapsed calendar weeks, or PF < 1.00, or sample < 80 trades
- Iterate only via **new** hypothesis ID if kill; do not tune this ID

## Independence / De-dup

- Differs from S639: no Tue skip; broader `[08,17)` vs `[10,14)`; weekend-flat Fri-off explicit; new EA folder/magic; GOAL cadence window 2021-2025
- Differs from killed `EA_M15HourOpenBreak`: RV-ratio expansion entry, not clock-hour micro-range break; no H1 CI gate
- Differs from ChopRegime: no Choppiness Index; direction from body sum under RV expansion, not EMA cross under CI
