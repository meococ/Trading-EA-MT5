# HYP-MULTI-TSMOM-D1-002 — frozen execution-corrected successor

Frozen before any performance output from this EA identity.

## Parent failure and identity

V2 is the engineering successor to `HYP-MULTI-TSMOM-D1-001`. The parent run
`EA_MultiAssetTSMOMD1V1/20260812_050007` is parked without an economic verdict
because its Monday key was consumed while the broker returned `Market closed`.
V2 changes only the preregistered execution meaning of `Monday at/after 00:00,
next available tick if closed`; it does not revise the strategy from the parent
performance readout.

- EA: `EA_MultiAssetTSMOMD1V2`
- Hypothesis: `HYP-MULTI-TSMOM-D1-002`
- Magic: `260812004`
- Primary tester chart: `EURUSD H1`; all decisions use completed D1 bars only.
- Universe: `EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCAD, USDCHF, XAUUSD, BTCUSD`.
- Warm-up: pre-2018 data only; no warm-up outcome is read.
- DESIGN: `[2018-01-01, 2022-01-01)`.
- VALIDATION: `[2022-01-01, 2024-01-01)` sealed.
- HOLDOUT: `[2024-01-01, latest]` sealed.

## Frozen signal and portfolio

For every symbol, once per broker Monday:

1. `ret252 = Close_D1[1] / Close_D1[253] - 1`.
2. Direction is long for positive `ret252`, short for negative, and flat for
   exact zero. No rank or relative comparison is used.
3. Annual volatility is the sample standard deviation of the 60 closed D1 log
   returns ending at shift 1, multiplied by `sqrt(252)`.
4. Raw absolute weights are normalized inverse volatility.
5. The complete basket is scaled down, never redistributed up, until all caps
   hold: 18% per symbol, 70% FX gross, 25% XAU, 20% BTC, 100% total gross, and
   25% absolute USD-factor exposure with correct base/quote signs.
6. All nine D1 histories are mandatory. Missing, non-finite, or non-monotonic
   source skips the whole week. A target below broker minimum lot is dropped
   without reallocating its weight.
7. USD notional per lot is `contract_size * mid` for USD-quoted symbols and
   `contract_size` for USD-base symbols. Volume rounds down. Planned aggregate
   margin is scaled down above 35% of equity or 80% of free margin.
8. There is no TP, SL, ATR signal, trend filter, breakout, session/news filter,
   rank, or discretionary chart rule. Weekend exposure is accepted.

## Frozen execution correction

At the first EURUSD tick on Monday, V2 attempts to close the complete old
basket. A `Market closed` or other rejected close does not consume the Monday.
The EA retries at a fixed 15-second cadence on incoming primary ticks. Once all
old legs are closed, the completed-D1 target basket is computed exactly once
and remains frozen across retries. The Monday is complete only when every
planned leg is accepted. Any partial open is immediately unwound and the same
basket is retried; `partial_unwinds > 0` invalidates economic interpretation of
the baseline and requires engineering review. A source-gate failure consumes
the week flat, as in V1.

Portfolio catastrophe controls remain 3.5% daily and 7% weekly equity loss.
They close all owned legs and remain locked until the next Monday. Rejected
risk closes are retried; this is risk enforcement, not a signal selector.

## Cost truth

Model 0 pays native tested Bid/Ask spread, tester commission, and current broker
swap. Historical point-in-time swap is unavailable, so any DESIGN survivor is
research-only. Post-run x1.5 and x2 stresses magnify negative observed swap and
other explicit variable costs; positive swap credits are set to zero.

## Frozen gates

Source/execution gate before economics:

- at least 95% of attempted Mondays have all nine valid series;
- no symbol misses more than 8% of attempted Mondays;
- every valid planned week completes exactly one basket;
- `partial_unwinds = 0`, no stale old position crosses a rebalance, and any
  market-closed rejects are followed by a completed retry.

DESIGN continues only if all are true:

- base-cost PF >= 1.20 and positive net expectancy;
- x1.5 adverse-cost PF >= 1.05 and x2 adverse-cost PF >= 1.00;
- maximum equity drawdown <= 18%;
- at least three of four calendar years have positive net return;
- top 5% of weekly profits contribute <= 30% of all positive weekly profit;
- average absolute pairwise correlation of raw weekly returns <= 0.55;
- primary PF and average weekly return beat a separately computed matched
  sign-flipped comparator with identical dates, weights, caps, and costs.

Failure kills this exact hypothesis. No lookback, universe, cap, direction,
filter, session, stop, leverage, cost, or symbol rescue may be derived from the
readout. Validation and holdout remain sealed until every DESIGN gate passes.
