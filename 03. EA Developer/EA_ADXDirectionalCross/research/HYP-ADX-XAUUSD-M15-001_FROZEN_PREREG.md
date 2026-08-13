# HYP-ADX-XAUUSD-M15-001 — frozen preregistration

Status: `FROZEN_BEFORE_SOURCE_AND_OUTCOMES`.

## Market thesis

A fresh directional-movement regime begins when the native +DI/-DI polarity flips while the ADX strength line is already at the conventional 25 level and still rising. This is a trend-initiation object, not the prior ATR/EMA impulse-pullback object and not an oscillator extreme re-entry.

## Exact signal

- FivePercent `XAUUSD`, native `M15`, TRAIN `2018.01.01 <= time < 2023.01.01`, Model `0`.
- Native MT5 `iADX`, period `14`; buffers `0=ADX`, `1=+DI`, `2=-DI`.
- Closed bars only, using prior/current completed values.
- LONG: prior `+DI <= -DI`, current `+DI > -DI`, current ADX `>=25.0`, current ADX `> prior ADX`.
- SHORT: prior `+DI >= -DI`, current `+DI < -DI`, current ADX `>=25.0`, current ADX `> prior ADX`.
- Exact next native M15 open only (`+900` seconds); a gap consumes the event.
- One accepted entry per server calendar day. No EMA, session, weekday, volume, volatility, higher-timeframe or direction filter.

## Exit, risk and execution

- Structural stop: prior five completed M15 bars' extreme plus/minus `0.20 * ATR14`.
- Target `1.50R`; time exit `12` completed M15 bars.
- Risk `0.25%` equity; daily lock `3.5%`; peak-equity drawdown latch `8%`; Friday flatten hour `20`; no weekend hold.
- Stop/target are tick-normalized but never widened. BUY geometry is validated from Bid and SELL geometry from Ask; invalid signals are consumed once.
- Deposit `100000`, leverage `1:100`, current spread, commission captured from report. No optimization.

## De-dup boundary

Local search found ADX used as one component in `EA_ATRImpulsePullbackContinuation`, whose decision surface requires ATR impulse, EMA50 context and pullback release. This hypothesis uses the native DI polarity crossover as the atomic trigger and ADX strength/rise only; it has no ATR impulse or EMA gate. No exact pure DI-cross object was found in the canonical registry/failure catalog.

## Acceptance

Engineering gates precede metrics: compile 0E/0W, nonrepaint PASS, HQ>97/full fixed-window DQ, nontruncated journal, duplicate summaries identical, `runtime_failed=false`, zero fatal markers and reconciled positions/orders.

Only then require PF `>1.30` after costs, positive expectancy, cadence `2–5/week`, both directions `>=30%`, max calendar-year share `<=30%`, and DD `<=8%`. Failure kills this exact mapping; no post-hoc threshold/period/filter/session/SL-TP/daily-cap rescue. Validation/OOS/holdout stay sealed unless every baseline gate passes.
