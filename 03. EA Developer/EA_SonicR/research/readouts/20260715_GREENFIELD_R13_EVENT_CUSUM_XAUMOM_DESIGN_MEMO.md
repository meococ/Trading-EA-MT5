# Design — Round 13 NFP cont / CUSUM persist / XAU thick-mom

Date: 2026-07-15
Hard constraint: **FORBIDDEN** OHLC fade / MR / session-edge densify.

## 1 `HYP-FX3-H1-NFP-IMPULSE-CONT-001`
First-Friday calendar (reconstructable); H1 hour∈(12, 13) UTC;
|body|≥0.8×ATR → CONTINUE impulse; SL=1.6 RR=2.0 hold≤12; per-symbol once/event.

## 2 `HYP-FX3-H1-CUSUM-BREAK-PERSIST-001`
Page CUSUM on z-returns (win=48, k=0.5, h=3.5);
trade WITH break; SL=1.75 RR=2.0 hold≤16; cooldown=24; first FX3/day.

## 3 `HYP-XAUUSD-H4-D1-TSMOM-THICK-001`
D1 |ROC20|≥2.5×ATR → H4 thick mom; SL=2.0 RR=2.5 hold≤36.
