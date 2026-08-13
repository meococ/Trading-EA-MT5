# HYP-IVRL-XAUUSD-M5-001 — frozen source feasibility

Status: `FROZEN_BEFORE_SOURCE_READ_OR_OUTCOME_ACCESS`

## Thesis

A session whose realized variance relocates from its early half into its late
half represents a late information-arrival regime. Continue the direction of
the late-half displacement at the exact 16:00 availability bar.

This is a time-of-variance mechanism, not entropy, skewness, serial
correlation, volume/OBV, breakout or indicator voting. It uses native
FivePercent MT5 bars only; no paid data.

## Frozen mapping

- XAUUSD M5 DESIGN `[2018-01-01, 2023-01-01)`; exact complete 192-bar session
  from 00:00 through completed 15:55 UTC.
- Compute all 191 adjacent log returns.
- Early segment is exactly return destinations 00:05..07:55: `r[0:95]`, 95
  returns. Late segment is exactly destinations 08:00..15:55: `r[95:191]`,
  96 returns; the 07:55→08:00 return belongs to late.
- For each segment compute mean squared log return about zero. No demeaning,
  annualization, threshold, normalization across days or lookback.
- Candidate iff late mean squared return is strictly greater than early.
- Late displacement is exactly `ln(close[15:55]/close[07:55])`, matching the
  sum of the 96 late returns. LONG iff positive; SHORT iff negative. Equality
  emits nothing.
- Decision completed 15:55; exact-next availability 16:00. Next price is never
  read. No session subset, weekday, cooldown, outcome, cost or future return.

## Outcome-blind source gates

Design rows `>=300,000`; session/measurement and exact-next coverage `>=95%`,
`>=500` events, cadence `2..5/week`, each year `1.25..6.5/week`, each direction
`>=30%`, max year share `<=30%`, zero conflicts and deterministic replay.

Any failure parks this exact variance-relocation continuation. No ratio
threshold, split-time, sign inversion, session or timeframe rescue is
authorized. Outcomes/economics remain sealed.
