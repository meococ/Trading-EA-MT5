# HYP-SONICR-XAU-H1-WHQ-001 — frozen tester-only

Status: `FROZEN_TESTER_ONLY`  
Object: **XAUUSD H1** Sonic Classic wave, gold WHQ.  
Not EUR M15 `001`. Not XAU M15 (tester 0 bars on smoke). Not ITSM.

## Pair-specific

- TF **H1** because MQ Demo M15 XAU smoke `20260816_233228` loaded 0 bars; H1 hcc exists 2012–2026.
- WHQ **$10**. Offset **$0.50**. SL cap **$20**. TP min runway **$5**.
- Session: London 08–16 + NY 12–17 (gold). Week cap **3**.
- PVSRA labels only. Scout off.

## Windows

- Train: `2016.01.01`–`2023.12.31`
- OOS/holdout sealed (2024+).
- HQ >97 required. Fast-Kill if loser after HQ.

Cadence target 1–3 / week. If N too low after HQ, do not densify with Scout/PVSRA.
