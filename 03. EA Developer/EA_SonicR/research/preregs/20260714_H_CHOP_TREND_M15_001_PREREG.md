# Prereg — HYP-CHOP-TREND-M15-001

Date: 2026-07-14  
State on freeze: **`FROZEN`** for Owner-authorized Model 0 screen (unlimited-GOAL queue).  
Prior twin-fail-closed note (`readouts/20260714_HYP_CHOP_TREND_M15_001_DEDUP_FAIL_CLOSED.md`) remains on file as de-dup caution; Owner queue 2026-07-14 orders empirical Model 0 anyway. Kill/park from readout; do not retune.  
Author: local self-research (no ChatGPT; Grok lane)

## Identity

- Hypothesis ID: `HYP-CHOP-TREND-M15-001`
- EA name: `EA_M15ChopTrend`
- Parent / near-miss seed: AlphaFactory `S630 / EA_ChopRegime` (USDJPY+ M15 Europe h10-14 Mon+Wed+Thu, PF ~1.26, 785 trades, WFA 5/5 efficiency 1.35) — PF>1.20 near-miss with cadence; **not** a post-hoc rescue of that exact day/hour filter set
- Explicitly **not**: tick-vol impulse (killed `HYP-TICKVOL-IMPULSE-M15-001`), hour-open-break (killed cadence-book), vol-expansion (`HYP-VOLEXP-M15-001` killed), carry/COT/bond-diff/OIS, fix/benchmark, Sonic Classic rescue

## Thesis

Choppiness Index gates trend-follow: only trade when CI(14) ≤ 50 (not random-walk). Direction from EMA8/21 fresh cross or strong-trend continuation when CI < 38.2, both requiring close vs EMA50 bias. Structural budget ≤2 trades/day, Mon–Thu liquidity window, weekend flat → target calendar cadence near 2–5 trades/week on USDJPY M15 without exogenous series.

## Locked Design (zero post-result edit)

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 (unsuffixed) |
| Decision bar | closed `bar[1]` only |
| Chop gate | CI(14) ≤ 50; continuation only if CI < 38.2 |
| Direction | EMA8/21 fresh cross **or** strong-cont under CI<38.2; long only if close > EMA50; short only if close < EMA50 |
| Session (server hour) | entry `[08,17)`, flat/exit from hour `21`, Fri flat |
| Days | Mon–Thu only (Fri reserved for weekend flat; **no Mon/Wed/Thu skip mining from S630**) |
| Risk | 0.50% equity per trade; max lot 1.0 |
| SL / TP | `1.5 × ATR` / `1.5R` |
| Caps | max 2 trades per calendar day; one position at a time |
| Cost policy | missing cost ≠ 0; tester report PF is **not** verified broker cost |

Banned after first readout: hour/day vetoes, CI/EMA threshold mining, symbol switch as rescue, adding filters from this run’s losers.

## Test Plan

- Screen: Model 0 preferred
- Window: `2021.01.01`–`2025.12.31`
- Deposit / leverage: `10000` / `100`
- Kill if: trades/week outside `[1.5, 6.0]` on elapsed calendar weeks, or PF < 1.00, or sample < 80 trades
- Iterate only via **new** hypothesis ID if kill; do not tune this ID

## Independence / De-dup

- Differs from S630: Mon–Thu all days (no Mon/Wed/Thu subset), session `[08,17)` not Europe-only `[10,14)`, weekend flat + Fri-off, unsuffixed USDJPY, 2021–2025 GOAL window, CTrade retry fill contract, new folder/magic
- Differs from killed TickVolImpulse: EMA cross under CI, not volume+body impulse
- Differs from killed HourOpenBreak: regime+EMA trend, not clock-hour open-range break
- Differs from killed VolExpansion: uses Choppiness Index + EMA cross, not RV-ratio body sum
