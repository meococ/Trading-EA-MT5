# TRAIN ECONOMIC PROBE PLAN - HYP-EURFXREV-EURUSD-M1-001

Frozen at `2026-07-29T18:04:24.909Z`, before reading any EURUSD return after
the Europe/Berlin `14:15` ECB-fix boundary. Any signal, lookback, threshold,
clock, cost, exit or gate change requires a new hypothesis ID.

## Identity and decision use

- Hypothesis: `HYP-EURFXREV-EURUSD-M1-001`
- Research-only package: `EA_EuropeOpenUSDDemand`
- Symbol/timeframe: `EURUSD`, completed Bid `M1` close proxy
- DESIGN/TRAIN: `2016-01-01` through `2020-12-31`
- Validation `2021-2024`: sealed; research holdout `2025+`: forbidden
- Attempt: `EURFXREV001-TRAIN-ECON-001`, exactly once
- Owner objective: cost-adjusted PF above `1.30`, not gross seasonality.

Only an 8/8 economic pass may authorize a fresh MQL5/Model-0 packet. It does
not authorize validation, holdout, optimization, promotion, paper or live.

## Fresh mechanism and contamination boundary

Krohn, Mueller and Whelan document USD appreciation before benchmark fixes and
depreciation after them. Their dealer-inventory explanation is that banks hedge
client order imbalances before a fix and trade away warehouse inventory after
the fix. Primary source: *Foreign Exchange Fixings and Returns Around the
Clock*, Journal of Finance, DOI `10.1111/jofi.13306`; open paper:
`https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf`.

The already-open pre-fix EURUSD ledger is used only as a contemporaneously
observable pressure signal. No post-14:15 target return has been read. The new
target is the post-fix interval, so this is not a VIX, weekday or clock filter
on the killed pre-fix trade. The signal selects large inventory-pressure days
using a strict-lag trailing median fixed before target access.

## Frozen data and rule

- Parquet SHA256:
  `C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6`
- Manifest SHA256:
  `4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8`
- Required EURUSD population: `1,859,939` unique increasing rows.
- Timezone: `Europe/Berlin`, including DST.
- Pressure input: exact completed `07:59` and `14:14` closes.
- Entry: completed `14:14` close, observable at `14:15`.
- Exit: completed `15:59` close, observable at `16:00`.
- Pressure: `(close_14:14 - close_07:59) / 0.0001` pips.
- Threshold: median absolute pressure of the preceding `60` complete weekdays,
  excluding the current day; require at least `40` prior complete values.
- Trade only if current absolute pressure is greater than or equal to that
  threshold and pressure is non-zero.
- Direction is the exact reversal of pressure: pressure below zero means LONG
  EURUSD; pressure above zero means SHORT EURUSD.
- One trade per eligible complete weekday; missing any boundary skips the day;
  no nearest/fill-forward bar.

No VIX, weekday/month/year/news veto, extra indicator, stop, target, trailing,
re-entry or carry is present.

## Costs, trials and gates

- Round-trip costs: x1=`1.50`, x1.5=`2.25`, x2=`3.00` pips.
- Matched control: trade in the same direction as pre-fix pressure.
- One-sided random-sign test: `10,000`, seed `20260729`.
- DSR: twelve x1 arms - five prior primary/reverse pairs plus current primary/
  reverse. Cost tiers are not extra arms.

Structural gates, all required:

1. at least `500` selected trades;
2. cadence `2.0` to `3.5` per elapsed calendar week;
3. largest year share no more than `30%`;
4. at least `25%` LONG and at least `25%` SHORT;
5. every trade uses exact `14:14` entry, `15:59` exit, strict-lag median and
   pressure-reversal direction.

Economic gates, all required:

1. primary PF x1 `>1.30`;
2. primary PF x1.5 `>=1.25`;
3. primary PF x2 `>=1.00`;
4. primary x1 expectancy `>0`;
5. at least four of five years positive at x1;
6. one-sided random-sign p-value `<=0.05`;
7. twelve-arm DSR `>=0.95`;
8. primary x1 PF and expectancy both exceed the matched continuation control.

Structural pass with any economic failure is
`KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED`. Only 8/8 is
`PASS_TRAIN_PROXY_AUTHORIZE_FRESH_MQL5_MODEL0_PACKET_ONLY`.

## One-shot evidence and prohibitions

Plan, normalized evaluator, test, parquet/manifest, five prior ledgers, parent
evaluator and canonical DSR must be hash-bound in the latest authorized registry
row before the evaluator sentinel is armed. Evidence root must be absent:

`03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EURFXREV-EURUSD-M1-001/EURFXREV001-TRAIN-ECON-001/`

Forbidden: reading target outcomes before arming; threshold/lookback/clock/
direction/cost changes; post-outcome calendar or magnitude buckets; stops/
targets; same-ID rerun; validation/holdout; MQL5/MT5; optimization; promotion;
paper or live trading.
