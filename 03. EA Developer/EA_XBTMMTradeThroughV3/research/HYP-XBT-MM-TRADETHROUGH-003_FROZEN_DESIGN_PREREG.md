# HYP-XBT-MM-TRADETHROUGH-003 — frozen constant-notional XBTUSD market making

Frozen before any V3 strategy outcome is computed.  V2 remains sealed one-day
engineering evidence.  V3 is a fresh identity because the official XBTUSD lot
size change made V2's 20-contract order and 80-contract hard cap structurally
non-executable during the declared DESIGN population.

Grok `/deep-research-trading-meta5` first proposed one venue lot per quote.
Lead-quant review rejected that rule because it creates a 100x notional jump at
the venue change.  The final rule uses the smallest constant order quantity
that is executable throughout the population: 100 XBTUSD contracts, or USD 100
notional, on every quote.

## Venue specification and population

- Instrument: BitMEX `XBTUSD` inverse perpetual, USD 1 per contract.
- DESIGN: `[2018-01-01, 2022-01-01)`; every calendar day is required.
- VALIDATION: `[2022-01-01, 2024-01-01)` sealed.
- HOLDOUT: `[2024-01-01, latest]` sealed.
- Official archive source: daily BitMEX `quote` and `trade` gzip files.
- Tick size during DESIGN: USD 0.50.  Each daily archive must independently
  pass the frozen price-grid check; a mismatch invalidates the entire DESIGN
  run.
- Venue lot size: 1 contract before `2021-06-08 04:30:00 UTC`; 100 contracts
  from that instant.  The source and engine both assert that every strategy
  order is an integer multiple of the contemporaneous venue lot.

Primary venue references:

- BitMEX technical lot-size announcement, 20 May 2021:
  <https://www.bitmex.com/blog/the-technical-details-of-our-lot-size-change-on-xbtusd-swap-and-xbt-futures>
- BitMEX 2024 minimum-price-increment announcement, which records the pre-change
  XBTUSD tick as USD 0.50:
  <https://www.bitmex.com/blog/site-announcement/coming-soon-changes-to-minimum-price-increments-for-xbtusd-and-ethusd>

## Frozen sizing and risk geometry

- Quote size: 100 contracts per side for all DESIGN timestamps.
- Soft inventory threshold: +/-200 contracts.
- Hard inventory cap: +/-400 contracts.
- Starting collateral: 1 XBT.
- Primary strategy NAV, daily PnL, PF, drawdown, recovery, concentration and
  candidate-vs-null comparison are measured in XBT.  Contemporaneous USD
  strategy PnL and collateral USD mark-to-market are secondary reports only.

This keeps quote notional and the maximum USD contract exposure constant across
the 2021 operational change.  It does not use V1/V2 performance and does not
resize from a backtest readout.

## Frozen candidate and comparator

For valid best bid/ask and positive displayed sizes:

`microprice = (bidSize*ask + askSize*bid)/(bidSize+askSize)`

- candidate bid = `min(bestBid, floor_to_tick(microprice - 1 tick))`;
- candidate ask = `max(bestAsk, ceil_to_tick(microprice + 1 tick))`;
- above +200 contracts, pull the bid one additional tick away;
- below -200 contracts, pull the ask one additional tick away.

The matched null uses the same size, latency, action pacing, caps, fills, costs,
funding retirement and timeout rules, but quotes plain best bid/ask and has no
microprice or inventory skew.  A side is amended only when its target changes
by at least two ticks.

## Certain-fill and execution contract

- A buy resting at `L` fills its full 100 contracts only on a strictly later
  sell-aggressor print below `L`.
- A sell resting at `L` fills its full 100 contracts only on a strictly later
  buy-aggressor print above `L`.
- Touches, exact-price prints, displayed-size changes and cancellations never
  award a fill.
- Place, amend and explicit cancel become effective 400 ms after decision.
- Until cancel/amend is effective, the old order remains fillable.
- Any two outbound decisions are separated by at least 2,000 ms globally.
- Each order expires locally and becomes non-fillable when quote age reaches
  2.000 seconds; this does not consume QVR.

At equal timestamps: activate due PLACE; apply local stale/risk blocks; match
trade against the old live order; apply due CANCEL/AMEND; update quote; then
make decisions.

## Inventory, funding and costs

- FIFO lots; opposing fills close oldest lots first.
- At oldest-lot age >=45 minutes, block maker matching and flatten all residual
  inventory at observed bid/ask.
- For funding time `F`, let `B=F-15m`: block ordinary place/amend from
  `B-4.4s`; bid cancel at `B-2.4s` effective `B-2.0s`; ask cancel at `B-0.4s`
  effective `B`; flatten residual inventory at `B`; maker matching remains
  blocked until `F` passes.
- Passive fee: 0 bp; no maker rebate claimed.
- Forced taker fee: 7.5 bp plus observed spread.
- Inverse PnL: signed contracts * `(1/entry - 1/exit)` XBT.
- Cost stresses: x1.5 and x2 multiply taker/adverse residual costs; favorable
  funding is zero under stress.

## Data and continuity contract

- Every daily quote/trade pair is SHA-256 bound and normalized before MT5.
- Schema, symbol, UTC-day boundary, nondecreasing event time, tick grid and
  event-stream hash must pass.
- Quote gaps over 60 seconds and crossed-book intervals over 50 ms contribute
  to invalid quote time; union invalid time must be <=0.5% of each day.
- No maintenance/event label creates a whitelist.  The observed gap alone is
  measured, and live orders still expire locally at two seconds.
- A missing, corrupt or rejected calendar day invalidates the entire DESIGN
  run.  No failed day is skipped and no economic output is authorized.
- Across valid adjacent files, inventory, FIFO timestamps, pending actions,
  last outbound action, quote freshness and funding state continue without an
  artificial UTC-midnight flatten.

## Engineering and throughput gates

Before reading any V3 economic number:

- all 1,461 DESIGN days are present and source-valid;
- no validation or holdout file was requested, downloaded or indexed;
- processed events equal the deterministic index totals;
- cross-day boundary tests pass;
- action interval, pending latency, funding-live-after-blackout,
  max-age-after-expiry, FIFO, hard-cap, venue-lot, future-read and source
  violations are all zero;
- quote actions/hour is at most 3,600;
- the full no-outcome DESIGN pass completes within four hours on the reference
  machine.

## Frozen economic gates

- at least 1,800 strict trade-through fills per year and at least 60% of days
  with one or more fills; below 1,200 fills/year kills for power;
- base PF >=1.30, positive average XBT PnL per filled contract and positive net
  expectancy after forced-flatten costs;
- x1.5 PF >=1.10 and x2 PF >=1.00;
- maximum XBT strategy-NAV drawdown <=12%; recovery <=45 calendar days;
- top 5% of days contribute <=25% of positive net PnL;
- average inventory holding time <=12 minutes;
- candidate beats matched null on PF and average daily XBT PnL.

Failure kills V3 exactly.  No size, cap, latency, fill rule, session, direction,
funding avoidance, threshold or cost rescue may be derived from its readout.
