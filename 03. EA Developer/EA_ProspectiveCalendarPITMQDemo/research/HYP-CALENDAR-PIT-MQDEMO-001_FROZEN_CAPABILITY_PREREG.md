# HYP-CALENDAR-PIT-MQDEMO-001 — frozen capability preregistration

Frozen before compile or attachment on 2026-08-13 (Asia/Saigon).

## Question

Can the already-configured local MetaTrader 5 runtime, when connected to
`MetaQuotes-Demo`, prospectively expose one future economic-calendar
occurrence through `CalendarValueHistoryByEvent` and return the same unchanged
occurrence on the immediately forced follow-up query?

## Fixed scope

- Source lineage: byte-identical v1.5 catalog/query/diff logic from
  `EA_ProspectiveCalendarPIT`.
- Runtime: `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable`.
- Required account server: exact `MetaQuotes-Demo`; existing configured account
  only. No account creation and no login automation.
- Mode: live terminal attachment only; Strategy Tester and optimization fail
  closed; terminal and EA Algo Trading permissions remain off.
- Data surface: MetaQuotes Economic Calendar only. No chart prices, ticks,
  symbols, orders, positions, deals, or outcome series.
- Currencies: USD, EUR, JPY, GBP, CHF, CAD, AUD, NZD.
- Namespace: `FILE_COMMON/calendar_pit_mqdemo_001/`; no reuse of v1.1-v1.5
  state.
- Attempt budget: one attachment, at most 48 hours, stopping after the first
  accepted pair or the first fatal contract violation.

## Acceptance gate

All conditions are mandatory:

1. exact server and safety fields on every JSONL record;
2. country/catalog enumeration succeeds for all 8/8 currencies;
3. one `FUTURE_DISCOVERY_HISTORY` record exists;
4. a later `IDLE_PROOF_HISTORY` exists for the same `event_id`, `value_id`,
   `scheduled_unix`, `period_unix`, and `payload_hash`;
5. `api_errors=0`, `gaps=0`, and no `API_ERROR`, `GAP_*`, `STATE_*`,
   `IO_ERROR`, or capacity error record exists;
6. `outcome_accessed=false`, `prices_read=false`, `orders=false`, and
   `trading_disabled=true` throughout.

## Fixed verdicts

- Pass: `ADMISSIBLE_MQDEMO_CAPABILITY_CHILD`. This is engineering evidence for
  prospective terminal collection only.
- Any server, permission, catalog, Calendar API, state, I/O, capacity, or gap
  failure: `KILL_MQDEMO_CAPABILITY_CHILD`. No second attachment or source
  revision is permitted under this ID.
- Timeout without an accepted pair: `INCOMPLETE_PROSPECTIVE_SAMPLE`; it is not
  evidence of an economic failure or edge.

No outcome, price, backtest, EA economics, or promotion claim is authorized by
this preregistration.
