# Prospective Calendar collection engineering receipt

Date: 2026-08-13

Authority: source-capability engineering only. This packet does not authorize a
trading hypothesis, EA economics, promotion, paper trading, live trading, or a
historical point-in-time claim.

## Frozen scope

- MT5 build 6090, account server `FivePercentOnline-Real`.
- XAU/Forex support universe only: USD, EUR, JPY, GBP, CHF, CAD, AUD, NZD.
- No chart prices, market outcomes, orders, BTC research, paid source, or Git
  dependency.
- Receive time means terminal observation time, never official first-public
  time.

## Build and static evidence

- Source: `EA_ProspectiveCalendarPIT.mq5`.
- Source SHA256:
  `5F7D77CA8528DC779DFA05F59E93E44F65E5E52BCB77A9C3D3577237E13D40D5`
  for v1.4.1.
- EX5 SHA256:
  `F8D21FB88F2ACA2C37B45D0A94737C1EFC4423AA21953C6F3E4CDEBDF2214179`
  for v1.4.1; deployed runtime copy matched exactly.
- AlphaFactory/MetaEditor receipt: `0 errors, 0 warnings`, 107,718-byte EX5.
- Local tests after the v1.4.1 state fix: `13 passed in 0.11s`.
- Algo Trading permission remained unchecked. The source is tester fail-closed
  and contains no trading or price-reading API.

## Runtime lineage and verdicts

1. v1.1-v1.3 used `CalendarValueLast` globally or by currency. Prime succeeded,
   but post-prime delta calls repeatedly blocked for about 50 seconds and
   returned `5401`. v1.3 stopped with seven errors and zero VALUE rows.
2. v1.4.0 moved to `CalendarValueLastByEvent`. An input reinitialization exposed
   a missing global counter reset: state doubled from 1,051 to 2,102 entries and
   produced zero event IDs. That tape is invalid and retained only as forensic
   engineering evidence.
3. v1.4.1 isolated fresh `*_v141.*` files, reset globals before state load, and
   failed closed on corrupt/zero/duplicate state. Deliberate input reinit proved
   `events_loaded=1051`, not 2102, with `primed_loaded=26` and no zero IDs.
4. Exact discovery then completed 8/8 currencies and 1,051 deduplicated event
   definitions. All 1,051 `change_id=0` calls returned `n=0`, `err=0`, and
   `change_id=277538048`.
5. The first two post-prime `CalendarValueLastByEvent` calls, for event IDs
   `840010001` and `840010002`, each returned `n=-1`, `api_error=5401` after the
   server timeout. Both receipts record `cursor_advanced=false`. There were zero
   VALUE and zero IDLE_PROOF rows.

Authoritative v1.4.1 runtime hashes:

- `calendar_pit_v141.jsonl`:
  `13D00658F5472405389C7CD04D849A8DBCEBF4919E25A2C59FF299A58371BE4B`
- `event_state_v141.txt`:
  `632469F61DC5167705D4E032D1C124496B4EF9CEE29AAB098220A9369BD1FA3F`

Auditor v3 verdict: `FAIL`; 1,051/1,051 durable events primed, two current-session
API errors, no post-prime acceptance evidence. Final engineering verdict:
`KILL_RUNTIME_CALENDAR_LAST_UNAVAILABLE_ON_SERVER`.

## Successor boundary (preregistered before v1.5)

Grok red-team and Lead allow exactly one materially different Calendar API
attempt: a prospective scheduled snapshot-diff watcher using
`CalendarValueHistoryByEvent`. The local terminal previously proved that the
History API can return 93,751 rows across 1,026 events, while every `Last*`
variant failed post-prime. The successor must use fresh versioned files and pass
a future-window History call plus a second unchanged-payload proof. Past-only
History, a forecast snapshot alone, any API/gap/state error, or inability to
observe the same future occurrence twice kills the Calendar lane.

## v1.5.0 terminal successor result

- Source SHA256:
  `63A63AEEB51FB6B63C08753A56C614D05B03FF1F0D26A12057B35E896E9FA35C`.
- EX5 SHA256:
  `CF01AFD532BC6D445D3E532B06DF56108570C6EA114CAA00E5B9406D6E6E3B92`;
  deployed runtime copy matched exactly.
- AlphaFactory/MetaEditor receipt: `0 errors, 0 warnings`, 114,832-byte EX5.
- Local source/runtime tests after auditor v4: `16 passed in 0.16s`.
- Runtime discovered all 8 currencies and 1,051 event definitions, selected 506
  moderate/high definitions, and froze catalog hash `1183765039875304157`.
- The first two bounded future-window `CalendarValueHistoryByEvent` calls, for
  event IDs `840010001` and `840010002`, each returned `n=-1` and
  `api_error=5401`. No cursor or occurrence state advanced.
- Shutdown receipt: zero future History successes, idle proofs, observations,
  mutations and gaps; two API errors. The watcher was removed from the chart.
- Runtime auditor v4 verdict: `FAIL`; selected event count 506, occurrence count
  zero, `future_history_seen=false`, `idle_history_seen=false`, and
  `paired_history_proof=false`.

Authoritative v1.5 runtime hashes:

- `calendar_pit_v15.jsonl`:
  `7A0A8E2C6EC00FE3DA166C7E80C7D1F558EBB07FE90256DB56656C3C3FC2FF12`
- `catalog_state_v15.txt`:
  `A806966AB919AD1D3D46CE0239B8A9C1A70AAADE9F21BA847414968AD150774F`
- `occurrence_v15.txt`:
  `4228D304CFE5D42E52B940AD9E9C31871763F5EF1A2DC01314BA423559A03E8A`

Final verdict: `KILL_CALENDAR_LANE`. This exhausts the sole authorized History
successor. No further `CalendarValueLast*` or `CalendarValueHistory*` revision is
allowed in this research lane. The active project goal continues only through a
materially different, database-first XAU/Forex information source.

Official contracts:

- https://www.mql5.com/en/docs/calendar/calendarvaluelastbyevent
- https://www.mql5.com/en/docs/calendar/calendarvaluehistorybyevent
- https://www.mql5.com/en/docs/calendar/calendareventbycurrency
