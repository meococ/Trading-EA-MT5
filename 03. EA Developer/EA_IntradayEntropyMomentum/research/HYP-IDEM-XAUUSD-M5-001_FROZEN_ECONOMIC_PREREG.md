# HYP-IDEM-XAUUSD-M5-001 — frozen untuned economic baseline

Status: `FROZEN_BEFORE_MQL5_COMPILE_OR_OUTCOME_READ`

## Source-passed signal

At completed 15:55 UTC, compute binary sign entropy from the 191 log returns
of the exact complete 00:00–15:55 M5 session. If current entropy is strictly
below the ordinary median of the prior 20 valid complete sessions, continue
the sign of the full-session return at exact next 16:00. Source attempt
`IDEM001-SOURCE-001` passed with 638 events and `2.445783/week`.

## Frozen execution mapping

- FivePercent XAUUSD native M5, `[2018-01-01, 2023-01-01)`.
- Decision completed 15:55 UTC; entry only at exact next 16:00.
- Require the same complete 192-bar session and exact entropy/median formula as
  the source prereg. Current day is excluded from the prior-20 median.
- LONG stop: minimum low of 12 completed M5 bars ending 15:55 minus
  `0.20*ATR14`; SHORT symmetric maximum plus buffer. ATR is closed shift 1.
- Normalize stop outward. Target is fixed `1.50R`, rounded outward to tick
  size. No trailing, break-even, partial, scale-in or retry.
- Flatten at/after 20:00 UTC; no weekend hold. Risk `0.10%` current equity;
  one position; daily/account entry locks `3.5%/8%`.
- Missing data, clock, ATR, geometry, margin or broker acceptance fails closed.

## Sole baseline and gates

Exactly one untuned AlphaFactory Model-0 run: XAUUSD/M5,
`2018.01.01..2023.01.01`, USD100,000, leverage 1:100, current broker spread
and report commission. No entropy/median/session/direction/stop/target/hold/risk
change or optimization.

Minimum gates before validation: HQ>97%; PF>1.30; expectancy>0; 2–5 completed
trades per `1826/7` weeks; both directions >=30%; no year >30%; relative equity
DD<=8%. Later cost stress: x1.5 PF>=1.25 and x2 PF>=1.00.

Engineering mismatch is not an economic verdict. PF, expectancy or cadence
failure kills this exact object. Validation, holdout, optimization, paper and
live remain closed until all gates pass.
