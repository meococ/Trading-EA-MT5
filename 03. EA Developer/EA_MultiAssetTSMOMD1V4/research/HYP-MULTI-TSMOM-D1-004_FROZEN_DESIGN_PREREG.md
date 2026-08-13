# HYP-MULTI-TSMOM-D1-004 — frozen 365-calendar-day TSMOM design

Status: frozen before V4 economics. Source gate must pass first.

## Mechanism

The candidate is own-asset time-series momentum across liquid FX, gold and
BTC. The economic claim is slow information/capital-flow adjustment and trend
persistence, not candle geometry or sub-minute microstructure. A professional
macro trader expresses this as a diversified, volatility-scaled basket rather
than nine independent optimized trades.

## Signal and decision clock

- Decision: once per UTC Monday, at the first time all active custom symbols
  have a valid current Bid/Ask tick.
- Current reference: the latest completed D1 close strictly before decision.
- Lookback reference: the latest completed D1 close whose close time is at or
  before `decision_time - 365 days`.
- Direction is only `sign(current_close / lookback_close - 1)`. Exact zero is
  flat. No rank, threshold, filter or parameter grid exists.
- Volatility is the sample standard deviation of 60 completed D1 log returns.
  It is annualized by observed calendar density:
  `sigma * sqrt(365.2425 * 60 / elapsed_calendar_days)`.
- Any incomplete/noncausal series makes the whole weekly snapshot invalid.

## Universe and deterministic weights

Eight core assets are active from 2018-01-01. BTCUSD becomes the ninth active
asset exactly at 2018-05-14 00:00 UTC.

Raw absolute weight is inverse annualized volatility and raw gross is one.
Caps are applied only downward; freed capacity is never redistributed upward:

1. clip each asset at 18%;
2. if aggregate FX gross exceeds 70%, scale all seven FX weights down together;
3. clip XAU at 25% and BTC at 20%;
4. USD-factor mapping is -1 for EURUSD/GBPUSD/AUDUSD/NZDUSD longs, +1 for
   USDJPY/USDCAD/USDCHF longs, and 0 for XAU/BTC. If absolute signed USD-factor
   exposure exceeds 25%, scale all seven FX weights down together;
5. if total gross still exceeds 100%, scale every weight down together.

Downward-only projection cannot re-violate an earlier cap. The portfolio may
use less than 100% gross. Below-minimum lots are dropped without reallocation.

## Execution and lifecycle

- Existing positions are adjusted by signed net delta; routine full
  close/reopen is prohibited.
- Direction reversals close the old leg before opening the new direction.
- A failed/partial weekly transition is engineering-invalid and is retried
  toward the same frozen target; signals and weights are not recomputed.
- If common source/trade readiness never occurs before Tuesday, the previous
  basket remains. No active asset is silently removed.
- No SL, TP, daily loss stop, weekly loss stop, session/news alpha filter or
  maximum holding period. Exposure caps are the risk control. Positions may
  remain open overnight and over weekends.

## Costs and matched comparator

MT5 pays imported native Bid/Ask spread and configured commission. Controlled
financing replaces, rather than adds to, native tester swap:
`pre_financing_net = native_net - signed_native_swap`; the adverse overlay is
then subtracted. This removes both native debits and credits before applying one
frozen research cost and prevents double counting.

The current FivePercent source receipts are hash-bound by broker-contract result
`5FD9A822...DF237` and weekday-schedule result `3D547E92...C9A67` (both
History Quality 100%, zero orders). Mode 1 uses
`abs(swap) * point / tick_size * tick_value` USD per lot per unit weekday
coefficient. Mode 4 uses
`contract * current_price * abs(rate_pct) / 100 / 360`. The eight FX/XAU
symbols have coefficients Sun 0, Mon-Thu 1, Fri 3, Sat 0; BTC has 1 on all
seven days. Current worst annualized sides are at most 5.787335% FX, 8.027304%
XAU and 69.755556% BTC on a 365-calendar-day horizon.

The frozen base overlay is `max(current worse side, class floor)` with floors
FX 6%, XAU 9%, BTC 70%, rounded upward from the current class maxima. Exposure
telemetry is last-state-per-calendar-day: a post-rebalance snapshot replaces
the earlier daily-open state, and missing weekend days carry the last state
forward. Positive financing credit is zero. This is a conservative current-
broker proxy, not historical PIT financing proof.

Stress is 1.5x and 2.0x every adverse cost component. The primary comparator is
a separate same-universe, same-volatility, same-cap long-only basket. Zero net
return is a second hurdle. A flipped signal is diagnostic only.

## Frozen splits and pass gates

- DESIGN: `[2018-01-01, 2022-01-01)`.
- VALIDATION: `[2022-01-01, 2024-01-01)` sealed until DESIGN survives.
- HOLDOUT: `[2024-01-01, 2026-08-12)` sealed until validation survives.

DESIGN must have at least 207 source-valid weekly decisions and at least 180
completed target transitions. Base net PF >= 1.25; 1.5x PF >= 1.10; 2x PF >=
1.00; net annualized return / maximum drawdown >= 0.70; maximum equity drawdown
<= 18%; at least 3/4 positive calendar years; top 5% weeks <= 25% of total net
profit; no one asset contributes more than 40% of total net profit; and V4 must
beat the frozen long-only comparator on PF and average weekly net return.

Failure kills this exact identity. No post-readout universe, activation date,
direction, lookback, volatility window, cap, cost, session or exit rescue is
allowed.
