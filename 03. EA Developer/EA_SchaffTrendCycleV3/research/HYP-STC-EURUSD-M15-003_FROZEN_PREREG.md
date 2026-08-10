# HYP-STC-EURUSD-M15-003 — frozen untuned baseline

Status: `FROZEN_PRE_BASELINE`

## Engineering lineage

Parent HYP002 is terminally killed as
`KILL_ENGINEERING_PRELOAD_ENDPOINT_OFF_BY_ONE_BAR_NO_ECONOMIC_VERDICT`.
Its sole MT5 run stopped in `OnInit` with zero bars, signals, orders and
returns. Failure packet SHA256:
`F96016C633669BF1699336F1E47BF332D1A6602A6A95B84D567AC44D6129FDA6`.

HYP003 changes only fresh identity/magic/log prefixes and the exact
tester-visible closed preload boundary. It does not change the recurrence,
signal, execution, risk, cost, DESIGN or sealed evaluation windows.

Read-only same-terminal/profile proof:
`HYP-STC-EURUSD-M15-003_PRELOAD_ORIGIN_PROOF.json`. The Strategy Tester closed
subset contains exactly `24,775` strictly increasing M15 bars from
`2015.01.02 09:00` through `2015.12.31 19:45`; timestamp-sequence SHA256
`C9006D5C5E0ED8BE72C63BA4F1C0FB1B12AD9DF518F0D7BE68639305EAD114FF`.
Any wrong endpoint, count, duplicate, non-increasing time, missing or partial
`CopyRates` preload fails closed. No wait/retry or rolling-window reseed.

## Market thesis and formula

Classic Schaff Trend Cycle combines the 23/50 EMA difference with two
10-bar stochastic normalizations and 3/3 EMA smoothing. A cycle reset is
traded only in the direction of the underlying EMA trend, seeking earlier
continuation entry after a pullback.

- Doug Schaff formula provenance:
  `https://forex-indicators.net/files/indicators/Schaff_Trend_Cycle.pdf`.
- TradingView research reference for classic `23/50/10/3/3`, 25/75 mapping:
  `https://www.tradingview.com/script/eZwlb7PV/`.

TradingView is not parity or acceptance evidence. The direct MQL5 recurrence
and MT5 Strategy Tester are authoritative.

## Frozen signal

- Completed EURUSD M15 close only.
- EMA fast/slow `23/50`; both stochastic windows `10`; EMA smoothing `3/3`.
- Zero-range stochastic carries the prior normalized value, seeded at `50`.
- LONG: prior STC `<=25`, current STC `>25`, current EMA23-EMA50 `>0`.
- SHORT: prior STC `>=75`, current STC `<75`, current EMA23-EMA50 `<0`.
- One first eligible signal per broker-server date.
- No ADX, HTF, pattern, session, news, volume or direction filter.
- Decision is the completed bar; availability is the exact next M15 open.
  A non-900-second gap consumes no signal and creates no order.

## Frozen execution and risk

- One owned position, no pending-order strategy or pyramiding.
- Risk `0.25%` of equity; volume rounded downward to broker step.
- SL `1.50 * ATR14`; TP `1.50R` from normalized request geometry.
- Exit only by SL, TP, `16` completed M15 bars, Friday/weekend flatten or
  DESIGN end. No trailing, break-even, partial or opposite-signal exit.
- Daily loss lock `3.5%`; peak-equity drawdown lock `8%`.
- No new Friday entry from `20:00` server time; flatten then/weekend.
- Deposit `100000`, leverage `1:100`, current spread, report commission/swap,
  Model `0`, execution mode `0`, fixed delay `0`.

## Frozen chronology

- DESIGN: `2016.01.04-2021.01.01`.
- Validation: `2021.01.01-2022.01.01`, unopened.
- Holdout: `2022.01.01-2023.01.01`, unopened.
- Exactly one untuned DESIGN baseline. No optimization, sweep, filter or
  same-ID economic retry.

## Gates and falsification

- Engineering: compile 0E/0W, focused tests, non-repaint PASS, complete report,
  HQ `>97%`, exact source/EX5/run identity.
- DESIGN: PF `>1.30` after report costs, cadence `2-5/week`, equity DD `<=8%`,
  each direction `>=30%`, no calendar year `>35%` of trades.
- Only a DESIGN pass may open x1.5/x2 cost stress: x1.5 PF `>=1.25`, x2 PF `>=1.00`.
- Validation, holdout, WFA, sensitivity, Monte Carlo and execution forensics
  stay sealed until prior gates pass.
- If implementation-correct PF `<1.0`, pre-cost expectancy is negative, or
  weakness is broad across directions/years, kill this exact mechanism without
  post-hoc ADX, session, threshold, R:R, ATR or holding-period rescue.
