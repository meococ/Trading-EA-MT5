# HYP-MULTI-TSMOM-D1-006 — frozen FX/XAU TSMOM DESIGN

Status: frozen before any V5 or V6 performance/PnL was opened. V6 is a fresh
source-failure-radius child, not a result-selected subset and not a claim that
the weekly system satisfies the final scalping preference by itself.

## Parent failure and child authority

V5's exact nine-asset identity is terminal because BTC official-D1 match was
99.3005%, below the frozen 99.5% source threshold. The other seven FX pairs and
XAU each matched 100%. Independent read-only review confirmed that an eight-feed
child is lawful only under a new identity before economics, with BTC deferred
to an independent source/sleeve contract. Source selection receipt SHA256:
`4F1930263791E7689B88AD42A2C062547C5FC2015474B9FAF67AE385116E5088`.

## Frozen mechanism and execution

- Universe: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCAD, USDCHF, XAUUSD.
- Decision once per UTC Monday at the first common trade-ready generated H1
  tick; a missing active asset invalidates the complete weekly snapshot.
- Signal is the sign of the most recent completed D1 close divided by the
  completed D1 close at/before the 365-calendar-day cutoff, minus one.
- Volatility is sample standard deviation of 60 completed D1 log returns,
  annualized by observed calendar density.
- Inverse-vol weights are capped only downward: 18% single asset, 70% aggregate
  FX, 25% XAU, 25% absolute USD factor and 100% gross. Freed capacity is never
  redistributed upward.
- Signed net-delta rebalancing; reversal closes old direction before opening
  new. No SL/TP, session/news alpha filter, loss filter, time exit, or parameter
  optimization.
- Long-only comparator is the same EX5 with `InpLongOnlyComparator=true`, magic
  `260812010`; primary uses magic `260812009`.

## Frozen engineering identity

- EA source SHA256:
  `FEFF2DF9642CDA30B042BEB1072DCFF90609507CCB37C91CC44FD0FD667D96B3`.
- EA EX5 SHA256:
  `3703DA9939F1A56FC8543C1E3D8BE7A1AE3B8E6EB8035E17DBFFE168177FA198`.
- Compile log SHA256:
  `B5351F22A0263AB4BC2D7CD27CD1D8F2B1400DB83826CD9CF68E1178035C25F9`;
  `0 errors, 0 warnings`.
- V6 imports the eight immutable feeds into fresh source-prefixed
  `*_AFD_TSMOM_V6` symbols. Every receipt verifies H1/M1/D1 counts plus exact
  origin currency base/profit/margin, trade calculation mode and contract
  size. The source prefix is mandatory because MT5 inferred invalid FX
  currencies from the earlier `AFD_*` prefix. All eight receipts bind parent
  source contract SHA256
  `82CB1576C9F7968F111225515A2F303727308A47C5EC2EA47579194F45C6CB9E`.
- Importer source/EX5/compile-log SHA256 values are respectively
  `F6E96CDF3ABCEEA0357FD2B4BF2FD8133FF30BC21DEA044D488B8EAE54F60582`,
  `0AF3740031FA1258D11C0E95C18DC1B8B26EBEFA379B8E592E6D5DD0724A5CCA`
  and `3CBEB083FC8591E823193FF46751ECBCA26DED45611B05D265D859A1C7173959`;
  compile result `0 errors, 0 warnings`.
- Closed bars only: `CopyRates(..., PERIOD_D1, 1, ...)`; no current bar,
  intrabar path, repaint or lookahead authority.
- Engineering attempt `20260812_110615` produced a tester report but failed
  AlphaFactory collection before acceptance because the EA emitted no required
  `DATA_EPOCH_D0_SERIES_PROOF`. It has no economic-verdict authority. The only
  revision above adds a fail-closed, read-only M5/M1 cache witness in `OnInit`;
  signal, sizing, execution, parameters, universe, splits and gates are
  unchanged.
- Attempt `20260812_110939` passed collection but is engineering-invalid for
  economics: the old `AFD_*_DUKA_TSMOM_V5` FX names were parsed by MT5 as
  currencies such as `AFD/_EU`, causing zero FX PnL and zero FX spread-cost
  telemetry. The frozen cost overlay rejected report/telemetry reconciliation.
  V6 now uses fresh source-prefixed symbols and fails `OnInit` unless an
  `OrderCalcProfit` witness for every asset is positive and within 5% of the
  frozen contract formula. No signal, sizing, execution, parameter, split or
  gate changed.
- Engineering attempt `20260812_112944` stopped in `OnInit` before the first
  strategy tick because auxiliary quotes were not yet available for the
  dynamic profit witness. Attempt `20260812_113212` then proved that retrying
  this witness per tick flooded and truncated the required journal. Both have
  zero economic authority. Static currency/calc-mode/contract checks and
  deterministic-price `OrderCalcProfit` witnesses now run once in `OnInit`,
  with no dependence on current/future bars and no strategy-field change.

## Frozen costs

Native imported spread stays in deal PnL. FX commission target is USD 2 per
standard lot per side; XAU is 0.001% of deal notional per side. Native signed
swap is removed and replaced by financing floors of 6% FX and 9% XAU with
weekday coefficients `[1,1,1,1,3,0,0]`. Additional slippage per deal is 0.25,
0.50 and 1.00 contemporaneous spread for base/adverse/severe; commission and
financing multipliers are respectively `(1,1)`, `(1.25,1.5)`, `(1.5,2)`.
Cost contract SHA256:
`FE48C57E936457F7423CA96935E79E75B7994963B8270EF6E2198B11B119DC1F`.

## Frozen splits and DESIGN gates

- DESIGN `[2018-01-01, 2022-01-01)`.
- VALIDATION `[2022-01-01, 2024-01-01)` sealed until DESIGN pass.
- HOLDOUT `[2024-01-01, 2026-08-12)` sealed until VALIDATION pass.

DESIGN needs at least 207 source-valid Monday decisions and 180 completed
rebalances with no failed terminal transition. Native PF after imported spread
must be at least 1.25; base and adverse adjusted net positive; severe adjusted
net nonnegative; base adjusted annual return/native maximum equity DD at least
0.70; native equity DD at most 18%; at least 3/4 profitable calendar years.
Primary must beat the long-only comparator on native PF and base adjusted
annual return. Top 5% realized weeks may contribute at most 25% of positive net
profit and no asset more than 40%.

Failure kills exact V6 with no universe/cap/lookback/direction/cost/exit rescue.
Pass opens sealed validation only; it does not complete the owner goal, claim a
scalping edge, authorize BTC, or authorize paper/live deployment.
