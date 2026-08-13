# HYP-MULTI-TSMOM-D1-002 — engineering execution failure

Status: `PARK_ENGINEERING_PARTIAL_BASKET_CHURN_AND_STOP_OUT_NO_ECONOMIC_VERDICT`

Run: `02. AlphaFactory/runs/EA_MultiAssetTSMOMD1V2/20260812_051406`

V2 correctly stopped consuming the Monday after a rejected order, but its
15-second retry still submitted liquid FX/BTC legs while XAUUSD was closed. It
then unwound the accepted partial basket and repeated the same process until
XAU opened. The first design Monday alone accumulated about 1,600 accepted
entries before one complete nine-leg basket was established.

Terminal evidence:

- `attempts=106`, `full_source=106`, `valid_baskets=106`, but the test terminated
  on 2020-01-13 instead of covering the frozen 2018-2021 design interval;
- `entries_requested=2853`, `entries_accepted=2546`;
- `rebalance_retries=19805`, `partial_unwinds=199`;
- `market_closed_rejects=27509`, including rejected closes while XAU was shut;
- `completed_rebalances=106` (52 in 2018, 52 in 2019, 2 in 2020, 0 in 2021);
- the tester ended after a stop-out event and reported only 50% interval
  completion.

The headline 2,546 trades, PF 0.5567505929, and net loss therefore include
mechanical partial-basket churn and an incomplete date range. They are not an
economic test of the frozen hypothesis and must not be used for strategy
tuning or rejection.

Authorized successor scope: a fresh identity may add a causal common-market
readiness barrier before any old-basket close or new-basket order. Every symbol
must have a valid, recent tick at the decision time; otherwise the EA remains
unchanged and retries without sending any order. Signal, lookback, universe,
weights, caps, cost, risk, and date partitions remain frozen.
