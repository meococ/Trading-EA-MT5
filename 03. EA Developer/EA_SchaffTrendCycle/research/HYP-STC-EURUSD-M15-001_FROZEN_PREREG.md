# HYP-STC-EURUSD-M15-001 — frozen untuned baseline

Status: `FROZEN_PRE_BASELINE`

## Market thesis

Schaff Trend Cycle (STC) combines an EMA-difference trend measure with two
stochastic normalizations. The thesis is not generic oversold mean reversion:
an STC reset is traded only in the direction of its own underlying EMA trend.
The expected edge is earlier continuation entry after a pullback while the
23/50 EMA trend remains intact.

Formula provenance is research-only:

- Doug Schaff's original article describes MACD passed through a reworked
  stochastic and the 25/75 cycle lines:
  `https://forex-indicators.net/files/indicators/Schaff_Trend_Cycle.pdf`.
- TradingView open-source STC documentation uses the classic
  `23/50/10/3/3`, close source and buy-above-25/sell-below-75 mapping:
  `https://www.tradingview.com/script/eZwlb7PV/`.

TradingView is not parity or acceptance evidence. All decisions and outcomes
are produced by the direct MQL5 implementation and MT5 Strategy Tester.

## Frozen indicator

- Source: completed EURUSD M15 close.
- Fast/slow EMA: `23 / 50`.
- Cycle window: `10` bars for both stochastic passes.
- First and second EMA smoothing: `3 / 3`.
- Zero-range stochastic carries the prior normalized value, seeded at `50`.
- Recurrence is initialized once from the exact native-M15 preload population:
  first server bar `2015.01.02 09:00`, last bar before DESIGN
  `2015.12.31 20:00`, exactly `24,776` bars. It is then advanced once per
  completed M15 bar. Missing/late/unsynchronized prehistory fails closed and no
  rolling-window reseeding is allowed. The origin proof is frozen in
  `HYP-STC-EURUSD-M15-001_PRELOAD_ORIGIN_PROOF.json`.
- LONG: prior STC `<=25`, current STC `>25`, current EMA23-EMA50 `>0`.
- SHORT: prior STC `>=75`, current STC `<75`, current EMA23-EMA50 `<0`.
- One first eligible signal per broker-server date. No ADX, higher timeframe,
  price-pattern, session, news, volume or direction filter.
- Decision is the completed bar; entry is the exact next M15 open. A non-900s
  decision-to-availability gap consumes no signal and creates no order.

## Frozen execution and risk

- One owned position, no pending-order strategy, no pyramiding.
- Risk `0.25%` of current equity, volume rounded downward to broker step.
- Stop distance `1.50 * ATR14`; target `1.50R` from normalized actual request
  geometry.
- Exit only by SL, TP, `16` completed M15 bars, Friday/weekend flatten or design
  end. No trailing, break-even, partial close or opposite-signal exit.
- Daily loss lock `3.5%`; peak-equity drawdown lock `8%`.
- No new entry from Friday `20:00` broker-server time; flatten then and during
  weekend.
- Deposit `100000`, leverage `1:100`, current spread, report commission/swap,
  Model `0`, execution mode `0`, fixed delay `0`.

## Sealed chronology

- DESIGN baseline: `2016.01.04-2021.01.01`.
- Validation: `2021.01.01-2022.01.01`, unopened.
- Final holdout: `2022.01.01-2023.01.01`, unopened.
- Exactly one untuned DESIGN baseline. No optimization, parameter sweep,
  session/direction filtering or same-ID economic rerun.

## Gates

- Engineering: 0E/0W compile, focused tests, non-repaint PASS, complete report,
  HQ `>97%`, valid source/EX5/run identity.
- DESIGN: PF `>1.30` after report costs, cadence `2-5/week`, equity DD `<=8%`,
  both directions `>=30%`, no calendar year `>35%` of trades.
- Only a DESIGN pass may open x1.5/x2 cost stress. Required: x1.5 PF `>=1.25`,
  x2 PF `>=1.00`.
- Validation/holdout, WFA, sensitivity, Monte Carlo and execution forensics stay
  sealed until the preceding gates pass.

## Falsification

Kill the exact mechanism without rescue if it is implementation-correct and
PF `<1.0`, pre-cost expectancy is negative, or weakness is broad across both
directions and multiple years. Do not add ADX, sessions, alternate thresholds,
R:R, ATR period or hold-time changes from the readout.
