# HYP-G10-XMOM-W1-002 — Frozen Economic Probe Plan

Status: `FROZEN_PRE_OUTCOME_BUILD_ONLY`

## 1. Identity and parent evidence

- Hypothesis ID: `HYP-G10-XMOM-W1-002`.
- Parent source-only ID: `HYP-G10-XMOM-W1-001`.
- Package: `EA_G10WeeklyXSMomentum`.
- Mechanism: one-week cross-sectional spot-return continuation across the seven non-USD G10 currencies represented by `AUDUSD`, `EURUSD`, `GBPUSD`, `NZDUSD`, `USDCAD`, `USDCHF`, and `USDJPY`.
- This is a retail spot-return translation. It is not a replication of academic spot-forward excess returns.
- Parent terminal artifact:
  `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-001_SOURCE_FEASIBILITY/G10XMOM001-SOURCE-001/attempt_terminal.json`.
- Parent terminal SHA256:
  `3FF657763271E77E61DA8110FAE1260710AD9733B2F2B14D613A3AAAB8CEC48F`.
- Parent source inventory SHA256:
  `DCF3754D4B95EFBA2B25A8455CF6DCDF5169C409CE81FE3568F5C7227C98FE01`.
- The parent established source feasibility only: exact 49 stable HCC files for 2018-2024 and two stable symbol-cache files. It did not decode a bar or evaluate an outcome.

## 2. Epistemic scope and trial budget

This child authorizes implementation and synthetic tests only until a later registry row binds exact implementation/test/review hashes. No price, rate, spread, return, rank, signal, trade, cost, PnL, MT5 session, holdout, optimization, promotion, paper, or live access is authorized by this document alone.

The economic trial budget is exactly:

1. one primary weekly momentum arm; and
2. one matched reverse-direction control on the same selected currencies, weeks, sizes, and cost model.

There is no parameter grid, alternative formation horizon, alternative number of legs, filter, session choice, year veto, direction veto, or sequential early stop. A valid economic failure closes this exact child. Any changed mechanism or decision surface requires a fresh ID and preregistration.

## 3. Frozen data contract and split seal

- Canonical terminal: `D:/Trading EA MT5/02. AlphaFactory/runtime/mt5-portable-fivepercent/terminal64.exe`, initialized with `portable=True`.
- Expected terminal data path: the same D-side portable root.
- Expected broker/server: `FivePercentOnline-Real`; all seven exact unsuffixed symbols must resolve with the expected pip geometry (`0.0001`, except `USDJPY=0.01`).
- Working dataset root:
  `02. AlphaFactory/data/fivepercent/G10WeeklyXSMomentum/HYP-G10-XMOM-W1-002/`.
- Product evidence root:
  `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/`.
- Train years: `2018-2021` inclusive. The first eligible trade week requires a completed prior W1 bar inside this window.
- Sealed internal holdout years: `2022-2024` inclusive. No holdout MT5 request, bar, path payload, manifest, or evaluator input may be opened until the frozen train arm and control both complete and the train survivor gates pass.
- Research holdout: `2025+` remains sealed and out of scope even if train and internal holdout pass.
- Acquisition API: `MetaTrader5.copy_rates_range(symbol, TIMEFRAME_W1, ...)`, exact requested years only.
- Runtime must reject a returned bar whose broker-year is outside the currently authorized split.
- Store both raw epoch and a broker-server label; weekly joins use exact monotonically increasing W1 sequence identity rather than inferred intraday UTC entry times.
- Data acquisition is outcome-blind: it may persist W1 OHLC, tick volume, spread field, and source metadata, but it may not calculate ranks, signals, forward returns, trades, PF, expectancy, or drawdown.
- Output is Parquet plus compact JSON manifest, atomically published, D-side only, with file SHA256, row count, schema, symbols, years, first/last bar, terminal metadata, plan SHA, parent inventory SHA, and hard-zero outcome counters.
- Broker historical spread fields are diagnostic only and are not accepted as the economic cost model.

## 4. Frozen signal and execution identity

Currency orientation is fixed:

| Currency | Pair | Orientation |
|---|---|---:|
| AUD | AUDUSD | +1 |
| EUR | EURUSD | +1 |
| GBP | GBPUSD | +1 |
| NZD | NZDUSD | +1 |
| CAD | USDCAD | -1 |
| CHF | USDCHF | -1 |
| JPY | USDJPY | -1 |

For every eligible current week `t`:

1. Use only the fully completed prior weekly bar `t-1`.
2. Currency formation return is `orientation * ln(close[t-1] / open[t-1])`.
3. Rank all seven currencies descending. Exact ties break by currency code ascending.
4. Select top two currencies for long-currency exposure and bottom two for short-currency exposure.
5. Pair direction is `orientation` for a selected long currency and `-orientation` for a selected short currency.
6. Entry price is current W1 `open[t]`; exit price is current W1 `close[t]`. This is the deterministic offline proxy for Monday entry and Friday flat.
7. All four legs are all-or-none. If any of the seven formation bars or any selected current-week entry/exit bar is absent, non-finite, duplicated, non-positive, or misaligned, skip the whole week and log the exact reason. No imputation, carry-forward rank, partial basket, or residual leg is allowed.
8. No weekend position exists after the current W1 close. Weekday overnight exposure is explicit and allowed for this weekly sleeve.
9. The control uses the same four selected currencies and flips every pair direction. It receives identical dates, 10% notional per leg, and costs.
10. No ATR, volatility target, trend, dispersion, gap, session, news, weekday, regime, or liquidity filter is present.

