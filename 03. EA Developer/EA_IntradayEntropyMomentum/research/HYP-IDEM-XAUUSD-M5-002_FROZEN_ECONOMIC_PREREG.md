# HYP-IDEM-XAUUSD-M5-002 — frozen untuned economic baseline

Status: `FROZEN_BEFORE_REVISION_COMPILE_OR_OUTCOME_READ`

Parent engineering failure: `HYP-IDEM-XAUUSD-M5-001`. No admissible economic
result was produced. The only revision is lifecycle telemetry control: a
required flatten is attempted at most once per native M5 bar, remains pending
until accepted, and is reconciled with `close_attempts`, `close_rejects`, and
`closes` counters. This is not a filter, session change, exit-time change, or
outcome-informed rescue.

## Frozen source-passed signal

At completed 15:55 UTC, compute binary sign entropy from the 191 log returns of
the exact complete 00:00–15:55 M5 session. If current entropy is strictly below
the ordinary median of the prior 20 valid complete sessions, continue the sign
of the full-session return at exact next 16:00. The bound source attempt
`IDEM001-SOURCE-001` produced 638 events and `2.445783/week` without outcomes.

## Frozen execution mapping

- FivePercent XAUUSD native M5, `[2018-01-01, 2023-01-01)`.
- Decision completed 15:55 UTC; entry only at exact next 16:00.
- LONG/SHORT structural stop: 12 completed M5 bars through 15:55 plus outward
  `0.20*ATR14`; ATR uses closed shift 1.
- Fixed `1.50R` target rounded outward to tick size; no trailing, break-even,
  partial, scale-in, filter, cooldown, or parameter search.
- Flatten remains due at/after 20:00 UTC and on day roll. A broker rejection is
  retried only on a later native M5 bar; the position is not abandoned.
- Risk `0.10%` equity, one position, daily/account entry locks `3.5%/8%`.
- Missing data, clock, ATR, geometry, margin or broker acceptance fails closed.

## Sole revision baseline and gates

Exactly one AlphaFactory Model-0 run: XAUUSD/M5, `2018.01.01..2023.01.01`,
USD100,000, leverage 1:100, current broker spread and report commission.

Engineering gates precede economics: HQ>97%, journal not truncated, exactly
638 raw signals with 344 LONG/294 SHORT, `runtime_failed=false`, and direct
entry/close/risk-lock reconciliation. Economic gates are PF>1.30 after costs,
expectancy>0, 2–5 completed trades per `1826/7` weeks, both directions >=30%,
no year >30%, and relative equity DD<=8%. Only after baseline pass may x1.5
cost PF>=1.25 and x2 PF>=1.00 be evaluated. Validation, holdout, optimization,
paper and live remain closed.
