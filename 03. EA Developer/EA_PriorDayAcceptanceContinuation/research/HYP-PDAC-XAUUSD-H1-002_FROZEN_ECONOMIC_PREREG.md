# HYP-PDAC-XAUUSD-H1-002 — frozen economic preregistration

Status: `FROZEN_BEFORE_HYP002_COMPILE_OR_OUTCOME_READ`

Parent HYP001 was parked before MT5 because its all-Friday entry ban made the
source-feasible event population structurally under-cadence and its attach
clock was not fail-closed. HYP002 changes only those two engineering rules.

## Source and execution mapping

- Inherit the exact HYP001 prior-day, first two-close acceptance event without
  changing a price condition, timeframe or direction rule.
- Block a new position only from Friday 20:00 UTC; earlier Friday events remain
  eligible. Flatten any owned exposure from Friday 20:00 UTC.
- On initialization, seed the current H1 open and do not process its preceding
  decision. This deliberately skips an ambiguous attach-time event rather than
  entering after the first tick. The chronological same-day rescan prevents a
  previously consumed daily event from firing later after restart.
- Entry: first tick of the exact next H1 bar.
- LONG stop: `prior_day_high - 0.25 * prior_day_range`; SHORT exact inverse.
- Target `1.50R`; time exit after eight completed H1 bars; no trail/break-even.
- Risk `0.25%` equity, broker-step round-down, one symbol position, no pyramid.
- Daily/account equity locks: `3.5% / 8%`.
- Design `[2018-01-01, 2023-01-01)`, Model 0, current spread, USD100,000,
  leverage 1:100 and telemetry off.

## Gates

- Source-aligned population must independently pass at least 500 events,
  2–5/week, both directions at least 30%, max-year share at most 30%, every
  year 1.25–6.5/week and inherited exact-next coverage at least 97%.
- Fresh tests, compile 0/0, non-repaint PASS, HQ strictly above 97%, full fixed
  window and non-truncated journal.
- Baseline x1: PF strictly above 1.30, positive expectancy, completed cadence
  2–5/week and max relative DD at most 8%.
- Only after x1 passes: cost x1.5 PF at least 1.25 and x2 PF at least 1.00,
  followed by separately frozen validation/OOS.

One untuned baseline. No session/weekday/direction deletion, price threshold,
stop/target/hold/risk change, optimization or same-ID rescue after outcomes.
