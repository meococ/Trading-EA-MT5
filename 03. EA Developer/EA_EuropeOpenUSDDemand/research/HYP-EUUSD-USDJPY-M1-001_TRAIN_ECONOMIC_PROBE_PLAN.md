# TRAIN ECONOMIC PROBE PLAN — HYP-EUUSD-USDJPY-M1-001

Frozen at `2026-07-29T17:14:34.171Z`, before reading any USDJPY return from
the Europe/Berlin `08:00` open proxy to the `14:15` ECB-fix boundary. Any
change to the clock, direction, costs, filters, exits, or gates requires a new
hypothesis ID. This is a one-shot DESIGN/TRAIN screen, not validation.

## Identity and decision use

- Hypothesis: `HYP-EUUSD-USDJPY-M1-001`
- Research-only package: `EA_EuropeOpenUSDDemand`
- Symbol/timeframe: `USDJPY`, completed Bid `M1` close proxy
- DESIGN/TRAIN: `2016-01-01` through `2020-12-31`
- Validation `2021-2024`: sealed
- Research holdout `2025+`: forbidden
- Attempt: `EUUSD001-TRAIN-ECON-001`, exactly once
- Owner objective: find a sleeve with cost-adjusted PF above `1.30`, not a
  favorable gross curve or a publishable seasonal average.

A full pass authorizes only a fresh MQL5/Model-0 packet. It does not authorize
validation, holdout access, optimization, promotion, paper trading, or live
trading. A failure kills only this exact clock/direction/data/cost object.

## Mechanism and primary-source boundary

Krohn, Mueller and Whelan document an unconditional intraday USD-demand
pattern around major FX fixes. Their spot return is expressed as foreign
currency per USD, so positive USD appreciation maps directly to a **long
USDJPY** position. Their pre-ECB window runs from the European market opening
at `08:00` Frankfurt time to the ECB fix at `14:15` local time. For JPY, their
1999-2019 Table I reports a negative foreign-currency return in that window,
consistent with USD appreciation. The paper links the pattern to dealer
inventory and pre-fix hedging, and separately shows that transaction costs can
remove most apparent trading profits.

Primary sources:

- Krohn, Mueller and Whelan, *Foreign Exchange Fixings and Returns Around the
  Clock*, Journal of Finance, DOI `10.1111/jofi.13306`; open working paper:
  `https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf`.
- FCA Occasional Paper 46, *Fixing the Fix? Assessing the Effectiveness of the
  4pm Fix*:
  `https://www.fca.org.uk/publication/occasional-papers/occasional-paper-46.pdf`.

This probe is a narrow workspace replication of the paper's pre-ECB USD-demand
leg on one pair and a broker-derived close-only source. It is not a replication
of Refinitiv quotes, order flow, the post-London leg, or the multi-currency
portfolio. The mechanism differs materially from the killed LOJM/LOFIX rules:
there is no opening-return sign, no same-direction forecast, and no 15:30-16:00
target. It is an unconditional inventory-seasonality object.

## Adverse prior and trial accounting

- `HYP-LOJM-USDJPY-M1-001` killed the London `08:00-08:30` sign followed in the
  same direction through `16:30`; its x1 PF was `0.793002`.
- `HYP-LOFIX-USDJPY-M1-002` killed the London `08:00-08:30` sign followed in the
  same direction during `15:30-16:00`; gross PF was `0.960619` and x1 PF was
  `0.594534`.
- These failures are adverse evidence for naive intraday momentum, but they do
  not test the present unconditional Europe-open-to-ECB-fix inventory claim.
- The same 2016-2020 DESIGN source has already been opened for other windows.
  Therefore this is an additional TRAIN trial, never independent confirmation.
- DSR universe is frozen at six x1 arms: LOJM001 primary/reverse, LOFIX002
  primary/reverse, and EUUSD001 primary/reverse. Cost tiers are not extra arms.

## Frozen data and dependency contract

- Parquet:
  `02. AlphaFactory/data/fivepercent/TriangularConsensusLag/HYP-TRILAG-EURJPY-M1-002/design_m1_close.parquet`
- Parquet SHA256:
  `C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6`
- Manifest:
  `02. AlphaFactory/data/fivepercent/TriangularConsensusLag/HYP-TRILAG-EURJPY-M1-002/design_m1_manifest.json`
- Manifest SHA256:
  `4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8`
