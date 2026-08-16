# HYP-SONICR-EURUSD-M15-PULL-001 — frozen tester-only

Status: `FROZEN_TESTER_ONLY`  
Object: EURUSD M15 Dragon-mid tag + reclaim. **Not** Classic EUR `001`.
Pair-specific: London only, EUR pip grid. Not gold copy.

## Pair-specific

- Whole **0.01** (big figure). Min TP **30 pips**. SL cap **40 pips**.
- Offset 10 points (1 pip on 5-digit). Spread gate 30 points.
- Session: London 08–16 only (`UseNy=false`). TTL 4 M15 bars.
- Magic `16081801`. Risk 0.25%. Week 3 / day 2.

## Clock

Train 2017.01.03–2023.12.31 Model 1. OOS/holdout sealed. HQ >97.

## Kill

Fast-Kill if loser after HQ. No Classic 001 revive. No weekday salvage.
