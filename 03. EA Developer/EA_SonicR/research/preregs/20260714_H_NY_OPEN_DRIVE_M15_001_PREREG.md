# Prereg — HYP-NY-OPEN-DRIVE-M15-001

Date: 2026-07-14  
State on freeze: `preregistered` (Model 0 screen under Owner MT autonomy)  
Author: local self-research after PDH Break park (no ChatGPT)

## Identity

- Hypothesis ID: `HYP-NY-OPEN-DRIVE-M15-001`
- EA name: `EA_M15NYOpenDrive`
- Path: `03. EA Developer/EA_M15NYOpenDrive/EA_M15NYOpenDrive.mq5`
- Parent / seed: classic NY opening-range auction. **Not** a LondonORB hour-window retune (banned). Not Spark/HourOpen/PDH/ITSM/SB/USBILL/Keltner rescue.

## Thesis

NY first-hour `[15,16)` (server) forms an opening auction range after London. After lock at hour ≥ 16, a closed `bar[1]` break with body confirmation and D1 EMA50 alignment continues through `[16,20)`. One trade/day, Mon–Thu, weekend flat, risk 0.5%. Expected elapsed cadence near ~2–4/week if edge exists.

## Locked Design

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 |
| Decision | closed `bar[1]` only |
| ORB window | `[15, 16)` build; lock at hour ≥ 16 |
| Range gate | ATR(14) × `[0.25, 2.50]` |
| Break buffer / body | ATR×0.10 / 0.40 |
| HTF bias | D1 EMA50 (closed D1 shift≥1) |
| Trade window | `[16, 20)`; flat hour `21` |
| Days | Mon–Thu; Fri off |
| Risk / SL/TP | 0.50%; opposite ORB + ATR×0.15 / `1.5R` |
| Caps | max 1/day; max hold 32 bars; spread ≤50 |
| Magic | 880942 |
| Cost | tester `current`; missing ≠ 0 |

Banned: day/hour vetoes, ORB window retune from this readout, buffer/body mining, LondonORB twin rescue.

## Test Plan

- Model 0; 2021.01.01–2025.12.31; Deposit 10000; Leverage 100
- Kill if tpw ∉ [1.0, 6.0] or PF < 1.00 or N < 80
- Park if PF ∈ [1.00, 1.30) with cadence OK, or PF≥1.30 but tpw < 2.0
- HIT_RESEARCH_BAR if PF>1.30 and tpw ∈ [2.0, 5.0] (still not confirmed)

## Independence

See `readouts/20260714_NY_OPEN_DRIVE_VS_LONDONORB_DEDUP_CLEARANCE.md`.
