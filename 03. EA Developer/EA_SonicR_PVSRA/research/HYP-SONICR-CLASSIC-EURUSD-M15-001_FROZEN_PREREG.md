# HYP-SONICR-CLASSIC-EURUSD-M15-001 — frozen tester-only contract

Status: `FROZEN_TESTER_ONLY`  
Object: closed-bar **ClassicWaveLeg3DragonBreak** on EURUSD M15.  
Not XAU cell. Not ITSM. Not Hybrid. Not Scout. Not PVSRA-only.

## Mechanism

EURUSD M15. After a completed bar (`shift >= 1`; `iTime(...,0)` new-bar only):

- Wave long: L–H–HL, Low0 below Dragon low. Short: H–L–LH, High0 above Dragon high.
- Trigger: first close beyond outer Dragon after HL/LH, same-color candle.
- Trend soft: close vs EMA89. Dragon mid[t] vs mid[t-3] same side.
- Entry: BuyStop/SellStop 3 pips beyond signal extreme. TTL 4 M15 bars.
- SL: beyond leg-1 extreme −/+ 0.10 ATR. Skip if > 120 pips. Do not shrink.
- TP: first whole/half at least 15 pips beyond pending. Skip if none.
- Session: London 08:00–16:00 Europe/London (TimeGMT + UK DST). Asia off. NY off.
- Flatten Friday 20:00 London and weekend. Weekday overnight lawful.
- One position. PVSRA labels only. Scout compile-off.

## Envelope

- MetaQuotes-Demo portable. Tester current spread. Not FivePercent. Not live.
- Train `2018.01.01`–`2023.12.31`. OOS/holdout sealed.
- HQ >97 required before economics. Fast-Kill if loser after HQ pass.
- No same-ID market-logic rescue. No XAU copy. No Scout/PVSRA-only rescue.
