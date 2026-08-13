# HYP-CALENDAR-PIT-MQDEMO-001 — terminal capability receipt

## Verdict

`KILL_MQDEMO_CAPABILITY_CHILD`

This closes the single preregistered MetaQuotes-Demo child. It does not close
the wider EA goal, and it does not authorize a second Calendar API attempt.

## Frozen identity and build

- preregistration was written before compile or attachment;
- source: `EA_ProspectiveCalendarPITMQDemo.mq5`;
- source SHA-256:
  `13D6A831F45B1022BD541F9FAAE17C4C0F676CF38A9F9742502354E29840352C`;
- EX5 SHA-256:
  `F4BC6CE147BFA1344469D854068C822B431A987A3E6969E6F597EB23F15852F5`;
- AlphaFactory compile receipt: `0 errors, 0 warnings`;
- static and auditor tests: `5 passed`;
- runtime: `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable`;
- account server: exact `MetaQuotes-Demo` on the existing demo account;
- terminal executable build reported by the EA: 6090; network authorization
  reported service build 6104;
- terminal-wide Algo Trading and EA `Allow Algo Trading` remained unchecked.

## Runtime evidence

The fresh namespace emitted 17 JSONL records:

- `DISCOVERY_COUNTRIES`: 23 countries;
- `DISCOVERY_EVENT_DEFS`: 8/8 currencies;
- all definitions: 1,051;
- moderate/high selected events: 506;
- catalog hash: `1183765039875304157`;
- first future-window `CalendarValueHistoryByEvent` call at local
  `2026-08-13 12:15:56`: event `840010001`, `n=-1`, `api_error=5401`;
- accepted occurrences, future proofs, idle proofs, observations and
  mutations: all zero;
- safety fields on every record: `outcome_accessed=false`,
  `prices_read=false`, `orders=false`, `trading_disabled=true`;
- shutdown reason 9, with zero orders and zero outcome/price access.

The retained runtime JSONL hash is
`C1A9E9A31AD1608C0E73F63D128BDF1FDE16CF50E7C1824B6BB96241BE423450`.
The terminal log hash is
`3B43165CFADA3B4B628843D0FA15761EFFB05CABFF4AEF5DE89F8F49E0D0B0D4`.

## Protocol deviation

The preregistration required stopping on the first fatal API error. A
LiveUpdate modal appeared while the terminal was being closed; two later timer
callbacks therefore ran before shutdown and returned the same `5401` for
events `840010002` and `840010003`. The independent auditor correctly records
`stop_after_first_fatal=false`.

This deviation cannot improve or change the verdict: the first call already
failed the mandatory zero-error gate, there was still only one attachment,
the source and query were not revised, and no price, outcome or order surface
was opened. It is nevertheless a real execution-control failure and must not
be hidden or relabeled as compliant.

## Authority boundary

- Engineering: compile-valid and safety-valid, but source-capability invalid.
- Economic: not opened; no price or return was read.
- Promotion/live trading: forbidden.
- Repetition: no second attachment, no `HistoryByEvent` revision, no
  `CalendarValueLast*` fallback, no broker substitution, and no state reuse.

Evidence is retained under
`research/evidence/HYP-CALENDAR-PIT-MQDEMO-001/`; the machine-readable verdict
is `research/runtime_audit_latest.json`.
