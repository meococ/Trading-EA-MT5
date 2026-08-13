# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-003 — DESIGN source quote plan

Status: frozen before any DESIGN payload access.

## Purpose

Price the complete 2019–2020 DESIGN clock population for the source-valid frozen
depth-transfer formula. This step is metadata-only and cannot evaluate returns or edge.

## Frozen population and request

- Clock ledger SHA-256:
  `5C30F99FF0E1341D680C2747315E2FF4DFF99C5FBE01C2C5C4036BC101375E7B`.
- Select exactly 329 sorted, unique clocks in calendar years 2019–2020, beginning at
  `EVT0001`. No event is selected or removed using price or strategy outcomes.
- For each clock request `GLBX.MDP3`, `mbp-10`, `6E.v.0`, `continuous`, `ts_recv`
  over `[event_time,event_time+60 seconds)`.
- Query `metadata.get_cost(historical-streaming)` and
  `metadata.get_billable_size` only. No timeseries, batch, subscription, raw source,
  target-price, validation, or holdout access.
- Metadata calls may retry up to three times because they are free and idempotent.

## Quote gates

- exactly 329 quotes returned with unique event identities and sorted clocks;
- every quote has positive billable bytes and nonnegative finite estimated cost;
- at least 95% of windows have nonzero cost;
- maximum per-event quote is at most USD 0.02;
- aggregate estimated DESIGN cost is strictly below USD 10.

A pass authorizes no purchase. A separate hash-frozen acquisition plan is required.

