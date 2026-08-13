# HYP-CME6E-OPT-PIN-EURUSD-M15-001 - DESIGN source campaign

Status: frozen before opening any 2018-2022 option payload or EURUSD target
series.

## Decision

Two source-only pilots passed on distinct option families:

- Friday Week-2 `2EU.OPT`, expiry 2019-07-12: definition coverage 73.3333%,
  unique unsigned max OI strike 1.1300;
- quarterly `EUU.OPT`, expiry 2019-09-06: definition coverage 75.2874%,
  published-only and zero-completed surfaces both had the same unique max OI
  strike 1.1400.

Both pilots had stable identity, strictly lagged OI, no post-decision records,
no symbol alias carrying OI for a missing definition ID, and no target/outcome
fields.  The missing-OI pattern was similar and every published OI quantity was
positive.  Together with CME's zero-OI Security Definition semantics, absent
Statistics OI for an otherwise stable eligible definition is frozen as zero.
This is a source-capability verdict only, not evidence of a trading edge.

## Frozen universe and period

- DESIGN source period: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`.
- Dataset: `GLBX.MDP3`; DBN; `stype_in=parent`;
  `stype_out=instrument_id`.
- Monthly/quarterly parent: `EUU.OPT`.
- Friday weekly parents: `1EU.OPT`, `2EU.OPT`, `3EU.OPT`, `4EU.OPT`,
  `5EU.OPT`.
- Wednesday weekly parents: `WE1.OPT`, `WE2.OPT`, `WE3.OPT`, `WE4.OPT`,
  `WE5.OPT`.
- A parent with no instruments during a subperiod contributes no event and is
  not an error.  No parent may be added or removed after source readout.

The list is family-complete by construction and is not filtered later by
expiry type, weekday, activity, strike distance, OI magnitude, direction, or
economic performance.

## Outcome-blind event discovery

1. Acquire the `definition` schema for the exact universe and full DESIGN
   source period in one call.
2. Reconstruct definitions point in time.  Eligible rows must have a stable
   instrument ID/symbol mapping, `instrument_class` call or put,
   `user_defined_instrument=N`, one of the frozen assets, source underlying in
   the `6E` futures family, finite positive strike, and a finite source-defined
   expiration within DESIGN.
3. Group exact events by `(asset, underlying, expiration)`.  Require both calls
   and puts.  Derive decision as `expiration - 15 minutes` and require it to be
   an exact UTC M15 boundary.
4. Independently calculate the expected CME clock in `America/Chicago`:
   expirations through 2019-06-09 use 14:00 CT; expirations after 2019-06-09 use
   09:00 CT.  The source-defined expiration must match.  A mismatch fails that
   event and is counted.
5. If more than one frozen asset/family produces the same `(underlying,
   expiration, decision)`, skip all colliding events.  There is no discovery
   order or family-priority tie-break.

## Strict PIT open-interest construction

For each discovered non-overlap event:

1. Quote a `statistics` request only for its frozen parent, from
   `00:00:00Z` on the expiration date to the exclusive decision timestamp.
   Requests sharing identical interval and parent may be coalesced; event
   intervals may not be widened.
2. Admit only `stat_type=9`, finite nonnegative quantity,
   `ts_event < decision`, `ts_recv < decision`, and
   `ts_ref <=` the last completed CME trade date.
3. Map by the latest stable definition before decision and retain the latest
   admissible OI record per instrument.  A published record under an unresolved
   or conflicting identity fails the event; it is not converted to zero.
4. An eligible stable definition with no admissible published OI record is
   assigned zero.  Sum call plus put OI unsigned by exact strike.
5. Empty or all-zero surfaces and ties at the maximum produce no pin.  A single
   positive maximum produces one source-only pin strike.  No price, direction,
   return, or PnL is read or generated.

## Source/cadence gates

All gates are frozen before DESIGN source readout:

- 100% of acquired raw payloads and request/quote/manifests are hash-bound;
- zero unresolved instrument remaps or post-decision inputs are tolerated;
- at least 95% of discovered non-overlap expiry clocks have stable call/put
  definitions and a nonempty timely OI surface;
- at least 90 expiry clocks have a unique positive pin across 2018-2022, keeping
  the earlier 1.5-events/month floor rather than lowering it after pilots;
- at least 48 of 60 DESIGN calendar months contain one unique positive pin;
- no DESIGN calendar month is empty of eligible Euro FX option definitions;
- identical code and absent-OI rules reproduce both pilot receipts.

Failure is `KILL_SOURCE_DESIGN` for this exact mapping.  It cannot be rescued by
changing families, clock, lag, zero completion, tie/overlap handling, cadence,
or coverage after readout.

## Staged acquisition and cumulative budget gate

The naive continuous quote for both schemas and all parents was obtained before
payload acquisition:

- definition: USD 4.653863418847; 2,939,439,880 billable bytes;
- statistics: USD 8.625851720572; 9,261,937,760 billable bytes;
- naive combined: USD 13.279715139419, outside the standing under-USD10
  authority and therefore forbidden.

The campaign is staged to minimize data, not to evade the cap:

1. Phase 1 acquires the one full-period `definition` payload at its live quote,
   only if it remains strictly below USD 10.
2. The frozen discovery algorithm derives exact event intervals without any
   target data.
3. Phase 2 obtains live cost and billable-size quotes for every exact
   event-window `statistics` request.  No statistics payload is acquired unless
   `actual phase-1 spend + combined phase-2 live quote < USD 10`.
4. If the cumulative campaign quote is USD 10 or more, stop and request new
   Owner authority.  Do not split, omit families, or buy partial years to fit.

Phase 1 authorizes one definition payload call only.  Phase 2 requires a new
hash-bound authority receipt containing the source-derived event count, every
request, total quote, cumulative spend, and exact payload-call count.

No trades, MBO, MBP, BBO, OHLCV, fixing price, EURUSD price, outcome, MQL5, MT5,
validation, holdout, optimization, paper, or live operation is authorized by
this source campaign.

