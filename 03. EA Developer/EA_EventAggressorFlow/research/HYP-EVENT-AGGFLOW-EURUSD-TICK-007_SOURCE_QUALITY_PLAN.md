# SOURCE QUALITY PLAN - HYP-EVENT-AGGFLOW-EURUSD-TICK-007

Frozen on 2026-08-12 while the HYP006 paid acquisition was still running and
before any HYP006 trade-record field or flow distribution was read.

## Purpose and trust boundary

HYP007 is outcome-blind source qualification only. It may decode the exact
completed HYP006 DESIGN corpus after HYP006 reaches a hash-bound terminal
download receipt. It must not access a network, API key, EURUSD price/tick/bar,
validation source, economic metric, chart, MQL5, MT5, optimization, paper or
live trading surface.

The parent manifest and receipt SHA256 values are intentionally unknown at this
freeze time. A later source-authority receipt may bind only those terminal
HYP006 artifact hashes plus the already-frozen plan/tool/test/runtime hashes; it
may not change the transform, thresholds, event population or gates below.

## Exact input contract

- Parent hypothesis: `HYP-EVENT-AGGFLOW-EURUSD-TICK-006`.
- Parent acquisition: `EVENTAGGFLOW006-TRADES-DESIGN-SOURCE-001`.
- Dataset/schema/symbol: `GLBX.MDP3` / `trades` / `6E.v.0`.
- Runtime: reviewed Python 3.12.10, Databento 0.55.1,
  `databento-dbn` 0.35.0, DBN version 3.
- Runtime receipt SHA256:
  `E98FB8FC4E26865DF3FEA1FE75064CA86666E17B7781E543B2912BA49F3CC0BD`.
- Source population: exactly the same 329 unique DESIGN identities from the
  frozen free quote; no 2021-2022 identity.
- Each identity must be covered by exactly one verified DBN manifest entry or
  one explicit live zero-byte/no-call entry.
- The parent acquisition aggregate estimate must remain <= USD 1.00 and every
  outcome/validation flag must remain false.

Before record decoding, the tool must verify the terminal parent manifest and
receipt hashes, parent live-plan hash, every DBN path containment, bytes,
SHA256, full-stream record count, request identity and exact `[start,end)`
timestamps. Any mismatch fails the one-shot attempt without a partial feature
artifact.

## Frozen record transform

For each DBN-covered identity:

1. Require DBN metadata version 3, dataset `GLBX.MDP3`, schema `trades`.
2. Iterate every `TradeMsg` exactly once.
3. Require action `T`, integer `size > 0`, and integer `ts_recv` in the exact
   half-open nanosecond interval `[start,end)`.
4. `side == B`: add `size` to buyer-aggressor volume.
5. `side == A`: add `size` to seller-aggressor volume.
6. `side == N`: count as unclassified and add to neither side.
7. Any other action/side, nonpositive size, malformed timestamp, out-of-window
   record, duplicate event identity, manifest mismatch or decode error is a
   hard source-integrity failure.
8. `signed_flow = buy_volume - sell_volume`.
9. Explicit live zero-byte, zero-record, no-direct-side, or tied signed flow is
   a no-trade event. It is never imputed or dropped from coverage.

No magnitude/ratio threshold, event name/type/subset, session, direction,
volatility, spread, price/momentum feature, normalization, winsorization or
parameter exists.

## Frozen feasibility gates

The source passes if and only if all are true:

- coverage is exactly 329/329 unique DESIGN identities;
- at least 313 identities contain at least one valid direct-side trade;
- at least 261 identities have nonzero signed flow;
- buyer-dominant identities are at least 25% of nonzero-flow identities;
- seller-dominant identities are at least 25% of nonzero-flow identities;
- zero hash/byte/count/request-window/metadata/action/side/size/decode/path
  violations;
- zero network/API-key access, outcome fields, EURUSD price access, validation
  source access, return calculation, trade simulation or economic metrics.

These are capability/cadence/balance gates only. Passing does not establish an
edge.

## Output contract

One exclusive local attempt writes canonical artifacts under
`research/evidence/HYP-EVENT-AGGFLOW-EURUSD-TICK-007/`:

- one row per 329 event in `event_signed_flow.csv`;
- `source_quality_summary.json` with counts, direction shares and gate verdicts;
- `artifact_manifest.json` binding every output SHA256/bytes/rows and every
  parent input hash;
- no raw trade rows, price field, target, return, PnL, PF, chart or optimization
  output.

Only a full pass may open a fresh economic/EA successor using the already-
frozen positive-flow=BUY EURUSD, negative-flow=SELL EURUSD mapping, sign-reverse
comparator, +15s entry and +75s exit. Failure terminates that exact mapping; it
may not be rescued with filters, thresholds, a new window or timing change.
