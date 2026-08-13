# HYP-EVENT-L1-REPLEN-EURUSD-TICK-001 — source quote readout

## Verdict

`PASS_FREE_DESIGN_MBP1_QUOTE_PILOT_PAYMENT_AUTHORITY_REQUIRED`

The one authorized metadata-only quote completed for every frozen DESIGN
identity. It establishes a source route, not a candidate and not an edge.

## Result

- Requests: 329/329.
- Nonzero billable windows: 327/329 (`0.993920972644377`).
- Implied nonzero cadence: `3.131326962235268` events/week.
- Estimate: `USD 1.191255122426`, `710611360` billable bytes.
- Source-frontier gates: all PASS.
- `metadata.get_cost`: 329; `metadata.get_billable_size`: 329.
- `timeseries.get_range`, batch, paid requests, payload reads, EURUSD outcome
  fields, validation-source access: all zero/false/empty.

The frozen cheapest semantics pilot is `EVT0001`, exact receive-time window
`[2019-01-03T15:00:00.000Z,2019-01-03T15:02:00.000Z)`. Its quote is
`USD 0.00741443038` and `4422880` bytes.

## Bindings

- Plan SHA-256:
  `D423A1CFF1CCA1852ACEEDDB83CA86D5700BBB50306CF1E17058A80211E32F11`
- Quote receipt:
  `02. AlphaFactory/data/databento/cme_6e_event_l1_replen/HYP-EVENT-L1-REPLEN-EURUSD-TICK-001/EVENTL1REPLEN001-MBP1-DESIGN-FREE-QUOTE-001/metadata_quote_receipt.json`
- Receipt SHA-256:
  `230E7D4F2BF291A78F276A7D0F4956BB2EC54CC226DE4D66E85858FA4BE31A64`
- Armed quote tool SHA-256:
  `60089419D98E506422169BE184A88CC1F48F951567733A4D4FD53275F85A25F0`
- Test SHA-256:
  `DBA367CF95E4BB34058731AE6F6A31CE7F45578A594BC2CE1C9502BFE6E59E62`

## Next legal action

Grok `/deep-research-trading-meta5` froze an outcome-blind feed-semantics
contract for the single pilot. The prior quote runtime was sufficient for
metadata only; a payload must use the already reviewed DBNv3 runtime:
Python 3.12.10, `databento==0.55.1`, `databento-dbn==0.35.0`.

No paid request is authorized here. The next action requires an exact Owner
ceiling of `USD 0.01` for only the frozen `EVT0001` MBP-1 window. Passing the
pilot may authorize discussion of a full DESIGN source plan; it cannot prove
coverage or edge and cannot open EURUSD outcomes.

