# HYP-RSF-USDJPY-M15-MBB-EVENT-ACCEPTANCE-017 - frozen preregistration

Frozen before event counting or any outcome calculation.

## Mechanism

The all-bar fixed-return and barrier-acceptance models are terminal. This ID
changes the decision population: MBB acts as the setup clock; AIRD/VRC are
regime routers; TB SMC contributes structural geometry; QQE contributes timing.
No indicator is an equal vote and no model scans ordinary bars.

An event occurs on a rising edge of any individual MBB S1, S2 or S3 direction
flag. Multiple same-direction rising edges on one bar collapse to one event.
If long and short rising edges occur together, the bar is rejected. Direction
is fixed by MBB; the acceptance model cannot flip it. No additional debounce,
session, weekday or price-outcome rule is allowed.

## Stage A - outcome-blind cadence gate

Using the bound native-M15 census SHA256
`1FFA026BF50C431C87EC9EC9CE5DD7D17ABB26DBDB179680B8E75C5421642D2A`,
count only event timestamps and types. Do not read future OHLC, barrier labels,
returns, MFE/MAE or trade outcomes.

Stage A passes only if:

1. pooled raw event cadence >= 2.0 per elapsed calendar week;
2. every 2018-2022 calendar year has >= 1.5 events/week;
3. no year supplies more than 35% of events;
4. long share is between 30% and 70%;
5. timestamps are unique after same-direction collapse and conflict rejection.

Failure closes the ID without economics. Passing authorizes exactly Stage B.

## Stage B - fixed event acceptance discovery

At an event, theoretical entry is next M15 open and TB ATR freezes geometry.
The six cells are identical in complexity to 016 so event selection is the
only new mechanism:

- target/stop ATR: 0.75/1.00, 1.00/1.00, 1.25/1.00;
- maximum path: eight M15 bars;
- same-bar target+stop: stop first; otherwise target/stop first passage, then
  timeout at bar-8 close;
- models: Logistic Regression C=0.1 and shallow HGB classifier;
- features: all AIRD, VRC, MBB, TB SMC and QQE state at the event, plus event
  type and direction-conditioned alignment features;
- cost: observed spread at point 0.001 times
  `1.5 + 0.15 * (1 + VRC volatility percentile / 100)`;
- expanding-year tests 2019-2022, training only on prior years, eight-bar
  purge/embargo;
- train-only threshold targets 2.5/3.5/4.5 non-overlapping trades/week.

If the raw event population cannot sustain 2.5/week after non-overlap, no
threshold may synthesize missing cadence. No signal type, family, direction,
year, hour or weekday may be removed after outcomes.

Stage-B gates are: at least three folds at 2-5 trades/week; every cadence-valid
fold net-positive and PF>1; median and pooled PF>=1.20; maximum positive-gross
year share<=40%; both adjacent threshold PF>1.05; all six cells counted.

## Sealed data

No 2023+ access unless one cell survives and is frozen. EA implementation,
optimization, paper, live and promotion are not authorized by discovery.
