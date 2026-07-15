# Prereg — HYP-SPARK-ASIAN-M15-001

Date: 2026-07-14  
State on freeze: `preregistered` (first Model 0 screen authorized under Owner MT autonomy)  
Author: local self-research after InsideBar / Chop / VolExp / GoldJPY kills (no ChatGPT)

## Identity

- Hypothesis ID: `HYP-SPARK-ASIAN-M15-001`
- EA name: `EA_M15SparkAsian`
- Path: `03. EA Developer/EA_M15SparkAsian/EA_M15SparkAsian.mq5`
- Parent / near-miss seed: AlphaFactory `S111 / EA_Spark` v1.4 USDJPY M15 baked config (PF ~1.26, ~71/yr ≈ 1.37/week, WFA 4/5). Independent Asian-compression → London/NY breakout mechanism.
- Explicitly **not**: InsideBar, ChopRegime/ChopTrend, VolExpansion, TickVolImpulse, HourOpenBreak, GoldJPY lead, SB Friday mining, carry/COT/bill-slope/bond/OIS, V2–V7 fix/flow families.

## Thesis

Asian-session range compression (server hours `[0,8)`) locks a tradeable Hi/Lo. When closed `bar[1]` breaks that range during London `[9,13)` or NY `[15,18)` with D1 EMA50 agreement, session continuation persists to a 1.5R target (executed frozen default) with stop beyond the opposite Asian extreme. Seed day filter is Tue+Wed only (S111 baked; S223 showed Mon–Thu densification destroys edge — a priori structural, not mined from tonight). Weekend flat. Expected research cadence near ~1.3–1.5/week; dual-filter near-miss vs GOAL PF>1.30 and 2–5/week.

## Locked Design (zero post-result edit)

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 (unsuffixed) |
| Decision bar | closed `bar[1]` only |
| Asian window | `[0, 8)` build; lock at hour ≥ 8 |
| Range gate | ATR(14) × `[0.80, 8.00]` |
| Break buffer | ATR × 0.15 beyond Asian high/low |
| Break body | min body/range of break bar = 0.35 |
| HTF bias | D1 EMA50 required (closed D1) |
| Entry windows | London `[9,13)` and NY `[15,18)`; flat/exit from hour `21` |
| Days | Tue+Wed only (seed baked; Fri off for weekend flat) |
| Risk | 0.50% equity per trade; max lot 1.0 |
| SL / TP | opposite Asian extreme + ATR×0.20 / `1.5R` (executed defaults; BE at 1R enabled) |
| Caps | max 2 trades/day; max hold 24 M15 bars; one position |
| Magic | 880930 |
| Cost policy | missing cost ≠ 0; tester report PF is **not** verified broker cost |

Banned after first readout: day/hour vetoes, range/buffer/body threshold mining, symbol/TF switch as rescue, adding filters from this run's losers, Mon–Thu densification rescue (already killed as S223).

## Test Plan

- Screen: Model 0
- Window: `2021.01.01`–`2025.12.31`
- Deposit / leverage: `10000` / `100`
- Spread: tester `current` (research-proxy label only)
- Kill if: trades/week outside `[1.0, 6.0]` on elapsed calendar weeks, or PF < 1.00, or sample < 80 trades
- Park / near-miss if: PF in `[1.00, 1.30)` with cadence OK, **or** PF ≥ 1.30 but cadence < GOAL 2.0 (research survivor; no GOAL claim)
- HIT_RESEARCH_BAR if: PF > 1.30 **and** elapsed cadence in `[2.0, 5.0]` under research-proxy cost (still not confirmed)
- Iterate only via **new** hypothesis ID if kill; do not tune this ID

## Independence / De-dup

- Differs from seed `EA_Spark`: new folder/magic; single-file closed-bar CTrade; GOAL window 2021–2025; risk 0.5%; no HolidayCalendar/PartialClose/ExecQuality sidecar dependency for this screen.
- Differs from killed InsideBar: Asian range breakout, not mother/inside geometry.
- Differs from VolExpansion: no RV-ratio gate.
- Differs from ChopRegime: no Choppiness Index / EMA cross.
- Differs from TickVolImpulse: no tick-volume spike.
- Differs from HourOpenBreak: multi-hour Asian range, not clock-hour micro-range.
- Differs from GoldJPY: no cross-asset gold lead.
- Differs from SB weekend-flat: not FVG/session SilverBullet management patch.

## Cost honesty

Tester `current` spread ≠ FivePercentOnline-Real QFSI. Do not claim GOAL confirmed from this screen alone.
