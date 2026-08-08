# HYP-RSF-USDJPY-M15-TB-EVENT-ACCEPTANCE-018 - frozen preregistration

Frozen before structural-event counting or future-path calculation.

## Structural event clock

This is the final price-derived event-clock test for the five-indicator fusion
frontier on USDJPY. TB SMC defines structure and direction; AIRD/VRC provide
regime context, MBB provides setup/location state and QQE provides timing.

Long event flags are rising edges of `tb_structure_up`,
`tb_displacement_up`, or `tb_sweep_low`. Short event flags are rising edges of
`tb_structure_down`, `tb_displacement_down`, or `tb_sweep_high`. Same-direction
rises on one bar collapse to one event. Opposing rises on one bar reject the
bar. No debounce, session, weekday, MBB prerequisite or QQE sign prerequisite
is allowed.

## Stage A - outcome-blind cadence

Use only event flags and timestamps from census SHA256
`1FFA026BF50C431C87EC9EC9CE5DD7D17ABB26DBDB179680B8E75C5421642D2A`.
Do not read future OHLC, returns, barriers, MFE/MAE or outcomes.

Pass requires pooled cadence >=2.0/week, every 2018-2022 year >=1.5/week,
maximum year share <=35%, long share 30-70%, and unique collapsed timestamps.
Failure closes without economics.

## Stage B - frozen acceptance protocol

If Stage A passes, evaluate exactly six cells on structural event timestamps:

- Logistic C=0.1 and shallow HGB classifier;
- target/stop ATR cells 0.75/1.00, 1.00/1.00, 1.25/1.00;
- direction fixed by TB event, entry next M15 open, horizon eight M15 bars;
- same-bar target+stop is a stop; timeout exits at bar-8 close;
- full AIRD/VRC/MBB/TB/QQE state, structural event-type flags and
  direction-conditioned features;
- dynamic observed-spread cost identical to 016/017;
- expanding-year tests 2019-2022 with eight-bar purge/embargo;
- train-only thresholds at 2.5/3.5/4.5 non-overlapping trades/week.

All structure, displacement and sweep types remain included. No direction,
year, hour, weekday or indicator family may be removed. Survival gates are
identical to 017: cadence-valid >=3 folds, every valid fold positive/PF>1,
median and pooled PF>=1.20, max positive-gross year share<=40%, both adjacent
PF>1.05, all six cells counted.

## Terminal rule

No survivor closes the native-price five-indicator fusion frontier on USDJPY
M5/M15. Reopening would require materially new external point-in-time
information, not more indicator conjunctions or session mining. 2023+ and all
trading/promotion lanes remain sealed unless a discovery cell survives.
