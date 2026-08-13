# HYP-EVENT-L1-REPLEN-EURUSD-TICK-002 — frozen MBP-1 semantics pilot

Prepared 2026-08-12 after HYP001 passed its free quote and before any new paid
request or MBP-1 payload read.

## Exact purchase boundary

- Parent quote: `EVENTL1REPLEN001-MBP1-DESIGN-FREE-QUOTE-001`.
- Dataset/schema/symbol: `GLBX.MDP3` / `mbp-1` / `6E.v.0`.
- Input symbology and clock: `continuous`, `ts_recv`.
- Single identity: `EVT0001`.
- Exact half-open request:
  `[2019-01-03T15:00:00.000Z,2019-01-03T15:02:00.000Z)`.
- Metadata estimate: `USD 0.00741443038`, `4422880` bytes.
- Hard aggregate Owner ceiling requested: `USD 0.01`.
- One fresh live quote must remain `<= USD 0.01` before the call.
- At most one serial `timeseries.get_range`; batch is forbidden.
- Checkpoint `in_flight` before the paid call. An unresolved in-flight identity
  is never retried automatically.
- Raw DBN payload is retained on D:, hashed before decode, and decoded only
  offline.

No approval is inferred from any earlier source campaign. This plan becomes
executable only after the Owner explicitly approves this exact identity,
window, schema, and ceiling in the current conversation and that authority is
hash-bound in a fresh registry row.

## Frozen runtime and payload receipt

- `02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe`
- Python 3.12.10
- `databento==0.55.1`
- `databento-dbn==0.35.0`
- DBN version 3

Receipt must bind plan, parent quote receipt, Owner authority, live quote,
request args, raw path/bytes/SHA-256, SDK/runtime versions, and zero counters
for validation, EURUSD outcomes, economics, MQL5, MT5, paper and live trading.

## Frozen semantics analysis

Only these source-only fields may be decoded: `ts_recv`, `ts_event`, `action`,
`side`, `price`, `size`, `flags`, `depth`, `sequence`, and top-level
`bid_px`, `ask_px`, `bid_sz`, `ask_sz`, `bid_ct`, `ask_ct`.

Compute exactly:

- total records and counts by action and side;
- trade-action count;
- BBO price-change count;
- BBO size-change-with-unchanged-price count;
- zero-size/empty-book updates;
- first/last `ts_recv` and half-open containment violations;
- monotonicity violations;
- median and maximum inter-message gap in milliseconds as diagnostics only;
- locked/crossed record share;
- null/constant status of every required field.

Ordinary event-driven silence is not a falsifier and no one-second maximum-gap
gate is allowed. `PASS_SEMANTICS` requires a matching raw hash, exact window
containment, monotone receive time, populated required fields, at least one
trade, and at least one valid BBO size update. Otherwise the pilot is
`PARK_SOURCE_SEMANTICS` without retry or rescue.

## Forbidden under this ID

No EURUSD price/spread join; no future return or PnL; no signed-flow,
absorption or replenishment formula; no direction or feature threshold; no
validation clock; no full DESIGN purchase; no optimization; no MQL5/MT5; no
paper/live/promotion. A one-event PASS proves only feed semantics, never source
coverage or economic edge.

