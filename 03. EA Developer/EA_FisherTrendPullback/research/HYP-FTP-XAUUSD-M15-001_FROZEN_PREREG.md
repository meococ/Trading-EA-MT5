# HYP-FTP-XAUUSD-M15-001 — Frozen Preregistration

Status: `FROZEN_BEFORE_SOURCE_AND_OUTCOMES`

## Market thesis

The classic Fisher Transform makes local price extremes and turning points explicit. TradingView documents it as a reversal/change detector and notes that it is best paired with a trend indicator because the standalone oscillator can emit many unprofitable signals: https://www.tradingview.com/support/solutions/43000589141-fisher-transform/

This hypothesis tests pullback exhaustion inside an established M15 trend. It is not a revision or rescue of the killed Donchian/Chandelier breakout. The causal event is a Fisher extreme that turns back with the EMA200 regime, followed by a fixed structural/ATR stop, fixed 1.5R target and fixed 12-bar time exit.

## Frozen identity and data split

- Hypothesis: `HYP-FTP-XAUUSD-M15-001`
- EA: `EA_FisherTrendPullback`
- Symbol/timeframe: native FivePercent `XAUUSD` / `M15`
- TRAIN: `[2010-01-04 00:00, 2018-01-01 00:00)`
- Validation: `[2018-01-01, 2021-01-01)` sealed until TRAIN passes
- Holdout: `[2021-01-01, 2023-01-01)` sealed until all earlier gates pass
- Tester: AlphaFactory Model 0, current-spread semantics, deposit USD 100,000, leverage 1:100, execution mode 0, zero fixed delay
- One untuned TRAIN baseline only. No same-ID retry after a report/outcome exists.

## Exact closed-bar indicator

At each new M15 open, update the indicator using only the newly completed M15 bar `t`.

1. Price input: `P_t = (high_t + low_t) / 2`.
2. Lookback: `N=10`, inclusive bars `t-9..t`.
3. `raw_t = 2 * ((P_t - LL10_t) / (HH10_t - LL10_t) - 0.5)` when the range is positive, otherwise zero.
4. `value_t = clamp(0.33 * raw_t + 0.67 * value_(t-1), -0.999, +0.999)`.
5. `fish_t = 0.5 * ln((1 + value_t) / (1 - value_t)) + 0.5 * fish_(t-1)`.
6. Trigger line at `t` is exactly `fish_(t-1)`.

Initialization is deterministic: on `OnInit`, require at least 500 valid completed native M15 bars before the current open, process them oldest-to-newest with `value=0` and `fish=0`, then continue statefully one completed bar at a time. Gaps do not create synthetic bars and do not reset state.

Trend inputs are native closed-bar MT5 indicators:

- `EMA200_t` at shift 1 and `EMA200_(t-8)` at shift 9.
- `ATR14_t` at shift 1.

## Exact signal

LONG on completed bar `t` only when all are true:

- `fish_(t-1) <= -1.50`;
- `fish_t > fish_(t-1)` (strict upward trigger cross/turn);
- `close_t > EMA200_t`;
- `EMA200_t > EMA200_(t-8)`.

SHORT is exact inverse:

- `fish_(t-1) >= +1.50`;
- `fish_t < fish_(t-1)`;
- `close_t < EMA200_t`;
- `EMA200_t < EMA200_(t-8)`.

The decision is made at the completed-bar boundary and sent at the first tick of the new M15 bar. Consume at most one accepted entry per broker-server calendar date. No hour/session/weekday/news/direction filter is permitted.

## Exact lifecycle and risk

- One owned position/order maximum; no pyramiding.
- Market FOK only; only full `TRADE_RETCODE_DONE` is accepted.
- Planned entry is current executable Ask for LONG and Bid for SHORT.
- LONG stop: `min(signal_low - 0.25*ATR14_t, entry - 1.25*ATR14_t)`.
- SHORT stop: `max(signal_high + 0.25*ATR14_t, entry + 1.25*ATR14_t)`.
- Stop is rounded outward to symbol tick size and must pass wrong-side/stops/freeze geometry.
- TP is exactly 1.50R from the normalized stop distance, rounded outward.
- No trailing and no break-even.
- Time exit at the first new M15 bar after 12 completed holding bars.
- Friday/server-time 20:00 flatten, weekend block/flatten, and design-end flatten.
- Risk 0.25% of equity via `OrderCalcProfit`; volume rounds down to broker step and must pass margin.
- Daily loss lock 3.5% and peak-equity drawdown lock 8.0%.

## TRAIN acceptance and terminal rules

The baseline must satisfy all:

- PF strictly greater than 1.30;
- expectancy strictly greater than zero;
- 2.0–5.0 closed positions per exact elapsed calendar week;
- maximum equity drawdown no greater than 8.0%;
- at least 30% LONG and 30% SHORT;
- no single calendar year above 30% of trades and no persistently negative year;
- compile `0 errors / 0 warnings`, non-repaint PASS, no runtime fatal, no orphan order/position.

Any headline PF/expectancy/cadence failure kills this exact mapping. Do not rescue it by changing threshold, lookback, EMA, stop/target/time exit, direction, session, weekday or risk after the readout. Cost stress, validation, holdout, optimization, WFA, Monte Carlo, paper and live remain closed unless the untuned TRAIN baseline passes.

The current XAU cost proxy does not cover the TRAIN window and has no observed fill slippage. Therefore a passing tester baseline would only authorize a separate verified-cost acquisition/rebuild; it would not itself establish `economic-valid` or promotion readiness.
