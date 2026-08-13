# DETACHED RECOVERY ACQUISITION PLAN - HYP-EVENT-AGGFLOW-EURUSD-TICK-008

Frozen on 2026-08-12 before retrying unresolved `EVT0081` or reading any
EURUSD outcome.

## Exact recovery scope

HYP008 preserves the Owner-approved source population and aggregate USD 1.00
ceiling. It may verify and copy the 80 completed HYP006 DBNv3 files locally,
then manually retry the exact unresolved `EVT0081` identity once and continue
the remaining frozen nonzero DESIGN identities serially. It may record the two
live zero-byte identities without time-series calls.

No new dataset, schema, symbol, event, timestamp window or validation identity
is introduced. `EVT0081` is the exact original request
`[2019-06-07T12:30:00.000Z,2019-06-07T12:30:15.000Z)` with live estimate USD
0.004807770252 and 184,368 billable bytes. Because its HYP006 request may have
reached the server before host termination, HYP008 accounts it twice in the
worst case:

- original frozen 329-window aggregate: USD 0.875670075414;
- one possible duplicate `EVT0081` estimate: USD 0.004807770252;
- worst-case aggregate: USD 0.880477845666 <= Owner ceiling USD 1.00;
- remaining headroom: USD 0.119522154334.

Only one manual `EVT0081` retry is authorized. An unresolved HYP008 in-flight
identity still has no automatic retry. Further duplication, re-quote, batch
access, VALIDATION 2021-2022, source transform, EURUSD price/outcome, economics,
MQL5, MT5, optimization, paper, promotion and live trading remain forbidden.

## Immutable parent/runtime basis

- Parent hypothesis/acquisition:
  `HYP-EVENT-AGGFLOW-EURUSD-TICK-006` /
  `EVENTAGGFLOW006-TRADES-DESIGN-SOURCE-001`.
- Parent live plan SHA256:
  `EAFE50B2C3B865FE9BDD1C4D42C1865C9510BA9483419351A4FEC66E670BFD13`.
- Parent stopped manifest SHA256:
  `B2BE864827F9B301B2EF020E3B2775ADA2C514D946B69964CAD38B20E5BB60BF`.
- Completed parent corpus: exactly 80 unique manifest files, 37,737 records,
  645,863 stored bytes, all full-stream DBNv3 verified.
- Parent unresolved identity: exactly `EVT0081`, with no final or partial file.
- Runtime receipt SHA256:
  `E98FB8FC4E26865DF3FEA1FE75064CA86666E17B7781E543B2912BA49F3CC0BD`.
- Runtime: Python 3.12.10, Databento 0.55.1, databento-dbn 0.35.0,
  self-contained DBNv3 validator; no legacy 0.54 foundation import.

Before remote access the tool must validate the exact plan, Owner receipt,
runtime receipt, free quote, parent plan/manifest, latest HYP008 registry row,
its own immutable SHA256 and focused-test SHA256. It must full-stream validate
all 80 parent files and copy them into a new exclusive HYP008 root with the same
bytes/SHA256/record counts. The copied manifest must explicitly label them
`inherited_local_no_remote_call`.

## Detached monitored execution

The paid worker must be launched as a hidden detached process with stdout and
stderr redirected to files under the exact HYP008 output root. The process PID,
command, start time and log paths are recorded in a launch receipt. A single
atomic campaign lock protects the root. Monitoring is read-only through PID,
lock, manifest and logs; no second worker may start.

Every paid request remains serial and is preceded by an atomic in-flight
checkpoint. `EVT0081` is explicitly labeled `manual_retry_after_parent_timeout`
and counts against the worst-case aggregate. All later identities are ordinary
remaining requests. Completion requires 329/329 coverage, terminal manifest,
receipt, absent lock, zero partials and process exit code 0.

Completion is source availability only. A separately frozen and reviewed
outcome-blind source-quality successor must still apply the exact `T` / `B,A,N`
/ positive-size / `ts_recv [start,end)` transform and the 313/261/25% gates.
