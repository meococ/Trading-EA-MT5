# TRAIN ECONOMIC PROBE PLAN — HYP-EUVIX-EURUSD-M1-001

Frozen at `2026-07-29T17:41:43.762Z`, before joining lagged VIX states to any
EURUSD PnL. The VIX file, feature algorithm and feature-only cadence were
hash-bound before target outcomes were filtered. Any threshold, window, clock,
direction, cost, or gate change requires a new hypothesis ID.

## Identity and decision use

- Hypothesis: `HYP-EUVIX-EURUSD-M1-001`
- Research-only package: `EA_EuropeOpenUSDDemand`
- Parent economic object: killed `HYP-EUUSD-EURUSD-M1-001`
- Symbol/timeframe: EURUSD completed-Bid M1 close proxy
- DESIGN/TRAIN: 2016-2020
- Validation 2021-2024 and research holdout 2025+: sealed
- Attempt: `EUVIX001-TRAIN-ECON-001`, exactly once

An all-gate pass authorizes only a fresh MQL5/Model-0 task packet. It does not
authorize validation, holdout, optimization, promotion, paper, or live.

## Fresh mechanism and source boundary

Krohn, Mueller and Whelan document that fix reversal returns are higher when
market volatility is high and estimate the relationship using lagged VIX. They
interpret this as compensation for constrained dealer intermediation. Their
Table I also ranks the pre-ECB EUR effect materially stronger than JPY. The
unfiltered EURUSD translation confirmed the correct gross sign (gross PF
`1.136519`, random-sign `p=0.045395`) but failed after cost (x1 PF `0.968723`).

Primary paper: *Foreign Exchange Fixings and Returns Around the Clock*, Journal
of Finance, DOI `10.1111/jofi.13306`; open working paper:
`https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf`.

External feature source: CBOE VIX daily close via FRED series `VIXCLS`:
`https://fred.stlouisfed.org/series/VIXCLS`.

This hypothesis is a prospective binary translation of the paper's continuous
lagged-VIX result. It is not an exact replication of their regression or
Refinitiv data. It does not use the observed Wednesday/month buckets, shift the
trade clock, reduce costs, or refit the parent rule.

## Frozen target and feature data

Parent EURUSD trade ledger:

- path:
  `03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUUSD-EURUSD-M1-001/EUEUR001-TRAIN-ECON-001/trades.jsonl`
- SHA256:
  `204050AAA213DB1BC468FD022733425DC3E2E70EF33A742A0A7D620EF8B166E8`
- required rows: `1,296`, exact parent short-EURUSD daily population.

VIX snapshot:

- CSV:
  `02. AlphaFactory/data/fred/VIXCLS/VIXCLS_2015-12-01_2020-12-31.csv`
- CSV SHA256:
  `2280FF566149A58E2FD3B137686D94D9C0E6E2C884C2A77BC02BA7FFB7F6B248`
- Manifest:
  `02. AlphaFactory/data/fred/VIXCLS/VIXCLS_2015-12-01_2020-12-31.manifest.json`
- Manifest SHA256:
  `864AEA48C737A091D7DE0C5503C72551015C4C20EEF70814595A5CD34B80BA7C`
- required rows/valid closes: `1,281`; 2015-12-01 through 2020-12-31.

Prior DSR ledgers are hash-bound for LOJM001, LOFIX002, EUUSD-USDJPY-001,
and EUUSD-EURUSD-001. The common evaluator and canonical DSR module are also
bound. All data/evidence stays on `D:`.

## Frozen pre-entry VIX state

For each parent local trade date `t`:

1. Select the last valid FRED VIX daily close with observation date strictly
   less than `t`; same-date U.S. close is forbidden because the EUR trade
   starts before that close exists.
2. For the selected VIX observation at index `j`, compute the median of the
   immediately prior `252` valid VIX closes, excluding observation `j`.
3. Require at least `60` prior valid closes; otherwise the date is ineligible.
4. `high_vix = VIX[j] >= trailing_prior_median[j]`.
5. Trade only when `high_vix` is true. Direction, prices and costs are copied
   exactly from the bound parent ledger: SHORT EURUSD from Europe/Berlin
   `07:59` completed close to `14:14` completed close.

The `252`-observation lookback is a conventional one-year daily state estimate;
the `60`-observation warm-up prevents a short initial threshold. Neither was
selected using target returns. Feature-only pre-outcome checks found 595
eligible business dates and cadence `2.280118` per elapsed week before joining
the feature to the 1,296 parent outcomes.

## Frozen costs, controls, and trials

- Costs: x1=`1.50`, x1.5=`2.25`, x2=`3.00` pips per selected trade.
- Primary/reverse PnL columns come from the exact parent trade prices and are
  recomputed from gross pips and costs.
- Matched reverse: same selected dates, opposite direction.
- Parent benchmark: unfiltered parent x1 PF `0.9687234884904704`, x1 expectancy
  `-0.29868827160493405` pips.
- One-sided random-sign test: `10,000`, seed `20260729`.
- DSR: ten x1 arms—four prior primary/reverse pairs plus current
  primary/reverse. Cost tiers are not extra trials.

## Structural and economic gates

Structural gates, all required:

1. at least `500` selected parent trades;
2. VIX mapping coverage `>=95%` of the 1,296 parent rows;
3. selected cadence `2.0` to `5.0` per elapsed calendar week;
4. at least `30` selected trades in every local year;
5. largest selected year share `<=40%`.

Economic gates, all required on the same selected population:

1. primary x1 PF `>1.30`;
2. primary x1.5 PF `>=1.25`;
3. primary x2 PF `>=1.00`;
4. primary x1 expectancy `>0`;
5. at least four of five local years positive at x1;
6. random-sign p-value `<=0.05`;
7. ten-arm DSR `>=0.95`;
8. primary x1 PF and expectancy both exceed the matched reverse **and** the
   frozen unfiltered parent benchmark.

Structural failure makes no economic claim. Structural pass plus any economic
failure is `KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED`; only 8/8 is
`PASS_TRAIN_PROXY_AUTHORIZE_FRESH_MQL5_MODEL0_PACKET_ONLY`.

## One-shot evidence and prohibitions

Before execution, armed/disarmed tests must pass. Registry authority must bind
this plan, normalized evaluator, tests, parent/prior ledgers, VIX CSV/manifest,
common evaluator and DSR. Evidence root must be absent:

`03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUVIX-EURUSD-M1-001/EUVIX001-TRAIN-ECON-001/`

Forbidden under this ID: changing 252/60 or comparison operator, using same-day
VIX, selecting weekday/month/year, shifting trade clocks, reducing costs,
adding an indicator/stop/target, accessing 2021+, optimization, MQL5/MT5,
Model 0/4, promotion, paper, or live.
