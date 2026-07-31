# TRAIN ECONOMIC PROBE PLAN — HYP-EURFXIMM-EURUSD-M1-003

Frozen on `2026-07-30` after HYP002 stopped before trade construction/economics.
HYP002 opened only one target-availability fact: every frozen TRAIN source date,
including `2017-09-28`, has both new immediate boundaries. It computed no trade,
cost, PF, expectancy, DSR, annual metric or chart. HYP003 is the exact data-
contract successor; HYP002 terminal SHA256:
`A9615BB67E2FED56365C5002E3A40CF038F4FC83C857F55567F1DE9B8ABA1646`.

Only two structural constants change:

- allowed missing target dates: `("2017-09-28",)` -> empty tuple;
- exact expected trades: `608` -> `609`.

Everything else from the HYP001/HYP002 frozen mechanism is unchanged: TRAIN
2016-2020 only; validation 2021-2024 and holdout 2025-current sealed; exact 630
strict-lag high-pressure dates; HYP013 final-15-second CME 6E `flow_signed` by
`ts_recv`; primary `sign(flow_signed)` continuation; signal ends 14:15:00
Europe/Berlin; enter completed 14:15 close observable 14:16 and exit completed
14:20 close observable 14:21; exact flow-reversal and price-pressure
continuation/reversal controls; 1.50/2.25/3.00-pip costs; no other filter,
stop/target, sizing or intrabar path; exactly 20 DSR arms and 10,000 sign flips
with seed 20260730.

All structural gates are required: 630 selected dates, zero missing targets,
exactly 609 trades, 2-5 trades/elapsed week, >=25% each direction and exact
frozen rule. All economic gates are required: PF x1>=1.30, x1.5>=1.25,
x2>=1.00; x1 expectancy>0; >=4/5 positive years; every leave-one-year-out
PF>1; one-sided p<=0.05; DSR>=0.95; max positive-year contribution<=35%.

One attempt only: `EURFXIMM003-TRAIN-ECON-001`. PASS opens only the right to
preregister a sequential validation successor. Any economic failure is
`KILL_TRAIN_IMMEDIATE_FLOW_CONTINUATION_HOLDOUT_REMAINS_SEALED`. No horizon
grid, threshold/clock/cost/calendar/regime rescue, validation/holdout, MQL5,
MT5, Model 0, optimization, promotion, paper or live authority.
