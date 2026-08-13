# MT5 Economic Calendar surprise — pre-hypothesis capability check

Status: `PRE_HYPOTHESIS_NO_SOURCE_ACCESS_NO_PRICE_OUTCOMES`.

## Why this lane is being checked

The prior macro-surprise idea was blocked because no free reproducible
point-in-time consensus archive had been verified. MetaTrader 5's built-in
Economic Calendar is a possible native cure: `CalendarValueHistory` exposes
trade-server timestamps and `MqlCalendarValue` stores actual, forecast, previous
and revised-previous values. This uses the existing demo terminal and requires
no paid data.

Primary references:

- https://www.mql5.com/en/docs/calendar/calendarvaluehistory
- https://www.mql5.com/en/docs/calendar
- https://www.mql5.com/en/articles/22196

The calendar API is not directly reproducible inside Strategy Tester. Any
surviving source must first be exported from the connected terminal and then
embedded or loaded as a SHA-bound static tester resource. Live and tester logic
must share the same event schema and time mapping.

## Stage-0 acceptance before any strategy ID

1. Export EUR and USD events for 2016–2022 without reading market prices.
2. Prove complete immutable fields for release timestamp, event identity,
   importance, actual, forecast, previous, revision and currency.
3. Fail closed on `LONG_MIN`, duplicate/conflicting IDs, ambiguous server→UTC
   mapping, missing event descriptions or unexplained revisions.
4. Establish whether the stored actual is the release-time value and whether
   forecast is the final pre-release consensus. If point-in-time semantics
   cannot be defended, stop the lane.
5. Build an outcome-blind high-importance numeric-event census. Require a raw
   2–5/week calendar supply across each year before defining price entry/exit.
6. Freeze an event-polarity allowlist from economic meaning before price access;
   do not infer beneficial direction from historical returns.

No source exporter, hypothesis, EA, paid request, price outcome, PF, optimizer,
validation, holdout, paper or live authority exists at this checkpoint.

