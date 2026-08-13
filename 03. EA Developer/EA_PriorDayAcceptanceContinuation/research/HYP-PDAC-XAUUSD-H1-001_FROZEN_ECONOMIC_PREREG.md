# HYP-PDAC-XAUUSD-H1-001 — frozen economic preregistration

Status: `FROZEN_AFTER_SOURCE_PASS_BEFORE_MQL5_COMPILE_OR_OUTCOME_READ`

The exact source mapping and event population are inherited unchanged from the
source preregistration and source-result artifacts. No event threshold, clock,
direction or density rule may change.

## Execution and risk mapping

- Symbol/timeframe: native FivePercent `XAUUSD H1`.
- Decision: completed second H1 acceptance close `t`; entry only on the exact
  `t+1 hour` next-bar first tick.
- LONG invalidation stop: `prior_day_high - 0.25 * prior_day_range`.
- SHORT invalidation stop: `prior_day_low + 0.25 * prior_day_range`.
- If the normalized stop is not strictly on the protective side of the actual
  requested entry or violates broker geometry, consume and skip the event.
- Target: `1.50R` from actual requested entry; no trailing or break-even.
- Time exit: first tick after eight completed H1 bars.
- Position risk: `0.25%` of equity via `OrderCalcProfit`; volume rounds down to
  broker step. Margin/API/price failures fail closed.
- Maximum one owned symbol position; no pyramid or pending-order retry.
- Daily/account equity locks: `3.5%` and `8%`.
- No new Friday position; owned exposure flattens from 20:00 UTC Friday.
- Design baseline: `[2018-01-01, 2023-01-01)`, Model 0, current broker spread,
  100,000 USD, leverage 1:100, telemetry off.

## Acceptance

- Engineering: focused source-contract tests, fresh compile `0 errors / 0
  warnings`, non-repaint PASS, HQ strictly above 97%, fixed-window coverage and
  non-truncated journal.
- Economics at x1 broker cost: PF strictly above `1.30`, positive expectancy,
  completed cadence `2–5/week`, both directions at least 30%, no calendar year
  above 30%, and max relative DD at most 8%.
- Only after x1 passes: x1.5 PF at least 1.25 and x2 PF at least 1.00, then
  validation/OOS under a separately frozen plan.

One untuned baseline only. No optimization, threshold/period/session search,
direction deletion, stop/target/hold/risk change, or same-ID economic rescue is
authorized after reading the report.
