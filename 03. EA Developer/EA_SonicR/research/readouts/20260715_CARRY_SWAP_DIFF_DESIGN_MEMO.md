# Design memo — Carry/swap-aware multi-day differential FX3

Date: 2026-07-15
Parent: D1 vol-regime break ALL_KILL → named next class

## Data
- G3 rates: `EA_CarryPublicRates/carry_rates_d1.csv` with V8 lags
  (+1 USD/EUR/GBP, +2 JPY).
- Broker SWAP_LONG/SHORT schedule: **GAP** (deal `swap` cols only).
  Funding = research proxy `|spot×carry%/365×nights|/pip` — not QFSI swap.

## Design 1 — Mon→Thu funding-proxy harvest
`HYP-FX3-CARRY-FUNDPROXY-MONTHU-HARVEST-001`
Monday H4≥08 UTC; |carry|≥0.5 pp; funding proxy ≥1.5
pip over 3 nights; hold with-carry to Thursday ≤16 UTC;
SL 1.8×ATR14_H4; ≤1/symbol ≤3 book.

## Design 2 — Flush then ride carry
`HYP-FX3-CARRY-FLUSH-MR-MULTIDAY-001`
|carry|≥0.35; 5d adverse move ≥1.0×ATR14_D1 ending
at flush extreme; enter WITH carry next H4; SL 1.6×ATR_H4;
RR=2.5; hold≤32 H4; ≤2 book.

## ≠ killed
≠ V8_CARRY_DIFF (Friday single winner); ≠ V8_CARRY_DAILY_RANK (deadband
long-max/short-min); ≠ V8_CARRY_RATE_EVENT_5BP; ≠ V8_CARRY_VOL_REGIME
(Menkhoff); ≠ USBILL slope→USD basket.

## If both fail — next object class
Microstructure only if research-grade cost exists; else greenfield
outside kill shelf (e.g. CME 6J spot−fwd basis gate) — not V8 carry retune,
not D1 breakout densify.
