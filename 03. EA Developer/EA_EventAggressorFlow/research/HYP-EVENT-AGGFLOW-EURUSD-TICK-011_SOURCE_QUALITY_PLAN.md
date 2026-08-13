# SOURCE QUALITY PLAN - HYP-EVENT-AGGFLOW-EURUSD-TICK-011

Frozen on 2026-08-12 while HYP010 acquisition was still running, after provider
condition warnings were identified, and before any HYP010 trade-record side,
size, or signed-flow distribution was read.

## Purpose and sealed boundaries

HYP011 is one local outcome-blind source qualification attempt for the exact
terminal HYP010 DESIGN corpus. It may decode CME 6E `trades` records only after
HYP010 reaches 329/329 hash-bound coverage and writes its terminal acquisition
receipt. It may not access a network/API key, EURUSD price/tick/bar, validation
source, return/PnL/economics, chart, MQL5, MT5, optimization, paper, promotion,
or live-trading surface.

The terminal HYP010 plan/manifest/receipt/launch/stderr hashes are unknown at
this freeze time. A later HYP011 source-authority receipt may bind only those
hashes plus this plan, the reviewed wrapper/foundation/tests, and the DBNv3
runtime. It may not change the transform or gates below.

## Exact input contract

- Parent: `HYP-EVENT-AGGFLOW-EURUSD-TICK-010` /
  `EVENTAGGFLOW010-TRADES-DESIGN-SOURCE-001`.
- Dataset/schema/symbol: `GLBX.MDP3` / `trades` / `6E.v.0`.
- Exactly 329 unique 2019-2020 DESIGN identities from the frozen quote.
- Each identity is covered once by a verified DBNv3 manifest entry or explicit
  live zero-byte/no-call entry.
- Parent status is `DOWNLOADED_RAW_SOURCE_QUALITY_REQUIRED`, in-flight is null,
  lock and partial files are absent, aggregate worst-case estimate <= USD 1.00,
  and outcome/validation flags are false.
- Runtime receipt SHA256:
  `E98FB8FC4E26865DF3FEA1FE75064CA86666E17B7781E543B2912BA49F3CC0BD`.
- Runtime: Python 3.12.10, Databento 0.55.1, databento-dbn 0.35.0, DBNv3.

Every input DBN is path-contained and rebound by identity, exact `[start,end)`
timestamps, bytes, SHA256, and full-stream record count before its values are
accepted.

## Frozen provider-condition caveats

Databento warned before any flow distribution was read that GLBX.MDP3 was
`degraded` on two dates. Official semantics: data is available, but may contain
missing data or other correctness issues.

- EVT0198, 2020-02-28 19:30:00Z: 408 verified records, 7,197 bytes,
  SHA256 `A327310124EF6DE99888B890FBE0A1322A66236509F0D552411E8F379B8AC6F4`.
- EVT0270, 2020-07-01 12:15:00Z: 82 verified records, 1,716 bytes,
  SHA256 `FC5C15E5FA3AD4C3BA9968A852BEA8BF6BF7A24D9C935C0745A68D86CBD9AA6F`.

Both identities remain in the primary population. Their condition is a source
caveat, not a tunable filter and not an automatic source-gate failure. Any
future economic successor must preregister and report a secondary exclusion
sensitivity before outcome readout; primary acceptance remains all eligible
events. The sensitivity may diagnose dependence but cannot rescue a failing
primary result.

## Frozen transform

For each DBN-covered identity, require metadata DBN version 3, dataset
`GLBX.MDP3`, schema `trades`. Iterate every record once and require:

- action exactly `T`;
- integer `size > 0`;
- integer `ts_recv` within exact half-open nanosecond `[start,end)`;
- side `B`, `A`, or `N` only.

Then:

- `buy_volume = sum(size where side=B)`;
- `sell_volume = sum(size where side=A)`;
- `signed_flow = buy_volume - sell_volume`;
- `N` is counted but contributes to neither side;
- live zero-byte, zero-record, no-direct-side, and tied-flow events are explicit
  no-trade events and never imputed.

Any unknown action/side, nonpositive size, malformed/out-of-window timestamp,
duplicate identity, decode/path/metadata/hash/byte/count mismatch is a hard
integrity failure. No magnitude/ratio threshold, event subset/type, session,
direction, volatility, spread, price/momentum, normalization, winsorization,
or parameter exists.

## Frozen feasibility gates

Pass if and only if:

- coverage is exactly 329/329 unique DESIGN identities;
- at least 313 identities contain at least one valid direct-side trade;
- at least 261 identities have nonzero signed flow;
- buyer-dominant share is at least 25% of nonzero-flow identities;
- seller-dominant share is at least 25% of nonzero-flow identities;
- all integrity-violation counters are zero;
- network/API-key/outcome/validation/return/trade-simulation/economic counters
  remain zero.

Passing proves source capability/cadence/balance only, not edge.

## Output and terminal rule

One exclusive attempt writes only:

- `event_signed_flow.csv`, one aggregate row per event;
- `source_quality_summary.json`;
- `artifact_manifest.json` binding inputs and outputs.

No raw trade rows, price, target, return, PnL, PF, or chart is emitted. A full
pass may open a fresh economic/EA successor using only the already-frozen
positive-flow=BUY EURUSD, negative-flow=SELL EURUSD mapping, sign-reverse
comparator, +15s entry, and +75s exit. Failure terminates that exact mapping and
cannot be rescued by filters, thresholds, a new source window, or timing change.
