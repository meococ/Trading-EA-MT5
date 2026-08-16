# HYP-SONICR-XAU-M15-PULL-002 — frozen tester-only

Status: `FROZEN_TESTER_ONLY`  
Object: XAUUSD M15 Dragon-mid tag in **4 bars** + reclaim. Cadence revision
of PULL-001 (0.16/wk). Same whole $20 TP. Not Classic. Not Europe salvage.

## Pair-specific

- Tag window 4 (`InpMaxPullbackAge=4`); prior bar at window edge not already on mid.
- Reclaim close through mid with candle in trend; still inside Dragon band.
- SL last two bars. TP first whole ≥ $20. Magic `16081703`.

## Clock

Train 2017.01.03–2023.12.31 Model 1. OOS/holdout sealed.

## Kill

Fast-Kill if loser after HQ. No weekday/session salvage.
