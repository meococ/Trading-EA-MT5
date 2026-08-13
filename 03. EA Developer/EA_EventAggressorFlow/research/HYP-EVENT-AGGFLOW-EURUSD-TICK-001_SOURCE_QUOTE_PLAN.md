# SOURCE QUOTE PLAN - HYP-EVENT-AGGFLOW-EURUSD-TICK-001

Frozen on 2026-08-12 before any immediate-window Databento payload or EURUSD
post-event outcome was read.

## Stage and authority

This packet authorizes exactly one free, metadata-only quote for the 329 frozen
DESIGN events in 2019-2020. It does not authorize a time-series download or any
payment. The 301 events in 2021-2022 remain source-sealed validation and are not
quoted in this attempt. Any positive USD spend requires a later exact Owner
approval bound to the quote ID, plan hash, and ceiling.

Forbidden at this stage: Databento `timeseries` or `batch` calls, trade-print
payload access, EURUSD price/outcome access, economics, charting, MQL5, MT5
Strategy Tester, Model 0/4, optimization, validation, promotion, paper, and live.

## Fresh mechanism and de-duplication

At scheduled high-impact USD/EUR releases, the first 15 seconds contain the
primary exchange-native aggressive flow in CME 6E. Buyer-initiated versus
seller-initiated executed volume is an information set unavailable in broker
OHLC/tick-volume bars. The candidate asks whether that first-wave flow has
enough residual impact for a one-minute EURUSD scalp after all signal inputs are
observable.

This is not a rescue or rename of:

- `HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002`, which used PRE/LATE displayed top-five
  book state and was parked outcome-blind on its frozen continuity gates;
- the killed SCC outcome-selected raw-break book-state/transition clocks;
- the killed ECB-fix signed-flow reversal or pre-fix pressure continuation;
- any session/fix rule, OHLC momentum, wick/sweep, jump, compression, or TSMOM
  family.

The information primitive (executed aggressor flow), source window
(`[0,+15s)`), and decision clock (`+15s`) are all new. The later rule may not
use PRE data, resting depth, price momentum, event names, a magnitude threshold,
or any filter discovered from a readout.

## Frozen source quote contract

- Clock ledger:
  `03. EA Developer/EA_EventCLOBPersistence/research/source/point_release_clocks_2019_2022.csv`
- Clock SHA256:
  `5C30F99FF0E1341D680C2747315E2FF4DFF99C5FBE01C2C5C4036BC101375E7B`
- DESIGN population: exactly 329 unique event clocks whose UTC year is 2019 or
  2020, ordered by event timestamp.
- Sealed validation: exactly 301 clocks in 2021-2022; no metadata request in this
  attempt.
- Dataset: `GLBX.MDP3`
- Schema: `trades`
- Symbol: `6E.v.0`
- `stype_in`: `continuous`
- Cost mode: `historical-streaming`
- Window: half-open `[event_time_utc,event_time_utc+15 seconds)` using the
  historical API receive-time index.
- Quote APIs allowed: `metadata.get_cost` and
  `metadata.get_billable_size` only.
- Quote output: one exclusive canonical JSON receipt under
  `02. AlphaFactory/data/databento/cme_6e_event_aggflow/`.
- The receipt must record per-request estimated cost/billable bytes, aggregate
  cost/bytes, nonzero-byte request count, API counters, exact bindings, and
  explicit zero counters for paid/time-series/batch/outcome access.

Databento's official `trades` schema is the minimum sufficient source: every
record is a trade, `side` is the initiating side, and `size` is order quantity.
`B` means buyer aggressor, `A` seller aggressor, and `N` is unclassified.
Official references:

- https://databento.com/docs/schemas-and-data-formats/trades
- https://databento.com/docs/standards-and-conventions/common-fields-enums-types

## Frozen source transform after a separately authorized purchase

For each exact DESIGN window:

1. Require manifest/hash/byte/count identity and decode only the paid DBN bound
   to that request.
2. Use `ts_recv` as the half-open request clock and require every accepted record
   inside `[event,+15s)`.
3. Require trade action, positive finite size, and direct `side in {B,A}`.
4. `buy_volume = sum(size where side=B)`.
5. `sell_volume = sum(size where side=A)`.
6. `signed_flow = buy_volume - sell_volume`.
7. Empty source, no direct-side volume, or `signed_flow == 0` is an explicit
   no-trade event, never an imputed value.

No magnitude, ratio, event-type, time-of-day, direction, volatility, spread, or
calendar filter exists.

Source feasibility gates before any outcome or MQL5 work:

- at least 313 of 329 DESIGN clocks (95.14%) contain at least one valid direct-
  side trade;
- at least 261 nonzero signed-flow events, equivalent to at least 2.5 eligible
  events per elapsed week over the frozen 104.428571-week DESIGN span;
- buyer- and seller-dominant directions each comprise at least 25% of eligible
  events;
- zero duplicate identities, out-of-window accepted records, hash/count/byte
  mismatches, negative sizes, forbidden API calls, or outcome reads.

The metadata quote is only cost/capability evidence. It cannot itself pass the
decoded source gates or establish market edge.

## Frozen eventual trading contract

This section prevents later timing/management rescue; it does not grant
economic authority.

- Symbol/execution: broker EURUSD real ticks in MT5, one position maximum.
- Signal interval: exact CME receive-time `[event,+15s)`.
- Decision time: `event+15s`, after the entire signal interval is closed.
- Primary direction: positive signed flow -> BUY EURUSD; negative -> SELL.
- Comparator: exact sign reversal. No other arm.
- Entry: first tradable EURUSD tick with timestamp at or after `event+15s`.
- Exit: first tradable EURUSD tick with timestamp at or after `event+75s`.
- Overlapping event while a position is open: deterministic skip.
- No SL, TP, trailing, breakeven, size optimization, event subset, session gate,
  spread entry veto, or weekend rescue.
- Position size is fixed for engineering; economic metrics are evaluated in pips
  and normalized risk, not rescued with sizing.
- Mid-price gross return is reconstructed from logged bid/ask ticks. Per-trade
  event cost is frozen as:
  `C(k) = k * (1.5 + max(0, entry_spread_pips - 1.0))` pips for
  `k in {1.0,1.5,2.0}`. The 1.5-pip floor includes normal spread, commission,
  and baseline slippage; the surcharge makes news-spread slippage dynamic.

## Frozen DESIGN economics gate

If and only if source feasibility passes, one fresh hash-bound MQL5/AlphaFactory
DESIGN attempt may later be opened. It must use 2019-2020 only and must satisfy
all of:

- at least 250 completed primary trades and cadence 2.5-5.0/week;
- base-cost PF >= 1.30 and expectancy > 0;
- 1.5x-cost PF >= 1.25;
- 2.0x-cost PF >= 1.00 and expectancy >= 0;
- both calendar years have positive base-cost net pips;
- max normalized equity drawdown <= 8%;
- sign-reversed comparator base PF is lower than primary PF;
- top 5% of primary events contribute <= 30% of total positive net pips;
- zero source/timing/reconciliation/lookahead violations.

Only a full pass may open a fresh, separately quoted 2021-2022 validation source
plan. Failure freezes this exact mapping. It may not be rescued by changing the
15-second window, +15/+75 timing, direction, event population, costs, management,
or adding thresholds/filters.

