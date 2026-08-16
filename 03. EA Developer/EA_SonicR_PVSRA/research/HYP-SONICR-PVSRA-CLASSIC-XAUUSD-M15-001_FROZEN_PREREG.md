# HYP-SONICR-PVSRA-CLASSIC-XAUUSD-M15-001 — frozen tester-only contract

Status: `FROZEN_TESTER_ONLY`  
Object: closed-bar **Classic Sonic R** (Dragon + Trend + wave) with a **PVSRA qualifier** on XAUUSD M15.  
Not archived `EA_SonicR`. Not Hybrid ICT-Sonic. Not Scout. Not PVSRA-only.

## Mechanism

XAUUSD M15. After a completed bar (`CopyRates` / `CopyBuffer` shift >= 1; `iTime(...,0)` only as new-bar gate):

- Trend: close vs EMA89 and EMA89 slope same direction.
- Dragon: EMA34 high / close / low. Mid slope in ATR units must exceed `InpDragonMinSlopeAtr` in Trend direction.
- Wave: last swing pullback into the Dragon band, then a closed break or reject in Trend direction. Overlap ratio above `InpMaxOverlapRatio` is choppy and rejected.
- PVSRA qualifier only: tick volume vs average of the prior **10** closed bars (reconstructed). Rising or climax **with** the breakout is `support`. Default `InpRequirePvsraSupport=false` so the first object is Classic geometry, not a volume AND-gate. Hard veto is only climax **against** the trade. PVSRA cannot open a trade alone.
- S/R runway: block if close is within `InpSrRunwayAtr` × ATR of the next whole/half level in trade direction.
- Session: London or NY kill zone only, clocked from `TimeGMT` + UK DST (last Sunday March 01:00 GMT through last Sunday October 01:00 GMT; reconstructed). No new entries Friday after `InpFridayFlattenHour` London. Flatten after NY end, on Friday flatten hour, and before the weekend. No weekend hold. Overnight only if the weekday hold window is widened by input.
- Entry: market at next bar open. One position. Magic-bound. No scale-in, grid, martingale, or Scout.
- Risk: hard SL default beyond Dragon opposite side / last swing; SL floor N× spread; TP **1.0R**. Optional time stop. Daily loss and account DD locks.

PVSRA thresholds `1.5×` rising and `2.0×` climax are **reconstructed inputs** (Traders Reality / later PVA clones), not original TAH/Kyaw numbers.

## Envelope / cost / clock

- Symbol: MetaQuotes-Demo `XAUUSD`
- Period: M15
- Cost source: **MetaQuotes-Demo** tester current spread. MQ Demo ≠ FivePercent. Not live-equivalent.
- Portable: `02. AlphaFactory/runtime/mt5-portable-mqdemo` / server `MetaQuotes-Demo`
- Model 0 when a later task authorizes it. This freeze does not authorize a run.
- Deposit 10000, leverage 100, risk 0.25%/trade
- HQ **>97** required before any economic read.
- FivePercent portable / live account not mutated.
- DD lock 8% stays.

## Windows (holdout sealed)

- Smoke (engineering only): `2023.01.03`–`2023.01.17`
- Train: `2018.01.01`–`2023.12.31`
- OOS: `2024.01.01`–`2025.06.30` (sealed until freeze of a run config)
- Holdout: `2025.07.01`–`2026.08.15` (sealed; do not read)

## Kill

Fast-Kill if a later authorized Model 0 is engineering-valid and still a loser after HQ pass on train. No holdout. No same-ID market-logic rescue. No Scout or PVSRA-only rescue. No 1.5R / daily-flat salvage.
