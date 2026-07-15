# Prereg — HYP-INSIDEBAR-M15-001

Date: 2026-07-14  
State on freeze: `preregistered` (first Model 0 screen authorized under Owner MT autonomy)  
Author: local self-research after SB weekend-flat park + Chop/VolExp kills (no ChatGPT)

## Identity

- Hypothesis ID: `HYP-INSIDEBAR-M15-001`
- EA name: `EA_M15InsideBreak`
- Path: `03. EA Developer/EA_M15InsideBreak/EA_M15InsideBreak.mq5`
- Parent / near-miss seed: AlphaFactory `S226 / EA_InsideBar` USDJPY M15 (PF ~1.32, 112t) and H1 confirmation `S232` (PF ~1.65). Independent compression→breakout mechanism; **not** a post-hoc rescue of day-skip variants (S319–S322).
- Explicitly **not**: ChopRegime/ChopTrend (FAIL_CLOSED), VolExpansion, TickVolImpulse, HourOpenBreak, GoldJPY lead, SB Friday mining, carry/COT/bill-slope/bond/OIS, V2–V7 fix/flow families.

## Thesis

Inside-bar compression at closed `bar[2]` inside mother `bar[3]` represents short institutional accumulation. When closed `bar[1]` breaks the inside-bar range during a priori London/NY kill-zone windows and aligns with H4 EMA50 bias, direction continues. Structural budget ≤2 trades/day, Mon–Thu, weekend flat → expected calendar cadence near GOAL 2–5/week on USDJPY M15 without exogenous series. Seed M15 was sparse (~16/yr); densification is a priori KZ retention + Mon–Thu (no day mining from S320), not threshold retune.

## Locked Design (zero post-result edit)

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 (unsuffixed) |
| Decision bar | closed `bar[1]` only; mother=`bar[3]`, inside=`bar[2]` |
| IB range gate | ATR(14) × `[0.20, 0.80]` |
| Break buffer | ATR × 0.05 beyond IB high/low |
| Break body | min body/range of break bar = 0.50 |
| HTF bias | H4 EMA50 required (close on side of break) |
| Kill zones (server hour) | `[09,12)` and `[15,18)`; flat/exit from hour `21` |
| Days | Mon–Thu only (Fri reserved for weekend flat; **no** Mon/Wed skip from seed day-mining) |
| Risk | 0.50% equity per trade; max lot 1.0 |
| SL / TP | IB opposite + ATR×0.20 buffer / `1.5R` |
| Caps | max 2 trades per calendar day; one position at a time |
| Magic | 880922 |
| Cost policy | missing cost ≠ 0; tester report PF is **not** verified broker cost |

Banned after first readout: hour/day vetoes, IB ATR threshold mining, symbol/TF switch as rescue, adding filters from this run's losers, converting to H1 sparse sleeve as "proof".

## Test Plan

- Screen: Model 0
- Window: `2021.01.01`–`2025.12.31`
- Deposit / leverage: `10000` / `100`
- Spread: tester `current` (research-proxy label only)
- Kill if: trades/week outside `[1.5, 6.0]` on elapsed calendar weeks, or PF < 1.00, or sample < 80 trades
- Park if: PF in `[1.00, 1.30)` with cadence OK (research near-miss; no GOAL claim)
- Iterate only via **new** hypothesis ID if kill; do not tune this ID

## Independence / De-dup

- Differs from seed `EA_InsideBar`: new folder/magic; M15 GOAL window 2021–2025; risk 0.5%; closed-bar CTrade retry fill; a priori Mon–Thu (not H1-only enforcement; not day-skip mining).
- Differs from killed HourOpenBreak: single-candle IB compression + break, not clock-hour micro-range.
- Differs from VolExpansion: no RV-ratio gate; IB geometry + H4 bias.
- Differs from ChopRegime: no Choppiness Index / EMA cross.
- Differs from TickVolImpulse: no tick-volume spike.
- Differs from SB weekend-flat: not FVG/session SilverBullet management patch.
- Differs from GoldJPY: no cross-asset gold lead.

## Cost honesty

Tester `current` spread ≠ FivePercentOnline-Real QFSI. Do not claim GOAL confirmed from this screen alone.
