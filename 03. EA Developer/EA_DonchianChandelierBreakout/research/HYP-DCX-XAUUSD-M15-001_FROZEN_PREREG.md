# HYP-DCX-XAUUSD-M15-001 — frozen untuned Model-0 baseline

Status: `FROZEN_PRE_OUTCOME_BUILD`

## Market thesis

Donchian Channels identify breakouts of a recent price range. TradingView documents the standard 20-period channel as the highest high and lowest low of the lookback and describes a channel break as potential trend confirmation. Chandelier Exit is a volatility-based trend exit using a recent extreme minus/plus an ATR multiple. The combined thesis is one coherent trend-following mechanism: enter the first confirmed close outside the prior Donchian range and remain in the move until the completed-bar Chandelier stop tightens or is hit.

This object is materially distinct from prior Supertrend flips, squeeze-release, oscillator crosses and jump-cluster reversal. It is not informed by any DCX trade, return, PF, session, direction, stop or target outcome.

References:

- https://www.tradingview.com/support/solutions/43000502253-donchian-channels-dc/
- https://www.tradingview.com/support/solutions/43000773013-chandelier-exit/
- https://www.mql5.com/en/docs/indicators/iatr

## Identity and split

- Hypothesis: `HYP-DCX-XAUUSD-M15-001`
- EA: `EA_DonchianChandelierBreakout`
- Symbol/timeframe: XAUUSD M15
- Frozen train: `[2010-01-04 00:00, 2018-01-01 00:00)` broker-server bar time
- Validation: `[2018-01-01, 2021-01-01)` sealed
- Final holdout: `[2021-01-01, 2023-01-01)` sealed
- MT5 Strategy Tester Model 0, execution mode 0, fixed delay 0, current spread, deposit 100000 USD, leverage 1:100.
- One untuned train baseline only. No optimization or same-ID retry.

## Frozen signal

Use completed native M15 bars only.

- Donchian length: 20.
- For release bar `t`, upper/lower are the highest high/lowest low of bars `t-20..t-1`; the release bar itself is excluded.
- LONG only when `close[t] > upper[t]` and `close[t-1] <= upper[t-1]`.
- SHORT only when `close[t] < lower[t]` and `close[t-1] >= lower[t-1]`.
- This transition rule emits only the first close outside a side of the channel.
- Decision/entry availability is the next M15 open exactly 900 seconds later. Missing/gap events are consumed.
- At most one consumed signal per broker-server calendar date. No session, weekday, news, spread, direction, trend-strength or volatility filter.

## Frozen stop and lifecycle

- ATR: native M15 Wilder ATR22 from the completed release bar.
- Chandelier length 22, multiplier 3.0.
- LONG stop: highest high of completed bars `t-21..t` minus `3*ATR22[t]`.
- SHORT stop: lowest low of the same bars plus `3*ATR22[t]`.
- Entry is a market FOK request at the first tick of the next exact M15 bar. The symbol must advertise FOK; otherwise initialization fails. Stop is rounded outward to tick size; wrong-side, nonfinite, stops-level or margin-invalid geometry skips the consumed signal.
- No profit target and no time exit. At each new M15 bar the stop is recomputed from completed bars and may only tighten. If market has already crossed the newly completed-bar Chandelier level, close immediately at market. If the level is not crossed but is too close for broker stops/freeze geometry, retain the old protective stop until a later tick/bar. Broker stop, Chandelier-cross close, Friday/end flatten, or a later risk-control flatten are the only exits.
- One owned position and zero owned pending orders before entry; no pyramiding or reversal-on-signal. Any ticket selection or owned-inventory property uncertainty fails closed, latches runtime failure and blocks new entries.
- Friday 20:00 or later in broker-server time blocks new entry and flattens. Saturday/Sunday exposure is flattened. Design-end exposure is flattened.

## Frozen risk

- 0.25% current-equity risk to requested entry/initial stop, sized downward by `OrderCalcProfit` and broker volume step.
- Required margin must not exceed current free margin.
- Maximum one accepted entry per broker-server day.
- Daily equity-loss latch 3.5%; account peak-equity drawdown latch 8.0%; latches block new entries.
- Deviation 20 points. No parameter optimization, alternate stop/exit, target, break-even or trailing multiplier.

Restart-persistent risk anchors, transaction-level partial-fill reconciliation, live deployment and promotion are explicitly outside this first economic baseline. They become mandatory engineering work only if the frozen baseline first passes economic gates.

## Acceptance and stopping rule

Before the baseline: source-to-spec tests, compile `0 errors / 0 warnings`, non-repaint audit and independent review must pass.

Economic gate on train:

- report PF > 1.30 after native spread/commission/swap;
- expectancy > 0;
- 2–5 closed positions per elapsed calendar week;
- equity drawdown <= 8%;
- both directions represented and no calendar year >35% of trades;
- complete report/deal/journal identity and no runtime fatal.

If any headline economic gate fails, exact HYP001 is killed without session/direction/period/ATR/multiplier/risk/exit rescue. Cost stress, optimization, WFA, validation and holdout remain closed. If all pass, build verified cost evidence and test x1.5/x2 before opening validation.
