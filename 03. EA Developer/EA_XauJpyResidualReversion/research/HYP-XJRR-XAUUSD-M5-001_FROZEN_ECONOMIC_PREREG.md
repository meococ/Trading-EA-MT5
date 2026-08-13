# HYP-XJRR-XAUUSD-M5-001 — frozen economic preregistration

Status: `FROZEN_BEFORE_MQL5_COMPILE_OR_OUTCOME_READ`

## Signal and execution

- XAUUSD M5 is the traded chart; USDJPY M5 is a synchronized read-only
  explanatory series. Use completed Bid bars only.
- Reproduce the authoritative source formula exactly: preceding 288 paired
  returns, no-intercept XAU-on-USDJPY beta, sample residual sigma and the
  prior/current two-sigma re-entry cross.
- The first raw cross per FivePercent server date consumes that date before
  exact-next, overlap, Friday or broker-geometry checks. After consumption,
  suppress the next 12 synchronized decision bars. No delayed entry.
- Entry is the first tick of the exact synchronized next M5 bar. Friday
  availability at or after 20:00 UTC is non-executable; flatten owned exposure
  from that boundary.
- LONG exits on the first completed residual `z >= 0`; SHORT on `z <= 0`.
  Hard time exit after 12 completed XAUUSD M5 bars. A trade present at the start
  of a decision bar may exit but may not reverse on that same tick.
- Protective stop is `1.25 * ATR14` from requested entry, normalized outward to
  tick size. No fixed TP, trailing stop or break-even.
- Risk `0.25%` of equity, broker-volume-step round-down, one owned XAUUSD
  position, no pending-order queue and no pyramid. Daily/account equity locks
  are `3.5% / 8%`.
- Attach/restart is fail-closed: reconstruct daily consumption and the 12-bar
  lock from closed synchronized history; never enter a historical event.

## Baseline contract and gates

- FivePercent XAUUSD, chart M5, design `[2018-01-01, 2023-01-01)`, Model 0,
  current spread, USD `100,000`, leverage `1:100`, telemetry profile `none`.
- Fresh focused tests, compile `0 errors / 0 warnings`, non-repaint PASS, HQ
  strictly above 97%, full fixed-window DQ and non-truncated journal.
- Runtime source counts must reconcile causally with the 1,290-event upper bound;
  every lost event must be classified as attach, exact-next, overlap, Friday,
  risk/geometry or order rejection.
- Baseline after broker spread and commission: PF strictly above `1.30`, positive
  expectancy, completed cadence `2–5/week`, max relative DD at most `8%`.
- Only after baseline passes: dynamic slippage/cost x1.5 requires PF at least
  `1.25`; x2 requires PF at least `1.00`; then freeze validation/OOS/holdout.

One untuned baseline only. No beta window, z threshold, quota, lockout, symbol,
session, weekday/direction, stop distance, exit, hold, risk or timeframe rescue
after outcomes.
