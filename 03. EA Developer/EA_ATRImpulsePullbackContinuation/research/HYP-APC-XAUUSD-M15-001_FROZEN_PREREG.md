# HYP-APC-XAUUSD-M15-001 — frozen untuned Model-0 baseline

Status: `FROZEN_PRE_OUTCOME_BUILD`

## Market thesis

The mechanism tests continuation after a discrete volatility impulse, a shallow one-bar pullback that preserves at least half of the impulse body, and a completed-bar release in the direction of an established EMA/ADX trend. ATR normalizes the impulse, pullback, release extension and protective stop; EMA50 slope plus ADX14/DI polarity prevents treating every large candle as trend continuation.

This is one atomic three-bar price-structure event. It is materially distinct from the parked MZMS Donchian fresh-breakout mode and its multi-bar pivot-reclaim mode: APC uses no Donchian channel, no confirmed pivot, no EMA20/EMA100 crossover and no session/cooldown rescue. It is not informed by any APC trade, return, PF, direction, stop or target outcome.

Indicator formula provenance is MT5-native `iATR`, `iMA` and `iADX`. No TradingView execution/parity evidence is used.

## Identity and split

- Hypothesis: `HYP-APC-XAUUSD-M15-001`
- EA: `EA_ATRImpulsePullbackContinuation`
- Variant: `ATR14_EMA50_ADX14_IMPULSE_PULLBACK_RELEASE_V1`
- Symbol/timeframe: XAUUSD M15
- Frozen train: `[2010-01-04 00:00, 2018-01-01 00:00)` broker-server bar time
- Validation: `[2018-01-01, 2021-01-01)` sealed
- Final holdout: `[2021-01-01, 2023-01-01)` sealed
- MT5 Strategy Tester Model 0, execution mode 0, fixed delay 0, current spread, deposit 100000 USD, leverage 1:100.
- One untuned train baseline only. No optimization or same-ID retry.

## Frozen signal

All price and indicator inputs are completed native M15 bars. For release bar `t`:

- ATR14 is read at `t`, `t-1`, `t-2`.
- EMA50 is read at `t` and `t-8`.
- ADX14 and DI polarity are read at `t`; ADX rise compares `ADX[t] > ADX[t-3]`.
- LONG trend: `close[t] > EMA50[t]`, `EMA50[t] > EMA50[t-8]`, `ADX[t] >= 18`, `ADX[t] > ADX[t-3]`, `+DI[t] > -DI[t]`. SHORT is the exact inverse except ADX remains rising/at least 18.
- LONG impulse `t-2`: true range at least `1.35*ATR[t-2]`, body at least `0.55*TR`, bullish, and close location `(close-low)/TR >= 0.70`. SHORT is symmetric.
- LONG pullback `t-1`: `low[t-1]` is at or above the midpoint of the impulse body, `close[t-1] >= open[t-2]`, and `TR[t-1] <= 0.85*ATR[t-1]`. SHORT is symmetric.
- LONG release `t`: `close[t] > high[t-1]` but `close[t] <= high[t-2] + 0.35*ATR[t]`. SHORT is symmetric.
- A simultaneous LONG/SHORT result is rejected.
- Decision/entry availability is the next M15 open exactly 900 seconds later. A missing exact next bar consumes the event.
- At most one qualifying signal is consumed per broker-server calendar date. No session, weekday, news, spread, direction, extra volatility regime or outcome-derived filter.

## Frozen stop, target and lifecycle

- LONG structural stop: `min(low[t-2], low[t-1]) - 0.20*ATR[t]`; SHORT is `max(high[t-2], high[t-1]) + 0.20*ATR[t]`.
- Market FOK entry on the first tick of the exact next M15 bar. The symbol must advertise FOK.
- Stop is rounded outward to tick size. Wrong-side, nonfinite, stops-level or margin-invalid geometry skips the consumed signal.
- Target is exactly `1.45R` from the requested market entry after stop normalization and is rounded inward to tick size.
- No trailing stop and no break-even.
- Close at broker SL/TP or at the first M15 open after ten completed M15 bars from entry. Time exit is reconstructed with native M15 `iBarShift` from the broker position time.
- One owned position and zero owned pending orders before entry; no pyramiding and no reversal-on-signal.
- Friday 20:00 or later in broker-server time blocks entry and flattens; Saturday/Sunday exposure and design-end exposure are flattened.

## Frozen risk

- 0.25% current-equity risk to requested entry/initial stop, sized downward via `OrderCalcProfit` and broker volume step.
- Required margin must not exceed current free margin.
- Maximum one accepted entry per broker-server day.
- Daily equity-loss latch 3.5%; peak-equity drawdown latch 8.0%; latches block new entries.
- Deviation 20 points.

Restart-persistent risk anchors and transaction-level partial-fill recovery are outside this first economic baseline and are mandatory before any promotion/live stage.

## Acceptance and stopping rule

Before baseline: source-to-spec tests, fresh compile `0 errors / 0 warnings`, non-repaint audit and independent review must pass.

Train gate:

- report PF > 1.30 after native spread/commission/swap;
- expectancy > 0;
- 2–5 closed positions per elapsed calendar week;
- equity drawdown <= 8%;
- LONG and SHORT each at least 30% of trades;
- no calendar year above 35% of trades;
- complete report/deal/journal identity and no runtime fatal.

If any headline gate fails, exact APC001 is killed without session/direction/threshold/period/stop/target/hold/risk rescue. Cost stress, optimization, validation and holdout remain closed. If all pass, require verified costs, PF >=1.25 at x1.5 cost and PF >=1.00 at x2 cost before validation.