- Required USDJPY population: `1,860,286` unique increasing M1 timestamps;
  columns exactly `symbol,time_utc,close`; DESIGN years exactly 2016-2020.
- LOJM001 prior ledger SHA256:
  `6985108DEEDF59A503F5A96285F7D5CC8D8CE303FC03A599B5C3E414E0ECDC98`
- LOFIX002 prior ledger SHA256:
  `04270A2E9772A884322753701D55B6101109B1BA1E49ABFF59F89B882815A6DB`
- Reused generic helper evaluator SHA256:
  `FE05610F1502E6FDAA6C296C6F0285809AB1A2F12715312E60604B9A463F41C6`
- Canonical DSR module SHA256:
  `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`

All sources and evidence must remain on `D:`. Any hash mismatch, duplicate
timestamp, null/non-finite price, wrong symbol count, opened validation/holdout
counter, existing evidence root, or consumed attempt fails closed.

## Frozen clock, signal, and execution proxy

Timezone is `Europe/Berlin`, including DST.

For every complete local weekday:

1. Entry price is the completed `07:59` M1 Bid close, observable at `08:00`.
2. Exit price is the completed `14:14` M1 Bid close, observable at `14:15`.
3. Direction is always `LONG USDJPY` (`+1`).
4. `raw_move_pips = (exit_close - entry_close) / 0.01`.
5. Primary gross pips equal `raw_move_pips`; reverse control gross pips equal
   `-raw_move_pips` on the exact same dates and prices.
6. At most one trade per complete weekday. Missing either boundary skips that
   day; no nearest-bar fill or forward/backward fill is allowed.

No indicator, threshold, news rule, weekday/month/year veto, volatility filter,
stop, target, trailing rule, re-entry, or overnight carry is present. These
would be new hypotheses, not a rescue of this one.

## Frozen costs, statistics, and gates

- Round-trip cost proxies: x1=`1.50`, x1.5=`2.25`, x2=`3.00` pips/trade.
- Primary net: `gross_pips - cost`; reverse net: `-gross_pips - cost`.
- Cost `0` is never interpreted as verified zero cost.
- Significance: one-sided random-sign permutation test of the primary gross
  mean, `10,000` permutations, seed `20260729`. The observed sign is fixed
  before outcomes; each null sample independently flips every daily raw move.
- DSR: canonical module above, six declared x1 arms; any invalid radicand maps
  to `0`, never omission.

Structural gates, all required:

1. At least `1,000` complete weekday trades.
2. Eligible weekday coverage at least `95%` between first and last trade.
3. Cadence between `2.0` and `5.0` trades per elapsed calendar week.
4. Largest local-year share no more than `25%`.
5. Every trade has direction `LONG` and both exact frozen boundary slots.

Economic survivor gates, all on the same population:

1. Primary PF x1 strictly greater than `1.30`.
2. Primary PF x1.5 at least `1.25`.
3. Primary PF x2 at least `1.00`.
4. Primary x1 expectancy strictly positive.
5. At least four of five local years have positive x1 net pips.
6. One-sided random-sign permutation p-value at most `0.05`.
7. Six-arm primary DSR at least `0.95`.
8. Primary x1 PF and expectancy both exceed the matched reverse control.

If structural gates fail, the result is engineering/data invalid and makes no
economic claim. If structural gates pass but any economic gate fails, verdict
is `KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED`. Only 8/8 economic gates yields
`PASS_TRAIN_PROXY_AUTHORIZE_FRESH_MQL5_MODEL0_PACKET_ONLY`.

## One-shot evidence and prohibitions

Before execution, evaluator and tests must pass in both disarmed and armed
sentinel states. The registry row must hash-bind the plan, normalized evaluator,
test, parquet, manifest, both prior ledgers, helper evaluator, and DSR module.
The authorized registry row SHA is then inserted into the evaluator sentinel.

The one-shot evidence root is:

`03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUUSD-USDJPY-M1-001/EUUSD001-TRAIN-ECON-001/`

It must be absent before execution and created with exclusive writes. Evidence
must include an attempt-start marker, complete trade ledger, and terminal JSON
with hashes, metrics, gate booleans, verdict, and zero forbidden counters.

Forbidden under this ID: changing `08:00`/`14:15`, using London instead of
Frankfurt time, flipping direction, selecting days or regimes, reducing costs,
adding an indicator or stop/target, accessing 2021+, optimization, MQL5/MT5,
Model 0/4, promotion, paper trading, or live trading.
