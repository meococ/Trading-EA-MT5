# Design memo — Greenfield book / XS / RV board

Date: 2026-07-15
Lane: single; no-Git; offline-first; `EXO_FRED_DISPLACE_SPAM_PAUSED`

## Problem

LNY EUR/GBP 3/3 KILL. Session/IB/ORB/coil/FRED/RR2-exit/COT boards exhausted.
Need true greenfield classes that can hit joint thick+cadence under +$12.

## Design 1 — XS USD residual fade book

`HYP-XS-USD-RESIDUAL-H1-FADE-BOOK-001`

**Thesis:** After a common-USD move, the pair with extreme residual vs equal-weight
factor mean-reverts; concentrate book on top |z| once/day.

**Frozen:** universe EUR/GBP/AUD/USDJPY; ret=24H1; z_lb=60; |z|≥1.5; fire UTC16;
SL=1.2 ATR; RR=2; max_hold=24; enter next open; 1 trade/day.

## Design 2 — XS USD momentum top1 book

`HYP-XS-USD-MOM-H1-TOP1-BOOK-001`

**Thesis:** When |factor_z|≥0.75, continue USD factor via the strongest aligned pair.

**Frozen:** same universe; factor mean of signed 24H1 returns; fire UTC16;
SL=1.2 ATR; RR=2; max_hold=24; 1 trade/day.

## Design 3 — AUD–NZD residual Z-MR

`HYP-AUDNZD-H1-RESIDUAL-ZMR-001`

**Thesis:** AUD vs NZD log-spread extremes mean-revert (commodity-dollar RV).

**Frozen:** spread=ln(AUDUSD)−ln(NZDUSD); z_lb=48; |z|≥2; fire UTC12;
trade AUDUSD leg; SL=1.5 ATR; RR=1.5; max_hold=36; 1/day.

## Model 0 policy

Only if offline `PROBE_SURVIVOR`. Else withhold. No Real stall required.
