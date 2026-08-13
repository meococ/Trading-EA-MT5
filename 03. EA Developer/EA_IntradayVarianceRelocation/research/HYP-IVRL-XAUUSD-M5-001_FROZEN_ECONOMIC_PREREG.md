# HYP-IVRL-XAUUSD-M5-001 — frozen untuned economic baseline

Status: `FROZEN_BEFORE_OUTCOME_READ`

## Frozen source-passed signal

At completed 15:55 UTC, compute the exact 95 early and 96 late adjacent M5 log
returns of a complete 00:00–15:55 session. If the late mean squared log return
is strictly greater than the early mean squared log return, continue the sign
of `ln(close[15:55]/close[07:55])` at exact next 16:00. The bound source
attempt produced 1,196 executable events and `4.584885/week` without outcomes.

## Frozen execution mapping

- FivePercent XAUUSD native M5, `[2018-01-01, 2023-01-01)`; no paid data.
- Decision completed 15:55 UTC; entry only at exact next 16:00.
- LONG/SHORT structural stop: 12 completed M5 bars through 15:55 plus outward
  `0.20*ATR14`; ATR uses closed shift 1.
- Fixed `1.50R` target rounded outward to tick size; no trailing, break-even,
  partial, scale-in, filter, cooldown or parameter search.
- Flatten is due at/after 20:00 UTC and on day roll; a broker rejection is
  retried only on a later native M5 bar.
- Risk `0.10%` equity, one position, daily/account entry locks `3.5%/8%`.
- Missing data, clock, ATR, geometry, margin or broker acceptance fails closed.

## Sole baseline and gates

Exactly one AlphaFactory Model-0 run: XAUUSD/M5, `2018.01.01..2023.01.01`,
USD100,000, leverage 1:100, current broker spread and report commission.

Engineering gates precede economics: HQ>97%, journal not truncated, exactly
1,196 raw signals with 607 LONG/589 SHORT, `runtime_failed=false`, and direct
entry/close/risk-lock reconciliation. Economic gates are PF>1.30 after costs,
expectancy>0, 2–5 completed trades per `1826/7` weeks, both directions >=30%,
no year >30%, and relative equity DD<=8%. Only after baseline pass may x1.5
cost PF>=1.25 and x2 PF>=1.00 be evaluated. Validation, holdout, optimization,
paper and live remain closed.
