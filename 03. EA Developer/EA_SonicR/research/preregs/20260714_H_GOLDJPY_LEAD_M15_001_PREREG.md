# Prereg — HYP-GOLDJPY-LEAD-M15-001

Date: 2026-07-14  
State on freeze: `preregistered` (Model 0 screen under Owner free-MT + GPT waived)  
Author: local self-research only (`GPT_DEEP_RESEARCH_WAIVED / LOCAL_SELF_RESEARCH_ONLY`)

## Identity

- Hypothesis ID: `HYP-GOLDJPY-LEAD-M15-001`
- EA name: `EA_M15GoldJPYLead`
- Parent / near-miss seed: AlphaFactory `S673 / EA_GoldJPYInverse` (USDJPY+ M15 NYC, PF ~1.26, 456 trades / ~57/yr). Independent cross-asset near-miss with PF>1.15; denser Mon–Thu NY window a priori aims calendar cadence ≥~1.5/week. **Not** a post-hoc rescue of S676/S699 hour/day mining.
- Explicitly **not**: ChopRegime/ChopTrend (FAIL_CLOSED twin), HourOpenBreak, VolExpansion, TickVolImpulse, carry/COT/bond-diff, InsideBar sparse sleeve.

## Thesis

Large closed-bar gold M15 move (vs gold ATR) leads an inverse USDJPY move under NY liquidity when USDJPY close aligns with EMA50. Structural budget ≤2 trades/day, Mon–Thu, weekend flat.

## Locked Design (zero post-result edit)

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 (trade); gold context `XAUUSD` |
| Decision bar | closed `bar[1]` only; gold/local bar-time sync required |
| Gold gate | \|close[1]−close[2]\| ≥ 1.20 × gold ATR(14) |
| Direction | gold down → BUY USDJPY; gold up → SELL; require close vs EMA50 |
| Session | entry `[15,18)`, flat/exit from hour `21` |
| Days | Mon–Thu (Fri flat); **no** Mon+Thu-only / skip-h16 from S676 |
| CI | **off** (not ChopRegime twin) |
| Risk | 0.50% equity; max lot 1.0 |
| SL / TP | `1.5 × ATR(14,M15)` / `1.5R` |
| Caps | max 2 trades/day; one position |
| Cost policy | missing cost ≠ 0; tester PF ≠ verified broker cost |

Banned after first readout: hour/day vetoes, gold-thresh mining, adding CI, symbol switch as rescue.

## Test Plan

- Screen: Model 0
- Window: `2021.01.01`–`2025.12.31`
- Deposit / leverage: `10000` / `100`
- Kill if: trades/week outside `[1.5, 6.0]` elapsed calendar, or PF < 1.00, or sample < 80
- Iterate only via **new** hypothesis ID if kill

## Independence / De-dup

- Differs from S673/S676: Mon–Thu full (not Mon+Thu-only); no skip-h16; no CI; new folder/magic; 2021-2025 GOAL window
- Differs from ChopRegime: cross-asset gold lead, not CI+EMA cross
- Differs from killed VolExp/HourOpen/TickVol: different causal surface
