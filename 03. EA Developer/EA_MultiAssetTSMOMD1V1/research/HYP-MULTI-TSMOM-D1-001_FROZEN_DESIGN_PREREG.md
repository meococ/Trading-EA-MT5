# HYP-MULTI-TSMOM-D1-001 — frozen nine-asset design baseline

Frozen before any performance output from this EA identity.

## Thesis and identity

The candidate is slow own-instrument time-series momentum, not cross-sectional
currency ranking. Persistent multi-month price trends are attributed to gradual
capital reallocation and under-reaction across liquid markets. The first cell is
the fixed portfolio `EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCAD, USDCHF,
XAUUSD, BTCUSD` on a FivePercent USD account. The primary tester chart is
EURUSD H1; decisions use completed D1 bars only.

- EA: `EA_MultiAssetTSMOMD1V1`
- Hypothesis: `HYP-MULTI-TSMOM-D1-001`
- Magic: `260812003`
- Warm-up: pre-2018 data only; no warm-up outcome is read.
- DESIGN: `[2018-01-01, 2022-01-01)`.
- VALIDATION: `[2022-01-01, 2024-01-01)` sealed.
- HOLDOUT: `[2024-01-01, latest]` sealed.

## Frozen signal and portfolio

At the first EURUSD H1 tick on each broker Monday, for every symbol:

1. `ret252 = Close_D1[1] / Close_D1[253] - 1`.
2. Direction is long for positive `ret252`, short for negative, flat for exact
   zero. No rank or relative comparison is used.
3. Annual volatility is the sample standard deviation of the 60 closed D1 log
   returns ending at shift 1, multiplied by `sqrt(252)`.
4. Raw absolute weights are normalized inverse volatility.
5. The complete basket is scaled down, never redistributed up, until all caps
   hold: 18% per symbol, 70% FX gross, 25% XAU, 20% BTC, 100% total gross, and
   25% absolute USD-factor exposure. USD factor includes FX, XAUUSD and BTCUSD
   with the correct base/quote sign.
6. The old basket is closed and the new basket is opened once per Monday. There
   is no TP, SL, trend filter, breakout, ATR signal, session/news filter, rank,
   or discretionary chart rule. Weekend exposure is accepted.
7. All nine D1 histories are mandatory for a weekly economic decision. A
   missing/non-finite/non-monotonic series skips the whole week. A target below
   broker minimum lot is dropped without reallocating its weight.
8. USD notional per lot is `contract_size * mid` for USD-quoted symbols and
   `contract_size` for USD-base symbols. Volumes round down. Aggregate planned
   margin is scaled down above 35% of equity or 80% of free margin.

Portfolio-only catastrophe controls are frozen: a 3.5% daily or 7% weekly
equity loss closes all legs and stays flat until the next Monday. They are risk
overrides, not signal selectors.

## Cost truth

Model 0 pays native tested Bid/Ask spread, tester commission, and current broker
swap. Historical point-in-time swap is unavailable, so any DESIGN survivor is
research-only. Post-run x1.5 and x2 stresses magnify negative observed swap and
set positive swap credits to zero; they never increase a favorable credit.
Slippage/commission adequacy must be checked from the deal report before any
validation is opened.

## Frozen gates

Source gate before economics:

- at least 95% of attempted Mondays have all nine valid series;
- no symbol misses more than 8% of attempted Mondays;
- no order/runtime failure invalidates the portfolio identity.

DESIGN continues only if all are true:

- base-cost PF >= 1.20 and positive net expectancy;
- x1.5 adverse-cost PF >= 1.05 and x2 adverse-cost PF >= 1.00;
- maximum equity drawdown <= 18%;
- at least three of four calendar years have positive net return;
- top 5% of weekly profits contribute <= 30% of all positive weekly profit;
- average absolute pairwise correlation of raw weekly returns <= 0.55;
- primary PF and average weekly return exceed a separately computed matched
  sign-flipped comparator with identical dates, weights, caps and costs.

Failure kills this exact hypothesis. No lookback, universe, cap, direction,
filter, session, stop, leverage, cost, or symbol rescue may be derived from the
readout. Validation and holdout remain sealed until every DESIGN gate passes.
