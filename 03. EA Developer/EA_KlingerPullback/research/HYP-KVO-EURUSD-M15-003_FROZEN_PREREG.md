# HYP-KVO-EURUSD-M15-003 — Frozen untuned economic baseline

## Thesis and revision boundary

EURUSD M15 can express intraday continuation when price remains on the correct side of EMA100 while Klinger Volume Force temporarily moves against that trend and then crosses its signal line before crossing zero. The mechanism, KVO/EMA periods, signal FSM, stop, target, holding time, daily cap, risk, data window and economic gates are unchanged from HYP-KVO-EURUSD-M15-002.

HYP-KVO-EURUSD-M15-002 opened MT5 but was engineering-invalid before economic acceptance. One `TRADE_RETCODE_MARKET_CLOSED` entry rejection set `runtime_failed=true` and blocked all later signals. AlphaFactory also failed during cleanup after `/ShutdownTerminal` had already written the report and exited. No PF, expectancy or outcome verdict was admitted.

This fresh child changes only rejected-entry reconciliation. `OrderSend=false` is always fatal. A non-DONE FOK response is a consumed, nonfatal event only for exact `TRADE_RETCODE_MARKET_CLOSED` with zero result order/deal tickets, followed by successful fresh owned-position and owned-order scans whose counts are both zero. Timeout, unknown retcode, any ticket, uncertain inventory, partial exposure or surviving order is fatal. The generic AlphaFactory post-report cleanup is independently fixed to release a stale PID claim without stopping a replacement process. No observed return or trade subset informed this revision.

TradingView is formula provenance only, never parity or acceptance: https://www.tradingview.com/support/solutions/43000589157/klinger-oscillator/ . FivePercent tick volume is unsigned broker activity, not centralized exchange volume or aggressor flow.

## Frozen identity and data

- Hypothesis: `HYP-KVO-EURUSD-M15-003`
- EA/package: `EA_KlingerPullback`
- Variant: `KVO34_55_13_EMA100_PULLBACK_REENTRY_REJECTSAFE`
- Magic: `5604003`
- Symbol/timeframe: native `EURUSD` / `M15`
- TRAIN: `[2010-01-04 00:00, 2018-01-01 00:00)`; Model 0; execution mode 0; fixed delay 0
- Validation: 2018–2022 sealed; holdout: 2023–2025 sealed
- One baseline attempt, no optimization or parameter grid

Frozen implementation evidence before compile:

- MQL source SHA256: `5D7E989E674C7D85E008FC58A44FB9335AB15C5B7A920EBBED60EF7FD0D66F73`
- EA contract SHA256: `2FBD4714B1C502063C55FEC26AB53B2269F58D7D3AA0036201F41AF1D949DE74`
- Source-contract test SHA256: `524A90B7DEE3E72235F3D737F81B1924EDEE547E5C72B8B9FC92C95DCE9CAB28`
- AlphaFactory runner SHA256: `B5AFD1B4478532A284B4B2C53B2AB7E200FC3C2D0D1A7D27EB9D4BE41DA8E226`
- Terminal cleanup regression test SHA256: `31BF3C04049598531E5E4A0DEE88102DF9902F47180BD4F8364A259CBCAFF780`
- Parent engineering failure SHA256: `9A2F91FE9940897CA106E80422F0D3576D9E37333F2FDF42FC423D2A573DB6EC`

## Frozen indicator calculation

For oldest-to-newest completed M15 bars:

- `S_t = High_t + Low_t + Close_t`; `DM_t = High_t - Low_t`.
- `T_t = +1` iff `S_t > S_(t-1)`; equality/decrease is `-1`.
- `CM_t = CM_(t-1) + DM_t` when the trend is unchanged, otherwise `DM_(t-1) + DM_t`.
- `VF_t = tick_volume_t * 2 * (DM_t / CM_t - 1) * T_t * 100`; no absolute value.
- `KO = EMA34(VF) - EMA55(VF)`; signal `EMA13(KO)`; trend `EMA100(close)`.
- Initialization begins at the first adjacent pair with positive total range. A later exact `CM=0` flat bar has `VF=0`. Bars are not deleted, interpolated or synthesized.
- EMA34/55 and EMA13/EMA100 use SMA seeds followed by `alpha=2/(N+1)` recursion.
- OnInit reconstructs all physically available completed M15 history oldest-to-newest and requires synchronized series, full `Bars-1` copy, exact `SERIES_FIRSTDATE`, exact shift-1 last bar and strictly increasing timestamps.
- Signals use completed bars only. ATR14 uses literal shift 1. The decision bar enters only at the exact next native M15 open (`+900s`).

## Frozen event FSM

- LONG arms strictly at `KO<0 && Close>EMA100`; SHORT at `KO>0 && Close<EMA100`.
- LONG emits on prior `KO<=Signal`, current `KO>Signal`, current `KO<=0`, `Close>EMA100`.
- SHORT is the exact inverse with prior equality allowed and current crossing strict.
- Existing state is evaluated before new arming. Trigger, invalidation or opposite context resets state; no same-bar rearm.
- A gap consumes the raw event. No session, weekday, direction, news, volatility or spread filter.
- At most one accepted entry per broker/server calendar date.

## Frozen execution, risk and exits

- FOK market entry; one owned position; no pyramiding or pending orders.
- LONG stop is the three-bar completed swing low minus `0.15*ATR14`; SHORT inverse. Stop rounds outward to tick size.
- TP is fixed `1.50R` from requested entry to normalized stop.
- Risk is `0.25%` equity via `OrderCalcProfit`, rounded down to volume step and margin checked.
- Exit only through broker SL/TP, 16 completed M15 bars, Friday 20:00 server time, weekend or design-end flatten.
- No trailing, breakeven, partial exit or reversal exit.
- Daily loss lock `3.5%`, account peak drawdown lock `8%`, deviation `20` points.

## Acceptance gates

Engineering precedes economics: compile 0/0, non-repaint PASS, D0 proof, History Quality `>97%`, `runtime_failed=false`, exact summary/report reconciliation, no orphan owned inventory and complete run artifacts.

Only if engineering passes, TRAIN must satisfy all: PF `>1.30` after report costs, cadence `2–5` trades per elapsed calendar week, positive expectancy/net profit, each direction at least 30%, no calendar year above 30%, and equity drawdown `<=8%`.

A material miss kills this exact mechanism. No filter, period, direction, session, stop/target, holding, symbol or timeframe rescue is permitted. Only a passing baseline may open cost stress and validation.
