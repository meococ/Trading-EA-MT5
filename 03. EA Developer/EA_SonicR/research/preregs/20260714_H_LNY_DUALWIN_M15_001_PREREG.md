# Prereg — HYP-LNY-DUALWIN-M15-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner rebuild after HARD_EMPTY_SHELF; GPT waived

## Identity

- Hypothesis ID: `HYP-LNY-DUALWIN-M15-001`
- EA: `EA_M15LNYDualWin`
- Path: `03. EA Developer/EA_M15LNYDualWin/EA_M15LNYDualWin.mq5`
- Parent: structural cadence expand of LondonNY-class thick edge
  (ref `20260709_074209`); **not** LNY sole-book reopen / not S530 day-skip

## Thesis

London session directional move (≥0.5×ATR_D1 by measure hour) sets ONE bias.
Structural cadence expand = TWO a-priori pullback windows sharing that bias:
late-London [12,15) and NY AM [15,18), max one trade per window (≤2/day).
Keeps thick RR=2.0 / PB-extreme SL architecture that survived friction offline;
does **not** densify by day mining.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| London | open hour 9; measure hour 12; trend ≥0.5 ATR_D1 |
| Windows | W1 [12,15); W2 [15,18); PB lookback 3; depth [0.15,0.60] ATR_D1 |
| Days | Mon–Thu; Fri off (a priori shelf standard) |
| Risk | 0.50%; max 2/day; TP 2.0R; SL PB±0.5 ATR_D1; flat 20 |
| Magic | 880983 |
| Overrides | (none) |

## De-dup

See `readouts/20260714_LNY_DUALWIN_VS_LONDONNY_DEDUP_CLEARANCE.md`.

## Kill / Park / HIT

Standard Model 0 research bar; on HIT run cost-stress x1.5/x2 immediately.
Cadence target: expand toward 2–5/wk while preserving thick expectancy.

## Banned

- Mon/Wed skip or day mine from S530
- Densify MaxPerDay beyond 2; RR/SL retune from readout
- Claiming GOAL from sparse LNY ref alone
