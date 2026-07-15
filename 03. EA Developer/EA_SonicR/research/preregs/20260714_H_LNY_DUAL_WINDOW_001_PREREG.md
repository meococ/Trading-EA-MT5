# Prereg — HYP-LNY-DUAL-WINDOW-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Author: local self-research (no ChatGPT)

## Identity

- Hypothesis ID: `HYP-LNY-DUAL-WINDOW-001`
- EA: `EA_M15LNYDualWindow`
- Path: `03. EA Developer/EA_M15LNYDualWindow/EA_M15LNYDualWindow.mq5`
- Parent: structural cadence expansion of LondonNY-class thick edge. **Not** S530 Mon/Wed skip; not Gotobi reopen; not MaxKZ/RR/USBILL.

## Thesis

Keep London ATR×0.50 directional bias (S529-class thick expectancy). Expand cadence structurally by allowing pullback entries in two a priori liquidity windows: late-London `[12,15)` and NY `[15,18)`, MaxPerDay=2, one trade per window. Day set = all Mon–Fri (S529-class), explicitly **not** S530 day filter.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| London bias | open@09:00 → measure@12:00 closed; ATR(D1)×0.50 |
| Windows | [12,15) + [15,18); MaxPerDay=2 |
| PB | lookback 3; depth ATR 0.15–0.60; bounce bar |
| Days | Mon–Fri all true (no Mon/Wed skip) |
| Risk | 0.50%; SL ATR×0.50; RR 2.0; flat hour 20 |
| Magic | 880983 |
| Cost | tester `current`; missing ≠ 0 |

Banned: S530 day-mine; ATR threshold mine from readout; RR retune; symbol hop rescue.

## Screen

Same hard screen; kill fast if cadence still <1.0/wk or x1.5 fails.

## De-dup

`readouts/20260714_POST_EMPTY_SHELF_PDH_H4_LNY_DEDUP_CLEARANCE.md`
