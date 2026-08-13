# HYP-IRSK-XAUUSD-M5-001 — frozen source feasibility

Status: `FROZEN_BEFORE_SOURCE_READ_OR_OUTCOME_ACCESS`

## Thesis

The sign of a complete session return describes net displacement, while the
standardized third central moment of its 191 M5 log returns describes which
tail dominated the path. A strict disagreement is a fragile/exhaustion state:
fade a positive session with negative realized skewness and fade a negative
session with positive realized skewness at exact next 16:00.

This is a distribution-shape mechanism, not entropy, serial correlation,
semivariance/CLV, total volume, OBV, breakout or indicator voting. It uses
native FivePercent MT5 bars only; no paid data.

## Frozen mapping

- XAUUSD M5 DESIGN `[2018-01-01, 2023-01-01)`; exact complete 192-bar session
  from 00:00 through completed 15:55 UTC.
- Compute 191 log returns, their population mean, population second central
  moment `m2`, and population third central moment `m3`.
- `skew = m3 / m2^(3/2)`. Nonfinite or `m2<=0` is invalid. No bias correction,
  winsorization, threshold, lookback or normalization across days.
- LONG iff session return `<0` and skew `>0`; SHORT iff session return `>0`
  and skew `<0`. Equality emits nothing.
- Decision completed 15:55; exact-next availability 16:00. Next price is never
  read. No session subset, weekday, cooldown, outcome, cost or future return.

## Outcome-blind source gates

Design rows `>=300,000`; session/measurement and exact-next coverage `>=95%`,
`>=500` events, cadence `2..5/week`, each year `1.25..6.5/week`, each direction
`>=30%`, max year share `<=30%`, zero conflicts and deterministic replay.

Any failure parks this exact realized-skewness divergence fade. No sign
inversion, agreement event, threshold, moment estimator, session or timeframe
rescue is authorized. Outcomes/economics remain sealed.
