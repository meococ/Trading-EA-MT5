# EA_ProspectiveCalendarPIT

Terminal engineering package for a prospective MetaQuotes Economic Calendar
source. It is retained as a fail-closed capability receipt, not as a trading EA.

Version 1.5.0 enumerates the preregistered USD, EUR, JPY, GBP, CHF, CAD, AUD,
and NZD event definitions, freezes the moderate/high-importance catalog, and
attempts one bounded `CalendarValueHistoryByEvent` future-window query per timer
callback. It reads no chart prices, submits no orders, and refuses Strategy
Tester or optimization mode.

Versioned outputs are append-only UTF-8 files under terminal Common Files:

- `calendar_pit/calendar_pit_v15.csv`
- `calendar_pit/calendar_pit_v15.jsonl`
- `calendar_pit/catalog_state_v15.txt`
- `calendar_pit/occurrence_v15.txt`
- `calendar_pit/event_catalog_v15.csv`
- `calendar_pit/countries_v15.txt`

The receive clock is terminal observation time (`ts_local` plus monotonic
`tick64`), never official first-public time. Raw `MqlCalendarValue` numeric
fields remain million-scaled integers, and missing `LONG_MIN` values serialize
as null.

Acceptance required both a `FUTURE_DISCOVERY_HISTORY` receipt and a later
`IDLE_PROOF_HISTORY` for the same occurrence, with no API, state, I/O, capacity,
or gap error. The local FivePercent runtime did not meet that contract:

- catalog discovery: 8/8 currencies, 1,051 definitions, 506 selected events;
- frozen catalog hash: `1183765039875304157`;
- first two bounded History calls: `n=-1`, `api_error=5401`;
- accepted future occurrences, idle proofs, observations, mutations: all zero;
- runtime auditor v4: `FAIL`.

Earlier v1.1-v1.4.1 `CalendarValueLast*` paths also failed after successful
priming. Therefore the exact terminal verdict is `KILL_CALENDAR_LANE`. Do not
create another Calendar API revision, infer a point-in-time historical tape, or
open a trading hypothesis from this package.

Status: `engineering-invalid source path / terminal Calendar lane`; no economic
edge, validation, promotion, paper-trading, or live-trading authority.
