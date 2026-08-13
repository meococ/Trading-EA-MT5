# SOURCE QUOTE READOUT - HYP-EVENT-AGGFLOW-EURUSD-TICK-001

## Verdict

`PARK_FREE_DESIGN_QUOTE_PASS_OWNER_PAYMENT_AUTHORITY_REQUIRED`

This is source-cost and capability evidence only. It is not a source-quality
pass and not evidence of economic edge.

## Exact receipt

- Quote ID:
  `EVENTAGGFLOW001-TRADES-DESIGN-FREE-QUOTE-001`
- Receipt:
  `02. AlphaFactory/data/databento/cme_6e_event_aggflow/HYP-EVENT-AGGFLOW-EURUSD-TICK-001/EVENTAGGFLOW001-TRADES-DESIGN-FREE-QUOTE-001/metadata_quote_receipt.json`
- Receipt SHA256:
  `9C48C85CEC7766E83C387841CD0F8502C7CF70BEAB3F4537737DD73E4DC12C9D`
- Frozen source-plan SHA256:
  `0167C4F62B1020865771520AE9895AC302129BE524783B4BDFC2E1B0052E650F`
- Registry authority row SHA256:
  `CC4DC6C43AEC9825A1F5ED9E5AFFDB0CEDFB9D9A523F5C4D0E8FD7A4404E6E41`

## Result

- Dataset/schema/symbol: `GLBX.MDP3` / `trades` / `6E.v.0`
- Window: `[event_time_utc,event_time_utc+15s)`
- Split: DESIGN 2019-2020 only
- Exact requests: 329/329
- Nonzero-billable requests: 327/329 = 99.3920972644%
- Estimated nonzero cadence: 3.1313269622/week
- Estimated total cost: USD 0.875670075414
- Estimated total billable bytes: 33,580,128
- Largest single-window quote: USD 0.018318593502
- Metadata attempts: 332 `get_cost`, 329 `get_billable_size`
- Paid request: zero
- Time-series/batch/download calls: zero
- Source payloads read: zero
- EURUSD prices/outcomes/economics read: zero
- Validation source quoted/read: zero

The two zero-byte windows are explicit and expected to remain no-source/no-trade
unless a later paid receipt proves otherwise:

- `EVT0206`: 2020-03-15 21:00:00Z to 21:00:15Z
- `EVT0228`: 2020-04-10 12:30:00Z to 12:30:15Z

The quote's 327 nonzero windows exceed the frozen 313-window source-coverage
planning threshold. A paid decode is still required to prove direct-side trade
coverage, signed-flow cadence, direction balance, hashes, counts, and timestamp
integrity.

## Required Owner authority

Recommended exact ceiling: **USD 1.00** for the 329 DESIGN windows only.

Approval opens a fresh paid-acquisition successor and must bind all of:

- hypothesis `HYP-EVENT-AGGFLOW-EURUSD-TICK-001`;
- quote ID `EVENTAGGFLOW001-TRADES-DESIGN-FREE-QUOTE-001`;
- source-plan SHA256
  `0167C4F62B1020865771520AE9895AC302129BE524783B4BDFC2E1B0052E650F`;
- quote-receipt SHA256
  `9C48C85CEC7766E83C387841CD0F8502C7CF70BEAB3F4537737DD73E4DC12C9D`;
- maximum aggregate paid cost USD 1.00;
- DESIGN 2019-2020 only, schema `trades`, exact `[0,+15s)` windows.

Even after approval, validation 2021-2022, EURUSD outcomes, economics, MQL5,
optimization, promotion, paper, and live remain closed until their separate
gates are satisfied.
