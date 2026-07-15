# Prereg — HYP-PDH-BREAK-M15-001

Date: 2026-07-14  
State on freeze: `preregistered` (Model 0 screen under Owner MT autonomy)  
Author: local self-research (no ChatGPT)

## Identity

- Hypothesis ID: `HYP-PDH-BREAK-M15-001`
- EA name: `EA_M15PDHBreak`
- Path: `03. EA Developer/EA_M15PDHBreak/EA_M15PDHBreak.mq5`
- Parent / seed: opposite side of dead LiqSweep/PDLevel **fade** books (S159–S161, S249–S251). **Not** a rescue of London ORB / Spark / HourOpen / ITSM / SB / USBILL / Keltner.

## Thesis

Prior-day high/low (closed D1 shift≥1) act as liquidity/auction references. A closed M15 bar[1] break beyond PDH/PDL with body confirmation and D1 EMA50 alignment continues in break direction; reclaim of the broken level invalidates. Mon–Thu, weekend flat, risk 0.5%, max 1 trade/day. Expected elapsed cadence near ~2–4/week if edge exists.

## Locked Design (zero post-result edit)

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 (unsuffixed) |
| Decision bar | closed M15 `bar[1]` only |
| Levels | D1 `iHigh/iLow` shift **1** only |
| Break buffer | ATR(14)×0.10 beyond PDH/PDL |
| Break body | min body/range = 0.40 |
| HTF bias | D1 EMA50 required (closed D1 shift≥1) |
| Trade window | `[9, 17)`; flat from hour `21` |
| Days | Mon–Thu; Fri off |
| Risk | 0.50%; max lot 1.0; max 1 trade/day |
| SL / TP | reclaim of PD level ± ATR×0.15 / `1.5R` |
| Caps | max hold 32 M15 bars; max spread 50 pts |
| Magic | 880941 |
| Cost | tester `current` research-proxy; missing ≠ 0 |

Banned after first readout: day/hour vetoes, buffer/body/EMA mining, fade flip, window retune, symbol switch as rescue.

## Test Plan

- Screen: Model 0
- Window: `2021.01.01`–`2025.12.31`
- Deposit / leverage: `10000` / `100`
- Kill if: trades/week outside `[1.0, 6.0]` elapsed, or PF < 1.00, or N < 80
- Park if: PF in `[1.00, 1.30)` with cadence OK, **or** PF ≥ 1.30 but cadence < 2.0
- HIT_RESEARCH_BAR if: PF > 1.30 **and** elapsed cadence in `[2.0, 5.0]` (still not confirmed / not Real QFSI)

## Independence / De-dup

See `readouts/20260714_PDH_BREAK_VS_LIQSWEEP_LONDONORB_DEDUP_CLEARANCE.md`.  
Probe: `readouts/20260714_HYP_PDH_BREAK_M15_001_PROBE.md`.

## Cost honesty

Demo/tester `current` ≠ FivePercentOnline-Real QFSI. Do not claim GOAL confirmed from this screen.
