# PAID SOURCE ACQUISITION PLAN - HYP-EVENT-AGGFLOW-EURUSD-TICK-002

Frozen on 2026-08-12 after the free metadata quote and before any immediate-
window CME 6E trade payload or EURUSD post-event outcome is read.

## Authority and exact failure radius

Owner authorization is limited to one resumable, serial acquisition campaign
with an aggregate ceiling of USD 1.00. It covers the exact 329 DESIGN request
identities from `EVENTAGGFLOW001-TRADES-DESIGN-FREE-QUOTE-001` only:

- dataset `GLBX.MDP3`;
- schema `trades`;
- continuous symbol `6E.v.0`;
- exact half-open receive-time window `[event_time_utc,event_time_utc+15s)`;
- DESIGN years 2019-2020 only;
- 329 frozen event clocks from the hash-bound clock ledger;
- fresh free live re-quote of all 329 identities before any paid request;
- serial `timeseries.get_range` only for identities with nonzero live billable
  bytes; zero-byte identities remain explicit source-empty coverage entries;
- aggregate fresh estimated cost must be finite, nonnegative and no greater
  than USD 1.00 before the first paid request.

The authorization does not cover another schema, symbol, clock, time window,
event population, retry of an unresolved paid identity, batch acquisition,
VALIDATION 2021-2022, EURUSD prices, economic analysis, charting, MQL5, MT5,
optimization, paper trading, promotion, or live trading. No API key may enter an
artifact or log.

## Immutable evidence basis

- Parent source-quote hypothesis:
  `HYP-EVENT-AGGFLOW-EURUSD-TICK-001`
- Free quote ID:
  `EVENTAGGFLOW001-TRADES-DESIGN-FREE-QUOTE-001`
- Source quote plan SHA256:
  `0167C4F62B1020865771520AE9895AC302129BE524783B4BDFC2E1B0052E650F`
- Free quote receipt SHA256:
  `9C48C85CEC7766E83C387841CD0F8502C7CF70BEAB3F4537737DD73E4DC12C9D`
- Frozen clock ledger SHA256:
  `5C30F99FF0E1341D680C2747315E2FF4DFF99C5FBE01C2C5C4036BC101375E7B`
- Quoted requests: 329 total, 327 nonzero-byte, 2 zero-byte.
- Free-quote estimate: USD 0.875670075414 and 33,580,128 billable bytes.
- Owner ceiling: USD 1.00 aggregate.

The paid successor must be a fresh registry identity. The terminal parked
source-quote row is never mutated or reopened.

## Remote-call contract

Before any paid call, the acquisition tool must validate its own normalized
source hash, focused-test hash, this plan hash, authority-receipt hash, free-
quote receipt hash, foundation hash, and the latest successor registry-row
hash. It must also verify that all economic/outcome/MQL5/validation authorities
remain closed.

Allowed remote methods:

1. `metadata.get_cost` for a fresh live re-quote of each frozen identity;
2. `metadata.get_billable_size` for the same identity;
3. `timeseries.get_range` serially for a nonzero-byte identity only.

Forbidden: `batch.*`, symbology changes, alternate dataset/schema/symbol/window,
or any request for the sealed 2021-2022 population.

The campaign writes an acquisition plan before paid access and a resumable
download manifest before each serial request. An unresolved `in_flight`
identity with no recoverable file freezes the campaign for manual
reconciliation; it is never retried automatically. Every completed DBN file is
bound by request identity, source timestamps, bytes, record count and SHA256.

## Outcome-blind source-quality gate

Download completion does not authorize market-outcome work. A separately
reviewed decoder must first prove, without reading EURUSD prices:

- all 329 DESIGN identities are covered by either a verified DBN file or an
  explicit live zero-byte entry;
- at least 313 identities contain one or more valid direct-side trades;
- at least 261 identities have nonzero `sum(B size)-sum(A size)`;
- buyer-dominant and seller-dominant events each represent at least 25% of the
  eligible population;
- every accepted record is a trade with positive finite size, `side in {B,A}`
  and `ts_recv` inside the exact half-open source window;
- zero duplicate identities, hash/byte/count mismatches, negative sizes,
  out-of-window accepted records, forbidden API calls, outcome reads or
  validation-source access.

Empty, unclassified-only and tied-flow windows are deterministic no-trade
events. No threshold, event subset, session rule, price feature or imputation
may be introduced after decoding.

Only a full source-quality pass may open a new, hash-bound economic/EA
successor using the frozen +15s entry, +75s exit and sign/reverse mapping from
the parent plan. A source-gate failure terminates this exact mapping.
