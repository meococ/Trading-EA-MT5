# EA_ProspectiveCalendarPITMQDemo

A closed, one-attempt source-capability child of `EA_ProspectiveCalendarPIT`
for the already-configured local `MetaQuotes-Demo` runtime. It is not a
trading EA and does not authorize an economic hypothesis.

The child preserves the v1.5 `CalendarValueHistoryByEvent` catalog, query, and
diff logic. Its only behavioral changes are strict runtime guards and a fresh
Common Files namespace:

- hypothesis: `HYP-CALENDAR-PIT-MQDEMO-001`;
- required server: `MetaQuotes-Demo`;
- Strategy Tester and optimization: fail closed;
- EA Algo Trading permission: must remain off;
- price, order, and position APIs: forbidden;
- output root: `calendar_pit_mqdemo_001/`.

Acceptance requires all eight currencies and a
`FUTURE_DISCOVERY_HISTORY` followed by an `IDLE_PROOF_HISTORY` for the same
occurrence, with zero API, state, I/O, capacity, or gap errors. A pass proves
only prospective terminal observation capability. It does not prove official
first-public timing, historical point-in-time availability, expectancy, or
promotion readiness.

The 2026-08-13 attachment enumerated all 8/8 currencies, froze 1,051 event
definitions and 506 selected events, then returned `n=-1`, `api_error=5401`
on the first future-window `CalendarValueHistoryByEvent` call. No occurrence,
future proof, or idle proof was observed. Two further timer callbacks occurred
before the LiveUpdate modal/terminal shutdown completed and returned the same
error; this is a disclosed stop-timing protocol deviation, not a second
attachment or a rescue attempt. Final verdict:
`KILL_MQDEMO_CAPABILITY_CHILD`. Do not rerun or revise this child.