Gross portfolio exposure is fixed at `0.40` (`0.10` account notional per leg). Position sizing is not an alpha input and is identical in both arms.

## 5. Frozen research cost proxy

The screen uses a deliberately conservative, non-promotion cost proxy. It does not claim historical same-broker execution-cost truth.

Frozen spread floors in pips:

| Symbol | Spread floor |
|---|---:|
| EURUSD | 1.0 |
| GBPUSD | 1.4 |
| AUDUSD | 1.2 |
| NZDUSD | 1.5 |
| USDCAD | 1.4 |
| USDCHF | 1.4 |
| USDJPY | 1.2 |

For each leg, x1 round-trip cost is:

`spread_floor + 0.7 commission reserve + 0.3 slippage reserve + 4.0 weekday-rollover reserve` pips.

No positive swap credit is allowed. Cost return is `cost_pips * pip_size / entry_price` and is subtracted from the directed arithmetic pair return. The exact same completed trade set is revalued at x1, x1.5, and x2 by multiplying the whole x1 cost. A missing, zero, negative, non-finite, or unmapped cost is fatal-invalid. A survivor still requires later verified same-broker historical cost provenance before promotion.

## 6. Frozen outputs and metrics

The evaluator must emit:

- one row per leg per arm with split, week identity, prior-bar identity, ranks, selected currency, pair, pair direction, entry/exit, gross return, cost pips, net returns x1/x1.5/x2, and skip provenance;
- one row per elapsed week with eligibility, four-leg completeness, arm return, and equity;
- funnel counts from elapsed weeks to complete joins, eligible baskets, and completed legs;
- aggregate, monthly, half-year, yearly, symbol, currency, side, and arm metrics;
- PF, net return, expectancy, cadence using elapsed calendar weeks, max drawdown, and deterministic Monte Carlo P95 max drawdown;
- exact hashes for plan, parent inventory, dataset manifest, dataset, evaluator, and output artifacts.

PF is `sum(positive net leg returns) / abs(sum(negative net leg returns))`. Weekly portfolio return is `0.10 * sum(four leg net returns)`. Equity compounds weekly from `1.0`. Monte Carlo uses 10,000 bootstrap paths of observed weekly basket returns, path length equal to the evaluated split, deterministic seed `5600102`, and reports the P95 path maximum drawdown.

## 7. Pre-outcome gates

Minimum observations per split before an economic verdict:

- at least 50 eligible complete-basket weeks; and
- at least 200 completed leg trades per arm.

Below minimum is `INVALID_SAMPLE`, never no-edge.

Train and internal holdout must each independently pass all of:

- post-cost x1 PF strictly greater than `1.30`;
- x1.5 PF at least `1.25`;
- x2 PF at least `1.00`;
- positive x1 net return and positive x1 expectancy;
- cadence between `2.0` and `5.0` completed leg trades per elapsed calendar week;
- Monte Carlo P95 max drawdown at or below `8.0%` at the frozen 0.40 gross exposure;
- challenger x1 PF strictly above control x1 PF and challenger x1 net return strictly above control x1 net return.

If train fails any valid fatal gate, the holdout remains sealed and the child is killed. If train passes, one separately authorized holdout run is allowed with no code, parameter, cost, or rule change.

After both splits pass, the combined exact 2018-2024 surface must report all 84 months, 14 half-years, and 7 years and pass:

- positive months ratio at least `0.50`, with no positive month above `20%` of total positive-month profit;
- at least `9/14` positive half-years, with no positive half-year above `35%` of total positive-half-year profit;
- at least `4/7` positive years, with no positive year above `40%` of total positive-year profit.

Passing this probe only permits EA/Model-0 construction. It is not confirmed, promotion-ready, paper-ready, or live-ready.

## 8. Fatal invalidation

- Any price/outcome access before a later hash-bound run-authority row.
- Any holdout access before a terminal train survivor verdict.
- Any use of current/bar-0 data in the formation signal.
- Any incomplete seven-symbol formation join, partial four-leg basket, imputation, or direction/orientation drift.
- Any extra filter, parameter search, alternative horizon, alternative leg count, post-result subgroup veto, or same-ID rescue.
- Dataset/manifest/plan/parent SHA mismatch, non-D data persistence, `FILE_COMMON`, network access, paid request, order submission, or live/paper attachment.
- Cost missing/zero/free, historical spread mislabeled as verified cost, or trade set changed between cost tiers.
- Metrics emitted by the acquisition stage alone.

## 9. Build and future authority

Authorized now after registry binding:

- implement the train-only W1 exporter, offline evaluator, synthetic tests, and static safety checks;
- independent read-only implementation review.

Not authorized now:

- initialize MT5 or call `copy_rates_range`;
- create train/holdout dataset or economic evidence;
- run evaluator on real prices;
- open 2022+ payloads;
- create or compile MQL5;
- run Strategy Tester, optimize, promote, paper trade, or live trade.

Later train acquisition/evaluation authority must bind exact plan, exporter, evaluator, test, and independent-review hashes in the candidate registry. Every runtime authority is one-use and must be revoked in the terminal row.
