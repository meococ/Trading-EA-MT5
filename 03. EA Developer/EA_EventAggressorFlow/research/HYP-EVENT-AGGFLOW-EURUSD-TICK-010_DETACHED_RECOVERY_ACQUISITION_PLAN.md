# DETACHED RECOVERY ACQUISITION PLAN - HYP-EVENT-AGGFLOW-EURUSD-TICK-010

Frozen on 2026-08-12 after HYP008 stopped on `BentoServerError` at exact
identity EVT0268 and before any CME trade-side/size distribution, EURUSD
outcome, validation price, return, PnL, chart, MQL5, or MT5 result was read.

## Purpose and non-economic boundary

HYP010 is an engineering-continuity successor for the same Owner-approved 329
CME 6E `trades` DESIGN windows. It does not change the market hypothesis,
mapping, event population, source schema, symbol, timing, or economic gates.
It must verify and copy HYP008's 265 completed DBNv3 files and two explicit
zero-byte/no-call identities locally, retry only unresolved EVT0268 once, and
then acquire only the remaining frozen nonzero identities serially.

No network call may read a new cell. No source transform, EURUSD outcome,
validation source, economics, optimization, MQL5, MT5, paper, promotion, or
live-trading surface is authorized.

## Frozen parent evidence

- Parent: `HYP-EVENT-AGGFLOW-EURUSD-TICK-008` /
  `EVENTAGGFLOW008-TRADES-DESIGN-SOURCE-001`.
- Parent live plan SHA256:
  `60D85837584D4738578D437954D0C1CAE5BDBB6264FE0CE03A691E387914DE86`.
- Parent stopped manifest SHA256:
  `3A98A1E3D4A7B213AA26EC53E8A4311ECB490D87B2393589C8CE33B6EA47857D`.
- Parent detached launch receipt SHA256:
  `D378439EBC3ABACD055B868AD425C6ABC16E3C17409AA1492180EFC38E34A752`.
- Parent stderr SHA256:
  `A3742A71AD79343C068B78ED476204C009EA50373BF4D8EF325A2295145DD21A`.
- Parent coverage: 265 verified DBNv3 files + 2 explicit zero-byte/no-call
  identities = 267/329; 80,419 records; 1,399,894 bytes.
- Parent lock absent, completion receipt absent, and no `.partial` or `.inherit`
  file exists.
- Parent in-flight: EVT0268, `[2020-06-23T07:15:00Z,
  2020-06-23T07:15:15Z)`, estimate USD 0.002187967300, 83,904 billable bytes,
  with no recoverable output.
- HYP008 already accounted one possible duplicate EVT0081 at USD
  0.004807770252. Its worst-case aggregate was USD 0.880477845666.
- One provider quality warning is frozen as a source caveat: GLBX.MDP3 date
  2020-02-28 is `degraded`, confined in this population to EVT0198. EVT0198's
  DBNv3 file remains included and has 408 full-stream-verified records. This
  caveat cannot be used to filter an event after outcome readout.

## Exact acquisition and cost contract

- Dataset/schema/symbol: `GLBX.MDP3` / `trades` / `6E.v.0`.
- Stype: `continuous` to `instrument_id`.
- Frozen population: exactly 329 unique DESIGN identities, 2019-2020,
  `[event_time_utc,event_time_utc+15s)`.
- Original aggregate estimate: USD 0.875670075414.
- Prior EVT0081 possible-duplicate allowance: USD 0.004807770252.
- New EVT0268 possible-duplicate allowance: USD 0.002187967300.
- Frozen worst-case aggregate: USD 0.882665812966.
- Owner ceiling: USD 1.00; frozen headroom: USD 0.117334187034.
- Exactly one paid retry of exact EVT0268 is allowed. No other previously
  attempted/completed identity may be retried. After EVT0268 succeeds, only
  never-attempted remaining nonzero identities may be called once, serially.
- Zero-byte identities remain explicit coverage and make no time-series call.

Each inherited file must be rebound by request ID, exact timestamps, filename,
bytes, SHA256, DBNv3 metadata, and full-stream record count before copying.
Inherited zero-byte entries must be rebound to the frozen live plan. All paths
must remain under the exact D: parent/output roots. One exclusive lock and
atomic checkpointing are mandatory. A remote exception leaves the successor
terminally stopped; no automatic retry follows.

## Terminal contract

Success requires exactly 329/329 coverage, no in-flight identity, no lock or
temporary file, and a hash-bound terminal manifest plus paid acquisition
receipt. The terminal status is only `DOWNLOADED_RAW_SOURCE_QUALITY_REQUIRED`;
it is not source-feasibility, engineering edge, economic edge, or promotion
evidence. Failure is parked with its exact identity and artifact hashes.
