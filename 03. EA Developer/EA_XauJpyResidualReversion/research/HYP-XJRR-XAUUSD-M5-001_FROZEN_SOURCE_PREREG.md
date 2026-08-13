# HYP-XJRR-XAUUSD-M5-001 — frozen source-feasibility preregistration

Status: `FROZEN_BEFORE_SOURCE_DATA_OPEN`

## Thesis

Short-horizon XAUUSD returns contain a common USD/rates component proxied by
USDJPY. A completed XAUUSD M5 move that is extreme relative to a rolling
no-intercept XAU-on-USDJPY beta, then crosses back inside a two-sigma residual
boundary, represents temporary cross-asset dislocation decay rather than a
directional breakout. The economic child would trade XAUUSD residual reversion.

This is a synchronized cross-asset statistical mechanism. It is materially
different from single-symbol indicator transitions, fixed-session opening
drives, prior-day acceptance and price-only sweep/reclaim objects.

## Frozen source contract

- Native FivePercent `XAUUSD M5` and `USDJPY M5` fully closed Bid bars from
  `DATA-FIVEPERCENT-5ASSET-MULTITF-004`.
- XAU file SHA256:
  `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`.
- USDJPY file SHA256:
  `FECD42A01AFD14D4149121A122468DA5597939A20DD1533A36DA711E6FA2DAFD`.
- Design window on the primary server axis: `[2018-01-01, 2023-01-01)`;
  elapsed weeks `1826/7`.
- Join only exact equal `source_epoch`; symbol/timeframe/price geometry/tick
  volume must be valid and timestamps strictly increasing.
- Return at completed bar i is `log(close_i / close_{i-1})` for each symbol.
- For decision t, use exactly the preceding 288 paired completed returns
  `t-288..t-1`. Normal market closures are bar-count spans, not synthetic bars.
- `beta_t = sum(rx*rj) / sum(rj^2)` with no intercept; denominator must be
  positive.
- Using that same beta over the preceding 288 pairs, compute sample standard
  deviation of residuals `rx - beta_t*rj` with `ddof=1`; it must be positive.
- `z_t = (rx_t - beta_t*rj_t) / sigma_t`. `z[t-1]` is its own causal value
  calculated from its own preceding window.
- LONG raw event iff `z[t-1] <= -2.0` and `z[t] > -2.0`; SHORT exact inverse
  from `>= +2.0` to `< +2.0`. Equality only arms, never completes a cross.
- Consume only the first raw event per FivePercent server calendar date and
  impose a deterministic 12-M5-bar lockout after consumption.
- Availability is the exact next synchronized XAU/USDJPY timestamp at `t+300`.
  Inspect timestamp only, never next OHLC.
- Convert availability server time to UTC with FivePercent winter UTC+2 and
  Europe-DST UTC+3. Friday availability at or after 20:00 UTC is consumed but
  non-executable.
- Ledger contains only timestamps, direction, beta/sigma and prior/current z;
  no post-decision price, return, PnL, cost, MFE/MAE or PF.

## Gates before any MQL5

- Joined design rows at least 300,000; feature coverage at least 99% after the
  fixed warmup.
- Exact-next coverage at least 97%; executable events at least 500.
- Executable cadence 2–5/week; each direction at least 30%; no year above 30%;
  every 2018–2022 decision year 1.25–6.5/week; zero direction conflicts.

Any failure parks this exact mapping before implementation. No beta window,
z-threshold, daily consumption, Friday boundary, timeframe, symbol or direction
rescue after the count. A pass authorizes implementation review only, not edge.
