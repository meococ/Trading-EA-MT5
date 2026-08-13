# HYP-EVENT-L1-REPLEN-EURUSD-TICK-002 — paid MBP-1 pilot readout

## Verdict

`PASS_PILOT_SEMANTICS__KILL_L1_ONLY_CANDIDATE_DEFINITION`

The exact EVT0001 payload proves that CME 6E MBP-1 supplies the joint trade
and L1 BBO-size event stream required for microstructure research. It does not
produce a lawful, unique trading mapping by itself. No full DESIGN purchase is
authorized for the rejected object.

## Acquisition and integrity

- Live estimate/paid ceiling: `USD 0.00741443038` / `USD 0.01`.
- API calls: one metadata cost, one billable-size, one serial
  `timeseries.get_range`, zero batch.
- Raw DBNv3 bytes/SHA-256: `256239` /
  `61E84C93DBC17690A95C59C37984A368744376AE29DBFAFB5B957E83018B668E`.
- Exact `ts_recv` window:
  `[2019-01-03T15:00:00.000Z,2019-01-03T15:02:00.000Z)`.
- No EURUSD field, future return, PnL, validation source, MQL5 or MT5 access.

## Source-semantics result

- Records: `11723`.
- Actions: A `4882`, C `4039`, M `638`, T `2163`, F `1`.
- Sides: A `5811`, B `5703`, N `209`.
- BBO price changes: `2873`.
- BBO size changes: `9401`; unchanged-price size changes: `6686`.
- Zero/empty book: `0`.
- Receive-time containment/non-monotonic violations: `0` / `0`.
- Locked/crossed share: `0`.
- Median/max inter-message gap: `0.1863265 ms` / `1181.014775 ms`.
- Frozen semantic gates: all PASS.

## Causal definition audit

Grok first proposed post-wave net aggressive flow plus last-minus-first BBO
size, same-direction. Lead review rejected it before source purchase because:

1. ask depletion under buy aggression is not ask replenishment;
2. last-minus-first size compares different queues when the BBO price changes;
3. same-direction signed flow plus a book condition risks becoming a filtered
   HYP013 rescue;
4. the proposal weakened the canonical 1.5x-cost PF gate.

After requiring refill/depletion to be accumulated only across consecutive
updates at the same BBO price, Grok returned `KILL_CANDIDATE`: L1 semantics do
not uniquely determine same-direction versus contrarian mapping without an
arbitrary structural choice or threshold. Therefore the estimated
`USD 1.191255122426` full-DESIGN MBP-1 purchase is not made for this object.

## Evidence bindings

- Acquisition plan SHA-256:
  `8DF625C7CBED2C53BCFF83174F8E3D9C657A690D5BA5B0E81755EF9F642696C2`
- Download manifest SHA-256:
  `2C814F534BCB79588C8D2A12B6C6726AB71FE25DF93639222CAD3788D5FC9970`
- Acquisition receipt SHA-256:
  `0283BEB625FF379ADA73F3CB27CD24AEEB36D88490BE3FDA95A3C20A2ACD9CDD`
- Semantics analysis SHA-256:
  `66B7745694362411627DEA89941278BE907602E662086D55E2FF117D3624D76C`
- Armed acquisition tool SHA-256:
  `514883B7CF247A1D82D762B0F4F1BA51751F71C7B5B651683233EED0A3EC1DA0`
- Focused test SHA-256:
  `1345273540E6B39203997574022BB7C870C43577DADA47B9455A38F3E3DB8139`

## Failure radius

Closed: using this L1-only post-first-wave stream to choose an absorption
direction by discretionary same/contrarian interpretation, or rescuing HYP013
with an L1 filter. A future candidate needs an independently motivated mapping
or a genuinely different causal input/population. The pilot remains reusable
only as source-semantics evidence, never as edge evidence.

