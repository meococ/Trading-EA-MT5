# FivePercent live DOM capability — source-only frontier receipt

Date: 2026-08-12  
Verdict: `PASS_PROSPECTIVE_COLLECTION_ONLY_NO_CANDIDATE`

## Scope

- Read-only capability check against the already configured
  `FivePercentOnline-Real` MT5 terminal.
- No order was sent, no position was modified, no price/return/PnL outcome was
  inspected, and no hypothesis or EA was opened.
- Git was not invoked and is outside this research lane.

## Local diagnostic

The installed MetaTrader5 API (`5.0.5509`) connected to the existing portable
terminal and queried only terminal connectivity, symbol book-depth capability,
subscription success, row counts, book-entry types and tick timestamps.

| Symbol | `SYMBOL_TICKS_BOOKDEPTH` | `MarketBookAdd` | Non-empty polls | Max rows | Entry types |
|---|---:|---|---:|---:|---|
| EURUSD | 16 | true | 19/20 | 15 | 1 and 2 |
| GBPUSD | 16 | true | 19/20 | 15 | 1 and 2 |
| USDJPY | 16 | true | 19/20 | 16 | 1 and 2 |
| XAUUSD | 16 | true | 19/20 | 14 | 1 and 2 |
| BTCUSD | 16 | true | 19/20 | 14 | 1 and 2 |

Poll cadence was 250 ms. The first immediate probe returned zero rows before
the subscription warmed; the bounded follow-up showed current non-empty books
and current tick timestamps on a connected terminal. This proves only that the
broker currently broadcasts a live DOM-shaped stream. It does not prove firm
exchange L2 provenance, historical continuity, unique-book-state capture or
economic information.

## Authoritative platform limitation

MetaQuotes documents that MT5 stores quote and tick history, but not Depth of
Market history. DOM is online-only and is unavailable in Strategy Tester; a
tester replay requires a prospectively collected static resource. MetaQuotes
also notes that an OTC order book may be constructed from information available
to the broker rather than being a firm exchange book.

- https://www.mql5.com/en/book/automation/marketbook
- https://www.mql5.com/en/docs/event_handlers/onbookevent
- https://www.mql5.com/en/docs/marketinformation/marketbookget

## Decision

This capability cannot satisfy the current `2018-latest` reproducibility
contract and cannot authorize a source hypothesis, trading direction, MQL5 EA,
economic backtest, paper trade or live trade. A passive collector could only
begin a future prospective dataset; it would not repair missing history or
prove train/serve identity retroactively. Do not turn the live book subscription
into a current edge claim.

## XAU/Forex source-quality follow-up — 2026-08-13

Verdict strengthened to:
`KILL_CURRENT_FIVEPERCENT_DOM_SIZE_INFORMATION / PRICE_LADDER_ONLY`.

A fresh read-only probe used the current portable FivePercent terminal and all
eight active symbols: `XAUUSD`, `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`,
`USDCAD`, `AUDUSD` and `NZDUSD`. The terminal was connected and reported
`trade_allowed=false`; no order API was called.

Initial subscription returned 13–16 rows per symbol, book depth 16, both entry
types 1 and 2, and current tick timestamps. A bounded quality sample then polled
each symbol 20 times at 250 ms:

- all 160 polls were non-empty and contained both sides;
- depth ranged from 11 to 16 rows;
- XAUUSD, USDJPY and GBPUSD changed frequently, while other symbols changed
  less often during their five-second windows;
- every sampled row on every symbol had the same `volume` and `volume_dbl`
  value: exactly `100000000`; and
- each symbol therefore had exactly one unique volume value across 267–300
  sampled rows.

This is sufficient to reject the current stream as a book-size information
source. It may expose a changing multi-level price ladder, but it contains no
cross-level or time-varying size information from which imbalance, refill,
depletion, absorption or queue pressure can be measured. Any such feature would
be constant or an artifact of level count. Price-ladder dynamics alone collapse
back into the already-closed quote-path/price-geometry family.

No collector was created. Prospective persistence cannot repair the constant
placeholder size, unknown OTC provenance, absent pre-2026 history or Strategy
Tester limitation. Reopen only if the broker/source contract changes and a
fresh outcome-blind probe proves non-constant, source-defined size with stable
units plus an accessible historical/live identity.

A bounded Grok Build source-quality review independently returned the same
`KILL_CURRENT_FIVEPERCENT_DOM_SIZE_INFORMATION`: constant size makes every
size-based feature artifactual; changing prices are only the closed quote-path
family; and prospective polling cannot manufacture historical/source identity.
This agreement is advisory; the local MT5 probe above is authoritative.

## Local terminal/broker frontier follow-up — 2026-08-13

A host inventory found two distinct configured source surfaces rather than a
second deployable broker:

1. `mt5-portable-fivepercent` on `FivePercentOnline-Real`, already killed above
   for constant placeholder size; and
2. `mt5-portable` connected to `MetaQuotes-Demo` / `MetaQuotes Ltd.`.

The install backup has no independent configured base, while the normal
Program Files terminal also exposes only MetaQuotes-Demo. There is no other
configured broker source on this host.

The MetaQuotes-Demo terminal was started hidden for a bounded read-only probe,
then its exact process was closed and verified absent. It was connected with
`trade_allowed=false`, book depth 32 and all eight active symbols available.
Across 20 simultaneous polls at 250 ms:

- all symbols were non-empty and two-sided in 20/20 polls;
- the seven FX majors had 8–16 unique size states, 9–15 size changes and
  23–63 unique size values;
- XAUUSD exposed seven different cross-level size values, but its size state
  did not change within the five-second sample; and
- no order API was called and no target-price outcome was inspected.

This proves a variable-size prospective FX book exists on the demo endpoint,
but it does not create a current candidate. MetaQuotes-Demo has no stored DOM
history or tester replay, is not the intended deploy venue and does not share
FivePercent's size semantics. Verdict:
`PASS_VARIABLE_SIZE_PROSPECTIVE_ONLY / NO_CURRENT_DOM_CANDIDATE`.

No collector was built. A MetaQuotes-Demo collector would be future
infrastructure only: it cannot backfill 2018-current evidence and would train on
a venue whose size field is absent at FivePercent deployment. Grok Build
independently returned the same parity verdict. Reopen only after the intended
broker supplies non-constant sizes plus replayable history, or after Owner
explicitly changes both the deploy venue and evidence window so train venue and
serve venue remain identical.

