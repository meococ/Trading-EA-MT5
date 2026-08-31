# CME 6E option-pin HYP002 terminal source verdict — 2026-08-12

## Verdict

`HYP-CME6E-OPT-PIN-EURUSD-M15-002` is terminal as
`KILL_SOURCE_DESIGN_MONOTONIC_PARTIAL`.

This is a source-contract verdict only. Economics, direction, futures reference
prices, MQL5, MT5 backtests, optimization, paper and live were not opened.

## Frozen contract

- Candidate object: open-interest pin from CME 6E option definitions and
  venue-published normalized statistics.
- Missing normalized open interest: `UNKNOWN_EVENT_INVALID`; never zero-fill.
- Planned expiry events: `516`.
- Frozen source-validity gate: at least `95%`, requiring at least `491` valid
  events and allowing at most `25` invalid events.
- Definition state: earliest valid expiry-decision fixed point, with zero
  selected definitions at or after their decision time.
- Source preregistration SHA-256:
  `0C1999109572622BF579EE2B4233BA77CBA6A73E1516D7B648AC77EC92209B86`.
- Strict analyzer SHA-256:
  `8C66234139CA3690DC1DF974E6D9CCEF0D87F9ED26494863C19C4631EDB57338`.

## Acquisition closeout

The single authorized acquisition stopped abruptly after `291/516` exact
timeseries calls. The persisted manifest remained `IN_FLIGHT` with `291`
hash-bound complete payloads, no `failed_request_id`, no `failure_type`, and no
complete acquisition receipt. Four payload requests emitted Databento degraded-
day warnings, but the manifest does not identify those warnings as the process
termination cause. The termination cause therefore remains unclassified.

The frozen authority forbids retry or resume. No second acquisition was
started.

## Fail-only monotonic audit

A dedicated partial auditor reused the frozen strict event analyzer. It is
incapable of passing a source design from partial data; it may only kill when
the already observed invalid count makes the original gate mathematically
unreachable.

- Acquired events audited: `291`.
- Strict source-valid acquired events: `0`.
- Strict source-invalid acquired events: `291`.
- Acquired events with at least one unknown normalized OI contract: `291`.
- Unacquired events: `225`.
- Best-case valid events if every unacquired event passed: `225`.
- Required valid events: `491`.
- Gate impossible: `true`.

Therefore acquisition completion cannot change the source verdict. The exact
option-pin mapping is killed before prices or outcomes.

## Evidence

- Partial monotonic audit:
  `02. AlphaFactory/data/databento/cme_6e_option_pin/HYP-CME6E-OPT-PIN-EURUSD-M15-002/CME6EOPTPIN002-DESIGN-SOURCE-001/phase_01_pit_definitions/design_source_partial_monotonic_audit_pit.json`
  (`0DA455B22ABCC08FA2CA4CDCC0E69B194313E1EA754276E0B85762B3F6DCC17F`).
- Terminal acquisition receipt:
  `02. AlphaFactory/data/databento/cme_6e_option_pin/HYP-CME6E-OPT-PIN-EURUSD-M15-002/CME6EOPTPIN002-DESIGN-SOURCE-001/phase_01_pit_definitions/phase_02_statistics_terminal_receipt_pit.json`
  (`0DB2B4750A34D16B6C9DB3C908DDA0825827DC8E7C329905DDB96B6F675DAD47`).
- Fail-only auditor:
  `03. EA Developer/EA_CME6EOptionPin/research/audit_cme6e_option_pin_partial_source_002.py`
  (`8C7530A0A7234589AB2AF28CF0C3CCCB9F8BA6EB7D47FDD4B81E996E70212249`).
- Auditor test:
  `03. EA Developer/EA_CME6EOptionPin/research/test_audit_cme6e_option_pin_partial_source_002.py`
  (`1EC3F0B547ACA0D71EA2E30DD563A99FA8868EC15835B9260CD1EDB70A1DC09E`),
  `3/3` tests passed.

Grok Build independently returned `MONOTONIC_LOGIC=PASS` and
`SOURCE_VERDICT=TERMINAL_KILL`. This is advisory corroboration; the local
hash-bound artifacts above are authority.

## No-revival rule

- Do not fill missing normalized statistics OI with zero.
- Do not retry/resume HYP002 or use the `225` unacquired events to rescue it.
- Do not add proximity, session, Sonic alignment, SL/TP or outcome-derived
  filters to this mapping.
- Do not acquire futures-reference prices or open economics from this lineage.
- A future option-derived candidate must use a materially different, complete
  point-in-time information object and a fresh source contract; renaming or
  recombining this incomplete normalized-OI surface is not a new candidate.

## Frontier after closeout

The pre-existing local OHLC/spread/tick-volume/Bid-Ask metatick/DOM/aggressor
frontier was already closed as `NO_CANDIDATE_LOCAL_FRONTIER`. HYP002 does not
open a replacement candidate. Database-first local discovery therefore remains
at `NO_CANDIDATE`; no EA or economic run is authorized until a materially new,
lawful and source-capable information object is identified.
