# Design memo — D1 vol-regime breakout FX3

Date: 2026-07-15
Parent: swing thick book ALL_KILL → named next class

## Design 1 — 8d extreme break under expansion
`HYP-FX3-D1-VOLREGIME-8D-BREAK-001`
ATR14/ATR50≥1.20; D1 close beyond prior 8-day high/low; next H4 open;
SL 1.6 ATR_H4 beyond extreme; RR=2.5; hold≤32 H4;
≤1/symbol; ≤2 book; EUR+GBP same-dir → higher ATR ratio.

## Design 2 — Two-close confirmation
`HYP-FX3-D1-VOLREGIME-2CLOSE-FOLLOW-001`
Same expansion; require two consecutive closes beyond the frozen 8d extreme.

## ≠ killed
≠ NR7/RV-compress (no range-rank compress); ≠ Donchian channel fade/break
with RV gate; ≠ ADX/thrust/TD/ROC densify; ≠ Outside/Engulf/EMA-PB/Weekly-HL.

## If both fail — next object class
Multi-day **carry / swap-aware differential** book (USD rate-diff proxy from
public price slope of short-rate FX) OR microstructure after research-grade
cost — not another D1 breakout densify.
