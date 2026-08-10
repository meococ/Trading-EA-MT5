# HYP-KVO-EURUSD-M15-002 — Frozen untuned economic baseline

## Thesis and novelty

EURUSD M15 can express intraday continuation when price remains on the correct side of its long trend while Klinger Volume Force temporarily moves against that trend and then crosses its signal line before crossing zero. The signal is one standard volume–price oscillator state transition, not an indicator-voting ensemble.

The prior `HYP-KVO-EURUSD-H1-001` stopped before event analysis because its literal first-two-bars seed produced `CM=0`. It opened no outcomes. This fresh M15 hypothesis freezes a flat-safe initialization convention before any event, trade or outcome is read. TradingView is formula provenance only, never parity or acceptance: https://www.tradingview.com/support/solutions/43000589157-klinger-oscillator/ . FivePercent tick volume is treated only as unsigned broker activity, not centralized exchange volume or aggressor flow.

## Frozen identity and data

- Hypothesis: `HYP-KVO-EURUSD-M15-002`
- EA: `EA_KlingerPullback`
- Symbol/timeframe: native `EURUSD` / `M15`
- TRAIN: `[2010-01-04 00:00, 2018-01-01 00:00)`; Model 0; execution mode 0; fixed delay 0
- Validation: 2018–2022 sealed until the baseline passes; holdout 2023–2025 sealed until parameters and validation plan are frozen
- One baseline attempt, no optimization or parameter grid

## Frozen indicator calculation

For oldest-to-newest completed M15 bars:

- `S_t = High_t + Low_t + Close_t`
- `DM_t = High_t - Low_t`
- `T_t = +1` iff `S_t > S_(t-1)`; equality/decrease is `-1`
- Standard continuation: `CM_t = CM_(t-1) + DM_t` when `T_t == T_(t-1)`, otherwise `CM_t = DM_(t-1) + DM_t`
- `VF_t = tick_volume_t * 2 * (DM_t / CM_t - 1) * T_t * 100`; no absolute value
- `KO = EMA34(VF) - EMA55(VF)`; `Signal = EMA13(KO)`; long-trend reference is `EMA100(close)`

Flat-safe convention:

- Initialization begins at the first `t>=1` with `DM_(t-1)+DM_t>0`; earlier rows are warmup only.
- If a later standard CM update is exactly zero because consecutive bars are flat, that bar has `CM=0` and `VF=0`; recursion continues without deleting, interpolating or synthesizing a bar.
- Nonfinite/inverted OHLC or negative/noninteger tick volume is fatal. Valid `H=L=C` and zero tick volume are accepted.
- EMA34/55 are SMA-seeded from the first 34/55 defined VF values; Signal EMA13 is SMA-seeded from the first 13 finite KO values; EMA100 is SMA-seeded from the first 100 valid closes. All later recurrences use `alpha=2/(N+1)`.
- OnInit reconstructs state once from every physically available completed M15 prehistory bar, oldest to newest. It requires synchronized series metadata, `CopyRates` count exactly equal to `Bars-1`, the first copied timestamp equal to `SERIES_FIRSTDATE`, the last copied timestamp equal to native shift 1, and strictly increasing timestamps. Partial copies or shifted origins fail initialization. The journal records requested/copied/first/last/current for run reconciliation. On each new M15 open it consumes exactly the newly completed bar. No current-bar OHLC enters the signal.

## Frozen event FSM

States are `IDLE`, `LONG_ARMED`, `SHORT_ARMED`. Existing state is evaluated before a new arm; an IDLE bar can arm but cannot emit on that bar.

- LONG arms strictly when `KO<0 && Close>EMA100`.
- SHORT arms strictly when `KO>0 && Close<EMA100`.
- LONG emits when prior `KO<=Signal`, current `KO>Signal`, current `KO<=0`, and `Close>EMA100`.
- SHORT emits when prior `KO>=Signal`, current `KO<Signal`, current `KO>=0`, and `Close<EMA100`.
- Current equality is not a cross; prior equality may cross. KO zero cannot arm but can complete an armed event.
- LONG remains armed only while `KO<=0 && Close>EMA100`; SHORT remains armed only while `KO>=0 && Close<EMA100`.
- Trigger, invalidation or opposite context resets the state; no same-bar rearm after a reset or event.
- Decision is the completed signal bar; entry is the first tick of the exact next native M15 bar. A non-`+900s` next open consumes the raw signal and does not queue it.
- At most one entry is accepted per native broker/server calendar date. There is no session, weekday, direction, news, volatility or spread filter.

## Frozen execution, risk and exits

- Market entry on the exact next M15 open; one owned position, no pyramiding or pending orders.
- ATR14 is read from the completed signal bar.
- LONG structural stop: minimum low of signal bar and two prior completed bars minus `0.15*ATR14`; SHORT inverse.
- Stop is rounded outward to tick size. Invalid/wrong-side/broker-stop geometry skips the event once.
- TP is fixed `1.50R` from actual requested entry to normalized stop.
- Risk is `0.25%` of current equity using `OrderCalcProfit`, rounded down to broker volume step; insufficient minimum-lot or margin geometry skips once.
- Exit only by broker SL/TP, `16` completed M15 bars, Friday `20:00` server-time flatten, weekend, or design-end flatten. No trailing, breakeven, partial exit or signal reversal exit.
- Daily loss lock `3.5%`, account peak-to-equity lock `8%`, max one accepted entry/day, deviation `20` points.

## Baseline gates

Engineering gates precede economics: compile `0 errors / 0 warnings`, non-repaint PASS, D0 series proof, History Quality `>97%`, `runtime_failed=false`, exact summary/report reconciliation, no orphan owned position/order, and deterministic source counts.

If engineering passes, the sole TRAIN baseline must meet all of:

- PF `>1.30` after report costs
- executed cadence `2–5` trades per elapsed calendar week
- positive expectancy and net profit
- both directions at least `30%` of trades and no calendar year above `30%`
- equity drawdown `<=8%`

A material miss kills the exact mechanism. No session/direction filter, EMA/KVO period change, daily-cap change, threshold, SL/TP, time-stop, symbol or timeframe rescue is allowed after reading the baseline. Only a passing baseline may open x1.5/x2 cost stress, validation, WFA/CPCV/DSR/Monte Carlo and holdout.
