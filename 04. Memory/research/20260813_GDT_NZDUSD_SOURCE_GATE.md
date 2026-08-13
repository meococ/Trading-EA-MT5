# GDT Price Index to NZDUSD source gate - 2026-08-13

## Scope and evidence boundary

- Source/mechanism-only, outcome-blind audit of one materially distinct NZDUSD
  object: the overall standard GDT Events `Change in GDT Price Index from
  previous event`, published twice monthly.
- Frozen sign under audit: positive change BUY NZDUSD, negative change SELL
  NZDUSD, zero or unavailable FLAT. GDT Pulse, product-group indices,
  round-by-round data, average price, quantity, thresholds and forecasts were
  excluded.
- No GDT payload or subscription was opened. No NZDUSD price, return, PF, code,
  compile, MT5 run, backtest or purchase was accessed.
- Grok Build independently checked official GDT and RBNZ material. Lead kept
  the final verdict bounded to the public-source and causal-horizon contract.

## Mechanism and public data

- Official results page:
  https://www.globaldairytrade.info/en/product-results/
- Official event calendar:
  https://www.globaldairytrade.info/en/gdt-events/calendar/
- Official FAQ and auction mechanics:
  https://www.globaldairytrade.info/en/gdt-events/gdt-events-frequently-asked-questions/
  https://www.globaldairytrade.info/en/gdt-events/how-gdt-events-work/learn-how-trading-events-operate/
- GDT defines the overall index change as a quantity-weighted aggregation of
  percentage price changes across products, contract periods and sellers. It
  is a real market-price-discovery object, not an NZD price transform.
- Standard events start at 12:00 UTC, normally on the first and third Tuesday,
  and typically last roughly 1.5 to 2.5 hours. GDT says results are published
  on the public Results page shortly after the event.
- The public Results page states that its information may be reproduced when
  Global Dairy Trade is acknowledged as the source. It displays the latest
  result and a current ten-year index chart.
- Exact downloadable results from all events since 2008 are sold through GDT
  Insight Market Pack at USD 99 per month. No subscription is within current
  authority and no purchase was made.

## Sign, clock, PIT and horizon

- RBNZ primary material supports the structural channel: dairy prices have a
  major effect on New Zealand terms of trade and, in turn, the NZD exchange
  rate. Relevant references:
  https://www.rbnz.govt.nz/hub/publications/speech/2014/speech2014-05-07
  https://www.rbnz.govt.nz/monetary-policy/about-monetary-policy/monetary-policy-handbook
- That evidence supports the preregistered polarity economically, but it does
  not define a post-publication H4/D1 NZDUSD holding horizon ending Friday.
  Price discovery occurs round by round during the variable-length auction, so
  some information is already visible to participants before the public final
  result.
- The public contract has no guaranteed event-close timestamp and no exact
  first-public result HH:MM UTC. `Shortly after` is not a deterministic clock;
  the paid pack's 15-20-minute update description also depends on the variable
  close and does not timestamp the free public release.
- The current ten-year chart is not an original-print vintage tape. No free
  official evidence reviewed here proves the exact initially published index
  change and public-use time for every 2018-latest event or a revision chain.
- Roughly 24 standard events per year would provide about 120 TRAIN events in
  2018-2022, 48 validation events in 2023-2024 and fewer than 50 holdout events
  from 2025 through the current date. Even if source timing were cured, the
  validation and holdout counts would require a deliberately modest statistical
  contract; repeated bars under one auction cannot increase independent N.
- The information object is distinct from price momentum, rate/carry,
  calendar-price OCO and the killed DOL seasonal-residual mapping. Novelty does
  not repair publication/PIT/horizon failure.

## Verdict

`NO_GDT_NZDUSD_CANDIDATE`

First fatal gate: a variable-length auction followed by `shortly after` public
publication does not provide a reconstructable first-public clock for every
2018-latest event. The current chart is not a first-print vintage chain, and
the RBNZ structural relation does not specify a Friday-flat H4/D1 horizon.

Do not subscribe to Insight, open Pulse or product-group variants, scrape a
current chart as historical PIT, or open NZDUSD outcomes from this receipt.
This is a scoped source rejection, not global infeasibility. No hypothesis or
registry row is created. Overall goal remains `ACTIVE / UNMET`; no market
mechanism is active.
