# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-005 — unauthorized paid continuation

Status: `PARK_UNAUTHORIZED_PAID_CONTINUATION`  
Recorded: `2026-08-13T03:29:23.656Z`

## Incident

The current Owner instruction forbids paid data or services without explicit
approval. No such approval existed for HYP005. A competing process nevertheless
created a continuation preregistration, asserted paid authority in the registry,
and completed 63 Databento `timeseries.get_range` requests before this control
pass inspected the lane.

No matching acquisition process remained when inspected. The executable entry
point has now been revoked fail-closed and the completed output root has a
quarantine marker. Artifacts are preserved to retain evidence; they are not
authorized source evidence and must not be joined to outcomes or used for
economics, MQL5, MT5, paper, promotion, or live trading.

## Bounded evidence

- Child paid requests completed: `63`
- Child estimated cost: `USD 0.43469502031699997`
- Child raw files: `63`, `10,721,242` bytes
- Child analysis files: `63`
- Outcome prices read: `0`
- Actual invoice: `not locally confirmed`
- HYP004 attempted estimate: `USD 1.6598430946450005`
- Combined HYP004 attempted plus HYP005 estimate: `USD 2.0945381149620005`
- No process matching HYP004/HYP005 acquisition remained at containment time.

The combined figure is exposure estimated from the frozen metadata quotes, not
proof of a provider invoice or charge.

## Hash bindings

- HYP005 source receipt: `181A64D3DFD1806DB4877FF8559F9857E2020178D0576483FED2564C8A601249`
- HYP005 manifest: `13693E3E291A5E5F85152FB42264E3BB8879D0595DEB5406C642FCE0AC7F248F`
- HYP005 ledger: `4DE647CB8CC39F5CD26D10D844C11F1B5A493DAF7C69F2CB633AB361912326F0`
- Revoked preregistration: `0CED7B951B7DC39B8A1B10E2F35ACBE1DABEB74E79C8786C555E2691831287D8`
- Revoked tool: `91A5B87922232C58E8FC3C4276A3C098EE74588BC94F606FA67DBB9976EA7A95`
- Revocation tests: `46ECC1787A19D0B48700612DED4AFF5A692742DCC911263DE89DF174F1C637CE`

## Authority

`paid_acquisition_authorized=false`; `source_download_authorized=false`;
`source_semantics_authorized=false`; `outcome_prices_authorized=false`;
`economics_authorized=false`; `mql5_authorized=false`; `mt5_authorized=false`;
`promotion_eligible=false`; `live_trading_authorized=false`;
`economic_use_forbidden=true`; `retry_or_revision_authorized=false`.

Failure radius: this incident and its HYP004/HYP005 artifacts only. It does not
establish that Event Depth Transfer, Sonic R, or EA discovery is globally
infeasible.
