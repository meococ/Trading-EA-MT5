# Prereg — HYP-LONDON-ORB-M15-001

Date: 2026-07-14  
State on freeze: `preregistered` (Model 0 screen under Owner MT autonomy)  
Author: local self-research after price-M15 dual-filter shelf EMPTY (no ChatGPT)

## Identity

- Hypothesis ID: `HYP-LONDON-ORB-M15-001`
- EA name: `EA_M15LondonORB`
- Path: `03. EA Developer/EA_M15LondonORB/EA_M15LondonORB.mq5`
- Parent / seed: classic London opening-range auction (not STRATEGY_LOG dual-filter near-miss). Structural a priori ORB — **not** a rescue of Spark/SB/ITSM/HourOpen/InsideBar/VolExp/Chop/TickVol/GoldJPY/USBILL.
- Explicitly **not**: Asian overnight range (Spark), clock-hour micro-ORB (HourOpenBreak), ICT Judas fakeout (LondonSweep/Judas dead).

## Thesis

London first-hour `[9,10)` (server) forms an opening auction range. After lock at hour ≥ 10, a closed `bar[1]` break beyond that range with body confirmation and D1 EMA50 alignment continues through the London–early-NY window `[10,16)`. One trade/day, Mon–Thu, weekend flat, risk 0.5%. Expected elapsed cadence near ~2–4/week if edge exists (dense enough for GOAL book; independent of Tue–Wed Spark sparsity).

## Locked Design (zero post-result edit)

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 (unsuffixed) |
| Decision bar | closed `bar[1]` only |
| ORB window | `[9, 10)` build; lock at hour ≥ 10 |
| Range gate | ATR(14) × `[0.25, 2.50]` |
| Break buffer | ATR × 0.10 beyond ORB high/low |
| Break body | min body/range = 0.40 |
| HTF bias | D1 EMA50 required (closed D1 shift≥1) |
| Trade window | `[10, 16)`; flat from hour `21` |
| Days | Mon–Thu; Fri off |
| Risk | 0.50%; max lot 1.0; max 1 trade/day |
| SL / TP | opposite ORB extreme + ATR×0.15 / `1.5R` |
| Caps | max hold 32 M15 bars; max spread 50 pts |
| Magic | 880940 |
| Cost | tester `current` research-proxy; missing ≠ 0 |

Banned after first readout: day/hour vetoes, ORB window retune, buffer/body/range mining, symbol switch as rescue, adding filters from this run's losers.

## Test Plan

- Screen: Model 0
- Window: `2021.01.01`–`2025.12.31`
- Deposit / leverage: `10000` / `100`
- Kill if: trades/week outside `[1.0, 6.0]` elapsed, or PF < 1.00, or N < 80
- Park if: PF in `[1.00, 1.30)` with cadence OK, **or** PF ≥ 1.30 but cadence < 2.0
- HIT_RESEARCH_BAR if: PF > 1.30 **and** elapsed cadence in `[2.0, 5.0]` (still not confirmed / not Real QFSI)

## Independence / De-dup

See `readouts/20260714_LONDON_ORB_VS_SPARK_HOUROPEN_DEDUP_CLEARANCE.md`.

## Cost honesty

Demo/tester `current` ≠ FivePercentOnline-Real QFSI. Do not claim GOAL confirmed from this screen.
