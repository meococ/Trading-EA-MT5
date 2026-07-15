# Dedup — H1 ATR Regime Mom vs VolExp / Chop / Stretch / ORB shelf

Date: 2026-07-14  
Verdict: `INTAKE_CLEARED / INDEPENDENT`

## Candidate

`HYP-H1-ATR-REGIME-MOM-001` / `EA_H1ATRRegimeMom` — H1 only; trade when
`ATR14 / SMA50(ATR) ≥ 1.20` and closed `bar[1]` close is on the EMA50 side
(continuation). Mon–Thu, weekend flat, risk 0.5%.

## Contrast table

| Family | Mechanism | Relation |
|---|---|---|
| VolExp M15 (KILL) | Single-bar range expansion breakout | **H1 ATR-ratio regime gate + EMA side; not M15 break** |
| ChopTrend / CI (KILL) | Choppiness Index trend gate | **ATR slow-ratio, not CI** |
| EMA Stretch Fade (KILL) | Mean-revert when |C−EMA|/ATR large | **Opposite: continuation in elevated vol** |
| Keltner Squeeze (KILL) | Squeeze → breakout | **No channel/squeeze construct** |
| ORB / PDH / NY / Spark / FailedORB | Session/level range objects | **No OR / PDH / Asian range** |
| ITSM / H4Ribbon | EMA-zone pullback entry | **No pullback-to-EMA entry; regime+side only** |
| LinReg / HA / KAMA momentum seeds | Indicator slope/color | **ATR regime + EMA side only** |

## Independence claim

Higher-TF volatility-regime filter plus simple directional continuation.
Owner-allowed surface (vol regime + directional; not stretch-fade). Not a
cosmetic rename of any killed M15 fade/break book.

## Banned after readout

Do not mine ATR ratio, EMA period, hour/day vetoes, or flip to mean-reversion.
