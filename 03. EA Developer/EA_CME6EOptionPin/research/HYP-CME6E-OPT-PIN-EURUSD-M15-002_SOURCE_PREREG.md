# HYP-CME6E-OPT-PIN-EURUSD-M15-002 - corrected source preregistration

Status: frozen before producing HYP002 discovery artifacts or acquiring any
new statistics, futures-reference, target, or outcome payload.

## Parent and information mechanism

Parent `HYP-CME6E-OPT-PIN-EURUSD-M15-001` is terminal because its R2 definition
selection was not point in time and its missing-OI-to-zero rule was not proven
by the acquired normalized schemas.  HYP002 is a new source-only child, not a
retroactive edit or economic rescue.

The economic object is the prior-completed-trade-date published CME Euro FX
option open-interest pin observed before the decision.  It is not intraday OI.
If this source object later passes, any direction is a cross-instrument
translation from the 6E options/futures complex to broker EURUSD spot/CFD.
Sonic R may supply execution, risk, telemetry, and fail-closed plumbing only;
Dragon, trend, session, proximity, SL/TP, and chart filters may not alter this
signal mapping.

## Reused source boundary

HYP002 may read only the 60 hash-bound 2018-2022 `GLBX.MDP3 definition`
payloads listed in the HYP001 phase-01 acquisition receipt.  It must not copy,
rewrite, redownload, or charge for them.  It writes to an exclusive HYP002
artifact root.

Frozen families remain `EUU.OPT`, `1EU.OPT` through `5EU.OPT`, and `WE1.OPT`
through `WE5.OPT`.  The DESIGN period remains
`[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`.

## Definition PIT invariant

For every raw symbol:

1. Enumerate the distinct candidate decisions implied by the definition
   history: `D = row.expiration - 15 minutes`, in chronological order.
2. At each candidate `D`, build the state that was actually knowable then:
   rows with both `ts_event < D` and `ts_recv < D`.
3. The active row is the argmax `(ts_recv, ts_event)` inside that knowable
   state.  `D` is a valid fixed point only when
   `active.expiration - 15 minutes == D`.
4. Select the earliest valid fixed point.  This prevents an expiry extension
   received after an earlier decision from silently moving that decision
   later.  A later fixed point cannot replace an already-reached earlier one.
5. Semantic identity (`instrument_class`, `asset`, `underlying`, strike) must
   be invariant within the knowable history at the selected fixed point.
6. Instrument-ID aliases may come only from that knowable history with the
   selected expiration and semantic identity.
7. A symbol with no valid fixed point is absent, never backfilled from a later
   archive snapshot.
8. Persist the selected decision and definition timestamps; assert zero
   selected rows at or after decision and report symbols with multiple fixed
   points rather than hiding them.

Events, overlap handling, CME clock validation, and the 15-minute decision are
otherwise unchanged.  The predeclared clock rule still excludes mismatches;
no timestamp is shifted to rescue an event.

## Strict normalized-OI invariant

If statistics are ever authorized after definition discovery:

- use only `stat_type=9`, finite nonnegative quantity,
  `ts_event < decision`, `ts_recv < decision`, and `ts_ref` equal to the frozen
  prior completed CME trade date;
- retain the latest admissible record per point-in-time instrument identity;
- an explicit published zero is zero;
- a stable listed contract without an admissible normalized OI record is
  `UNKNOWN`, not zero;
- any unknown contract in the event's eligible call/put set makes the event
  source-invalid and produces no pin;
- unresolved aliases, deletes, empty sides, all-zero surfaces, or tied positive
  maxima also fail the event.

No definition distance, activity, moneyness, side, session, family, or later
economic outcome may prune the unknown set.

## Source-only gates

Before any futures reference or EURUSD target can be opened:

- all input payloads and generated artifacts are hash-bound;
- zero selected definition rows are at/after decision;
- zero unresolved semantic identities are used;
- every DESIGN month contains eligible definitions;
- at least 90 non-overlap candidate events survive the definition-only stage;
- after strict OI analysis, at least 95% of candidate events are source-valid,
  at least 90 have a unique positive pin, and at least 48 of 60 months contain
  a pin;
- target/outcome field-use lists remain empty.

Failure is terminal for HYP002.  It cannot be rescued by zero completion,
family/session/proximity filters, clock shifts, thresholds, or price readout.

## Authority boundary

The existing metadata quote is informational only.  A new HYP002 request plan,
live quote, exact authority receipt, cumulative-cost check, and no-retry rule
are required before any statistics payload call.  Economics, MQL5, MT5,
validation, optimization, paper, live capital, and promotion remain closed.

## Primary source anchors

- CME MDP 3.0 Open Interest documents previous-trading-day OI, once-daily
  updates, and explicit zero in Security Definition tag 5792.
- Databento `statistics` documents venue-published statistic records, explicit
  quantity values, and reference timestamps.
- CME SER-8206 supplies the frozen 14:00-to-09:00 Chicago expiry regime change.
