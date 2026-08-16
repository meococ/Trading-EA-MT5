# HYP-SONICR-XAU-M15-WHQ-001 — frozen tester-only

Status: `FROZEN_TESTER_ONLY`  
Object: XAUUSD M15 Sonic Classic wave, **gold** WHQ/ATR.  
Not EUR `001`. Not ITSM. Not Scout. Not PVSRA-as-entry.

## Pair-specific (why not EUR copy)

- Whole/half grid: **$10 / $5** (`InpRoundWhole=10`).
- Offset: 50 points = **$0.50** (`point=0.01`).
- SL cap: **$20** (2000 × 0.01). Skip if wider. Do not shrink.
- TP: first $5/$10 at least **$5** beyond pending.
- Session: London 08–16 **and** NY 12–17 London clock (gold prints in NY).
- Week cap **3** (Owner 1–3 / week). Day cap 2.
- Spread gate 500 points. Risk 0.25%.

## Clock / windows

- Train: `2016.01.01`–`2023.12.31` (request 2016; if HQ/bars fail, record actual_from).
- OOS: `2024.01.01`–`2025.06.30` sealed.
- Holdout: `2025.07.01`–`2026.08.16` sealed.
- Model **1** (1-minute OHLC): model 0 every-tick generate ~2%/25min on this portable; closed-bar pending logic is the object. Model 0 confirm only if this train survives PF/cadence. HQ >97, MetaQuotes-Demo portable. Not live.

## Kill

Fast-Kill if loser after HQ pass. No same-ID rescue. No hour salvage. No copy EUR 120-pip cap.
