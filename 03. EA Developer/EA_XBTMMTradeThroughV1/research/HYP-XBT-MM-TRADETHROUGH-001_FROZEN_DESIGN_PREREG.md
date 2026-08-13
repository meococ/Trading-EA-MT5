# HYP-XBT-MM-TRADETHROUGH-001 — frozen BitMEX trade-through market making

Frozen before any strategy outcome is computed. The mechanism was produced and
adversarially repaired through Grok `/deep-research-trading-meta5`; Codex
rejected touch/queue-model fills and retained only certain trade-through fills.

## Venue, data, and splits

- Instrument: BitMEX `XBTUSD` inverse perpetual, one USD per contract.
- Source: official daily BitMEX quote and trade archives. Quote rows provide
  best Bid/Ask and both displayed sizes; trade rows provide aggressor side,
  size, and price.
- DESIGN: `[2018-01-01, 2022-01-01)`.
- VALIDATION: `[2022-01-01, 2024-01-01)` sealed.
- HOLDOUT: `[2024-01-01, latest]` sealed.
- Starting collateral: 1 XBT. Report PnL in XBT and contemporaneous USD.

Raw daily archives and normalized event streams are SHA256-bound. Events at an
identical timestamp are processed as: already-live orders against trades,
quote update, then strategy decision. New orders cannot act on their decision
event.

## Frozen candidate

Tick size is USD 0.50. Fixed quote size is 20 contracts per side. With
`microprice = (bidSize*ask + askSize*bid)/(bidSize+askSize)`:

- `bid_limit = min(bestBid, floor_to_tick(microprice - 1 tick))`;
- `ask_limit = max(bestAsk, ceil_to_tick(microprice + 1 tick))`.

Quotes are always passive. There is no size/regime switch, session filter, or
direction filter. A side is amended only when its target changes by at least
two ticks. Any place/amend/cancel action on either side is separated from the
previous action by at least 2,000 ms. An order becomes live 400 ms after the
decision. These limits are fixed before outcomes and stay below the current
3,600 free-quotes/hour QVR allowance.

The soft inventory threshold is 40 contracts and the hard cap is 80. Above +40
contracts the bid is pulled one additional tick away; below -40 the ask is
pulled one additional tick away. A side that would exceed the hard cap is not
quoted.

## Certain-fill rule

A resting buy at `L` fills 20 contracts only when a strictly later
sell-aggressor trade prints below `L`. A resting sell at `L` fills only when a
strictly later buy-aggressor trade prints above `L`. Touches and exact-price
prints never fill. Displayed queue changes and cancellations never award a
fill. This trade-through rule is a price-priority lower bound and avoids
optimistic L1 queue assumptions.

## Inventory, funding, and costs

- Fifteen minutes before 00:00, 08:00, and 16:00 UTC, cancel both quotes and
  flatten inventory at observed Bid/Ask. Resume only after the funding time.
- Inventory reaching 45 minutes of age is flattened the same way.
- Passive fee is 0 bp; no maker rebate is claimed.
- Every forced market flatten pays 7.5 bp taker fee plus the observed spread.
- x1.5 and x2 stresses multiply all taker/funding costs; favorable funding is
  zeroed under stress.
- Inverse PnL for signed contracts is
  `contracts * (1/entry_price - 1/exit_price)` XBT.

The research engine is a virtual exchange simulator inside MQL5 because native
MT5 pending-order fills cannot enforce the strict trade-through condition. It
emits hash-bound fill, inventory, PnL, and source logs. Live mode later maps the
same causal quote state to real passive orders; simulated economics never imply
live fill proof.

## Comparator

The matched null uses the same 20-contract size, 400 ms latency, 2,000 ms global
action interval, hard cap, funding/timeout rules, fees, and trade-through fills,
but quotes plain best Bid/Ask and has no microprice or inventory skew. Candidate
must beat it on PF and average daily PnL.

## Source and engineering gates

- schema, symbol, daily UTC boundary, archive SHA, and event-stream SHA pass;
- timestamps are nondecreasing; no future access;
- crossed-book periods over 50 ms and quote gaps over 60 seconds invalidate the
  affected segment; invalid quote time must be <=0.5% of each day;
- quoting pauses and existing quotes expire whenever current quote age >=2s;
- trade gaps alone are not failures because no-trade is a valid state;
- action interval violations, fill timestamp violations, touch/exact fills,
  future reads, hard-cap violations, or QVR >3,600 actions/hour must be zero.

The source-only 2018-01-01 preflight contained 963,512 events (730,578 quotes,
232,934 trades), zero crossed quotes, maximum quote gap 7.520132 seconds, and
natural trade gaps. No PnL was read when repairing these source gates.

The exact operational boundary is conservative and deterministic: every
virtual order carries `expiry = last_quote_update + 2.000s`. At the first
event with `event_time >= expiry`, both candidate and null orders are marked
expired/non-fillable before any trade match. This local safety expiry is not
an outbound cancel message and therefore does not consume QVR. Explicit
place/amend/cancel messages remain subject to the 2,000ms global interval. An
order becomes fill-eligible at `event_time >= decision_time + 400ms`.

## Design gates

- at least 1,800 strict trade-through fills per year and at least 60% of days
  with one or more fills; below 1,200 fills/year kills for power;
- base PF >=1.30, positive average PnL per filled contract, and positive net
  expectancy after forced-flatten costs;
- x1.5 PF >=1.10 and x2 PF >=1.00;
- maximum USD mark-to-market drawdown <=12%; recovery <=45 calendar days;
- top 5% of days contribute <=25% of positive net PnL;
- average inventory holding time <=12 minutes;
- candidate beats matched null on PF and average daily PnL.

Failure kills this exact hypothesis. No threshold, quote size, latency, fill
rule, time filter, direction, funding avoidance, or cost rescue may be derived
from the readout. Validation and holdout stay sealed until every DESIGN gate
passes.
