# HYP-MULTI-TSMOM-D1-003 — frozen common-readiness successor

Frozen before any performance output from this EA identity. Grok's
`/deep-research-trading-meta5` review confirmed this as a pure execution repair
after rejecting a logically impossible decision-time quote bound and a
post-hoc 15-minute cutoff.

## Parent failures and unchanged alpha

- V1 (`HYP-MULTI-TSMOM-D1-001`) consumed Monday while markets were closed.
- V2 (`HYP-MULTI-TSMOM-D1-002`) generated 199 partial-basket unwinds while
  FX/BTC were open and XAU remained closed; the tester stopped in 2020.
- Neither parent has an economic verdict. Their PF/readout is forbidden as a
  strategy decision or tuning input.

V3 preserves the exact alpha contract:

- EA `EA_MultiAssetTSMOMD1V3`, hypothesis `HYP-MULTI-TSMOM-D1-003`, magic
  `260812005`, primary chart `EURUSD H1`;
- exact universe `EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCAD, USDCHF,
  XAUUSD, BTCUSD`;
- `ret252 = Close_D1[1] / Close_D1[253] - 1`, direction by sign only;
- annual volatility is sample standard deviation of 60 closed D1 log returns
  ending at shift 1, multiplied by `sqrt(252)`;
- normalized inverse-vol weights, scaled down without upward redistribution to
  18% single, 70% FX gross, 25% XAU, 20% BTC, 100% total gross, and 25% absolute
  USD-factor caps;
- all nine D1 sources are mandatory; below-minimum lot drops only that leg and
  does not reallocate its weight;
- no TP, SL, breakout, ATR signal, session/news alpha filter, rank, or
  discretionary chart rule; weekend exposure remains accepted;
- planned margin cap remains 35% of equity and 80% of free margin;
- portfolio catastrophe controls remain 3.5% daily and 7% weekly equity loss.

DESIGN is `[2018-01-01, 2022-01-01)`. VALIDATION `[2022-01-01, 2024-01-01)`
and HOLDOUT `[2024-01-01, latest]` remain sealed.

## Frozen causal readiness and atomicity contract

At the first observed tick of each broker Monday, V3 records `decision_time`
and computes the nine closed-D1 signals, volatilities, and capped weights once.
This snapshot is never recomputed.

For every causal retry time, all nine symbols must simultaneously satisfy:

- `SymbolInfoTick` succeeds, Bid > 0, Ask > Bid;
- tick time is not in the future and is no more than 60 seconds old relative to
  the current retry time;
- the published MT5 trade session for that symbol is open.

If any check fails, the EA sends zero close/open orders and retries after at
least 15 seconds on primary ticks. There is no intra-Monday cutoff. If no common
readiness occurs before Tuesday, the week is failed and the prior basket stays
unchanged.

Only after common readiness:

1. close every old strategy position;
2. convert frozen weights to lots exactly once using current fresh prices and
   current equity after the old basket is flat;
3. submit every planned new leg.

Any partial close, partial fill, partial open, or partial unwind makes the run
engineering-invalid. The code may continue only to collect diagnostics; no
economic metric from such a run is admissible.

## Cost and gates

Model 0 pays native tested Bid/Ask spread, tester commission, and current broker
swap. Historical point-in-time swap is unavailable. A DESIGN survivor remains
research-only and must later pass x1.5/x2 adverse cost stress with positive swap
credits zeroed.

Engineering gates before economics:

- expected Mondays = source attempts = 208 for 2018-2021;
- valid snapshots / attempts >= 95%; atomic success / valid snapshots >= 95%;
- full 2018-2021 tester coverage and no stop-out;
- partial close = partial open = partial unwind = basket recomputation =
  orders outside common readiness = 0.

Economic gates remain unchanged: base PF >= 1.20 with positive expectancy;
x1.5 PF >= 1.05; x2 PF >= 1.00; maximum equity DD <= 18%; at least 3/4 positive
design years; top 5% weekly profit contribution <= 30%; average absolute raw
weekly return correlation <= 0.55; and primary PF plus average weekly return
must beat the matched sign-flipped comparator.

Failure kills this exact hypothesis. No lookback, universe, cap, direction,
filter, session, stop, leverage, cost, or symbol rescue may be derived from the
readout.
