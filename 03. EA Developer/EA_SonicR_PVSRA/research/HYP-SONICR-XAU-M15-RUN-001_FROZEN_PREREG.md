# HYP-SONICR-XAU-M15-RUN-001 — frozen tester-only

Status: `FROZEN_TESTER_ONLY`  
Object: XAUUSD M15 Sonic Classic wave, **first whole $10** at least **$20**.
Revision of killed WHQ-001. Thesis: Sonic trades the run, not the first $5
half magnet. Same entry. Not Monday salvage. Not year drop.

## Pair-specific

- Whole grid only: **$10** (`InpRoundWhole=10`). No half/quarter TP.
- Offset: 50 points = **$0.50**.
- SL cap: **$20**. Skip if wider.
- TP: first whole ≥ **$20** beyond pending (`InpMinTpPips=2000`).
- Session: London 08–16 and NY 12–17. Week cap 3. Day cap 2.
- Spread gate 500 points. Risk 0.25%. Magic `16081701`.

## Clock / windows

- Train: `2017.01.03`–`2023.12.31` (broker actual_from).
- OOS/holdout sealed as WHQ-001.
- Model 1 (1-minute OHLC). HQ >97. Tester-only.

## Kill

Fast-Kill if loser after HQ. No same-ID rescue. No hour/weekday salvage.
