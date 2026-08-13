# HYP-ISDS-XAUUSD-M5-001 — frozen untuned economic baseline

Status: `FROZEN_BEFORE_MQL5_COMPILE_OR_OUTCOME_READ`

## Source-passed signal

At the complete 15:55 UTC M5 bar, compute the ordinary lag-1 Pearson
correlation of the 191 returns from the exact 00:00–15:55 session. Positive
correlation continues the 15:25–15:55 return sign; negative correlation fades
it. Zero/invalid values emit nothing. Source attempt `ISDS001-SOURCE-001`
passed at 1,275 executable events and 4.887733/week. Report SHA256 is
`F4706B9D62DCB250F35EF1C4ACE4E912646ED568CC94577F1D54EAABEFC5ED90`.

## Frozen execution mapping

- FivePercent XAUUSD, native M5, `[2018-01-01, 2023-01-01)`.
- Decision completed 15:55 UTC; entry only on first tick of exact 16:00.
- Require exactly 192 positive-volume, geometrically valid, contiguous bars.
- LONG stop is the minimum low of the 12 completed M5 bars ending 15:55 minus
  `0.20*ATR14`; SHORT uses maximum high plus the same buffer. ATR is closed-bar
  shift 1 at 16:00. Normalize stop outward to tick size.
- TP fixed `1.50R`; no trailing, break-even, partial or scale-in.
- Flatten at/after 20:00 UTC same day; no weekend hold.
- Risk `0.10%` current equity, rounded down by broker volume step using
  `OrderCalcProfit`; one symbol position, no pyramid.
- Entry locks `3.5%` daily / `8%` peak-equity drawdown. Missing data, price,
  ATR, geometry, margin or trade acceptance fails closed.
- FivePercent server UTC+2 winter / Europe-DST UTC+3.

## Sole baseline

Exactly one untuned AlphaFactory Model-0 run:

- EA `EA_IntradaySerialDependenceSwitch`, XAUUSD/M5;
- tester `2018.01.01..2023.01.01`, USD100,000, leverage 1:100, current broker
  spread and report commission;
- no rho threshold, alternate recent window, session/weekday/direction filter,
  stop/target/hold/risk change or optimization.

Minimum gates before validation: HQ>97%; PF>1.30; expectancy>0; 2–5 completed
trades per `1826/7` weeks; both directions >=30%; no year >30%; relative equity
DD<=8%. Later cost stress requires x1.5 PF>=1.25 and x2 PF>=1.00.

Compile/runtime/signal mismatch is engineering failure. Headline PF,
expectancy or cadence failure kills this exact object. Validation, holdout,
optimization, paper and live remain closed until the baseline and later gates
pass.
