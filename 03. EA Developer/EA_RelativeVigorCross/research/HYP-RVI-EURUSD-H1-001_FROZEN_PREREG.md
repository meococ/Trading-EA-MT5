# HYP-RVI-EURUSD-H1-001 — frozen source-feasibility preregistration

Status: `FROZEN_PRE_SOURCE_SCAN`

## Independent mechanism

This is a fresh close-versus-range vigor crossover on EURUSD H1. It is
materially distinct from STC's double-stochastic EMA momentum and Mass Index's
range-bulge completion. Repository de-dup found no existing iRVI/Relative Vigor
object.

Formula provenance:

- TradingView Relative Vigor Index documentation:
  `https://www.tradingview.com/support/solutions/43000591593-relative-vigor-index/`.
- MetaQuotes native iRVI documentation:
  `https://www.mql5.com/en/docs/indicators/irvi`.
- Exact offline parity source is the terminal-shipped MetaQuotes example
  `02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Indicators/Examples/RVI.mq5`,
  SHA256 `AB6F66E19B0FDB1D1DA81CE42DA5D41C6C978607B2BE78B6EAFBE09C4E378DC0`.

TradingView is research provenance only; the MetaQuotes formula and later MT5
native buffer parity are authoritative.

## Frozen source mapping

- Source: `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_H1_2015_now.parquet`,
  SHA256 `71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08`.
- Read native closed H1 bid bars from 2015 prehistory through
  `2021.01.01` exclusive; score `2016.01.04 <= t < 2021.01.01` only.
- Period `N=10`.
- For bar i, weighted numerator
  `(C_i-O_i)+2(C_i-1-O_i-1)+2(C_i-2-O_i-2)+(C_i-3-O_i-3)`.
- Weighted denominator is the same `1,2,2,1` construction from `(H-L)`.
- Main RVI is sum of the last 10 weighted numerators divided by the sum of the
  last 10 weighted denominators. Denominator `<=0` or invalid fails closed.
- Signal is `(RVI_i + 2*RVI_i-1 + 2*RVI_i-2 + RVI_i-3) / 6`.
- LONG iff prior main `<=` prior signal, current main `>` current signal, and
  current main and signal are both strictly below zero.
- SHORT iff prior main `>=` prior signal, current main `<` current signal, and
  current main and signal are both strictly above zero.
- Completed H1 bar only; availability is the exact next native H1 timestamp
  `+3600s` and must remain inside DESIGN. Inspect no next-bar price.
- No session, weekday, ATR, HTF, volume, cooldown, debounce, stop, target or
  outcome field. Normal market closures do not reset bar-count lookbacks.

## Outcome-blind source gates

- Source SHA/schema/order/geometry and deterministic replay pass.
- DESIGN rows `>=25,000`; usable coverage `>=99%` after exact warmup.
- Executable candidates `>=500`; pooled cadence `2-5/week`.
- LONG and SHORT each `>=30%`; no year `>35%` of candidates.
- Each year cadence `1.25-6.5/week`; zero conflicts.

Any failed gate parks this exact mapping only. No threshold/period/timeframe/
session/cooldown rescue or same-ID scan. Only a source pass may authorize one
EA build and untuned Model-0 DESIGN baseline under a separately frozen risk
contract.
