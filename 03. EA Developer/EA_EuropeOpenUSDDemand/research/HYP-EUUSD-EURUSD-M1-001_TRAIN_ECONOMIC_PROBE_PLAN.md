# TRAIN ECONOMIC PROBE PLAN — HYP-EUUSD-EURUSD-M1-001

Frozen at `2026-07-29T17:27:36.855Z`, before reading any EURUSD return from
Europe/Berlin `08:00` to the `14:15` ECB-fix boundary. Any clock, direction,
cost, filter, exit, or gate change requires a new hypothesis ID.

## Identity and decision use

- Hypothesis: `HYP-EUUSD-EURUSD-M1-001`
- Research-only package: `EA_EuropeOpenUSDDemand`
- Symbol/timeframe: `EURUSD`, completed Bid `M1` close proxy
- DESIGN/TRAIN: `2016-01-01` through `2020-12-31`
- Validation `2021-2024`: sealed; research holdout `2025+`: forbidden
- Attempt: `EUEUR001-TRAIN-ECON-001`, exactly once
- Owner objective: cost-adjusted PF above `1.30`, not gross seasonality.

Only an 8/8 economic pass may authorize a fresh MQL5/Model-0 packet. It does
not authorize validation, holdout, optimization, promotion, paper, or live.

## Mechanism and ex-ante symbol choice

Krohn, Mueller and Whelan document unconditional USD appreciation from the
European market opening at `08:00` Frankfurt time to the `14:15` ECB fix. Their
Table I reports the pre-ECB foreign-currency return for EUR at `-8.87%`
annualized (`t=-7.24`) versus JPY at `-2.61%` (`t=-2.37`) over 1999-2019. The
negative foreign-currency return maps to **short EURUSD**. Their proposed
mechanism is dealer inventory and pre-fix USD demand, not opening-price
momentum. The paper also warns that transaction costs remove much of the
apparent profit.

Primary source: Krohn, Mueller and Whelan, *Foreign Exchange Fixings and
Returns Around the Clock*, Journal of Finance, DOI `10.1111/jofi.13306`; open
working paper:
`https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf`.

The prior USDJPY cell was frozen and run first because it continued the active
JPY lane. It produced gross PF `1.051219` and x1 PF `0.887604`. Selecting EURUSD
now is not a favorable bucket found in that result: EUR is a distinct symbol
and data contract, and the public source ranked its pre-ECB effect materially
stronger before this EURUSD target window was opened. No USDJPY clock, day,
month, cost, or rule is reused as a rescue.

## Prior trials and DSR universe

The same 2016-2020 DESIGN parquet has already supported multiple hypotheses, so
this is TRAIN discovery only. Eight x1 arms are frozen for DSR:

1. LOJM001 primary and reverse;
2. LOFIX002 primary and reverse;
3. EUUSD-USDJPY-001 primary and reverse;
4. current EURUSD primary and reverse.

Cost tiers are not extra arms. The exact prior ledger hashes are bound below.

## Frozen data and dependency contract

- Parquet SHA256:
  `C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6`
- Manifest SHA256:
  `4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8`
- Required EURUSD rows: `1,859,939`; columns exactly
  `symbol,time_utc,close`; unique increasing timestamps; DESIGN years only.
- LOJM001 ledger SHA256:
  `6985108DEEDF59A503F5A96285F7D5CC8D8CE303FC03A599B5C3E414E0ECDC98`
- LOFIX002 ledger SHA256:
  `04270A2E9772A884322753701D55B6101109B1BA1E49ABFF59F89B882815A6DB`
- EUUSD-USDJPY-001 ledger SHA256:
  `18D8C2333FE421DFA279325D30A29D759AAD4333A304BA1FC68E7B485009E10C`
- Bound common/helper evaluator SHA256:
  `A8E8E61A8D75E9D95808A637E3E876A627DDBC8906EDF94743A79F1DCF691A63`
- Canonical DSR SHA256:
  `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`

All sources/evidence remain on `D:`. Any hash drift, wrong population, invalid
price/time, opened validation/holdout counter, existing evidence root, or
consumed attempt fails closed.

## Frozen clock, direction, and execution proxy

Timezone: `Europe/Berlin`, including DST. For every complete local weekday:

1. Entry is the completed `07:59` M1 Bid close, observable at `08:00`.
2. Exit is the completed `14:14` M1 Bid close, observable at `14:15`.
3. Direction is always `SHORT EURUSD` (`-1`).
4. `raw_move_pips = (exit_close - entry_close) / 0.0001`.
5. Primary gross = `-raw_move_pips`; matched reverse = `+raw_move_pips`.
6. Missing either exact boundary skips the day; no nearest/fill-forward bar.

No indicator, news rule, weekday/month/year veto, volatility filter, stop,
target, trailing rule, re-entry, or carry is present.

## Frozen costs, statistics, and gates

- Round-trip costs: x1=`1.50`, x1.5=`2.25`, x2=`3.00` pips per trade.
- Net = arm gross minus cost. Zero or missing cost is not verified zero cost.
- One-sided random-sign permutation of primary gross mean: `10,000`, seed
  `20260729`.
- DSR: canonical implementation, eight declared x1 arms; invalid result is `0`.

Structural gates, all required:

1. at least `1,000` complete trades;
2. weekday coverage at least `95%`;
3. cadence `2.0` to `5.0` per elapsed calendar week;
4. largest year share no more than `25%`;
5. every trade is fixed short with the exact frozen boundaries.

Economic gates, all required on one population:

1. primary PF x1 `>1.30`;
2. primary PF x1.5 `>=1.25`;
3. primary PF x2 `>=1.00`;
4. primary x1 expectancy `>0`;
5. at least four of five years positive at x1;
6. one-sided random-sign p-value `<=0.05`;
7. eight-arm DSR `>=0.95`;
8. primary x1 PF and expectancy both exceed the matched reverse.

Structural failure is engineering/data invalid. Structural pass with any
economic failure is `KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED`. Only 8/8 is
`PASS_TRAIN_PROXY_AUTHORIZE_FRESH_MQL5_MODEL0_PACKET_ONLY`.

## One-shot evidence and prohibitions

Before execution, armed/disarmed tests must pass and the registry must hash-bind
the plan, normalized evaluator, test, data, three prior ledgers, helper, and DSR.
The latest authorized row SHA is then inserted into the one sentinel.

Evidence root:

`03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUUSD-EURUSD-M1-001/EUEUR001-TRAIN-ECON-001/`

It must be absent and written exclusively with attempt-start, complete ledger,
and terminal JSON. Forbidden: moving clock, switching symbol/direction, any
post-outcome filter, lower cost, indicator/stop/target, 2021+ access,
optimization, MQL5/MT5, Model 0/4, promotion, paper, or live.
