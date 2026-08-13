# HYP-FLI-EURUSD-M15-001 — frozen source-feasibility preregistration

Status: `FROZEN_PRE_SOURCE_SCAN`

## Market thesis and provenance

Follow Line is a single volatility-state mechanism, not an indicator vote. A
close outside a Bollinger Band updates an ATR-offset recursive line; the line
can only ratchet in the active direction. A trade candidate exists only when
the line changes direction. This tests whether displacement beyond recent
noise persists long enough to create a usable M15 trend state on EURUSD.

The default parameters are taken from the open-source TradingView Follow Line
indicator: BB period `21`, deviation `1.0`, ATR filter enabled and ATR period
`5`. TradingView describes BUY/SELL as a change in Follow Line direction after
price closes beyond the corresponding band:
`https://www.tradingview.com/script/UXKo4RaJ/`. TradingView is research and
behavior provenance only. The exact local formula below and its bidirectional
golden-vector tests are the source/MQL5 parity authority; no claim is made that
TradingView's mutable hosted bytes are acceptance evidence.

Repository de-dup found no prior Follow Line object. It is distinct from
Supertrend/Chandelier because Bollinger displacement selects when the state
can update, while ATR only offsets the recursive line; it is not a CCI, QQE,
Donchian, Ichimoku, Keltner-squeeze or session-breakout revision.

## Frozen source and window

- Hypothesis `HYP-FLI-EURUSD-M15-001`; future EA `EA_FollowLineTrend`.
- FivePercent native EURUSD M1 source:
  `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`,
  SHA256 `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Aggregate exact 900-second server buckets to M15: first open, max high, min
  low, last close. Missing buckets are not synthesized.
- Read prehistory from `2015-01-01`; score only completed M15 bars in
  `[2016-01-04, 2023-01-01)`. Validation `2023-2024` and holdout `2025+`
  remain unopened.
- No paid/external data, outcome, next-bar price, spread, commission, order,
  PnL, PF, validation or holdout field is allowed in the source attempt.

## Exact closed-bar formula

On completed M15 bar `t`:

1. `basis_t = SMA21(close)` and `sigma_t` is the population standard
   deviation (`ddof=0`) over the same 21 closes.
2. `upper_t = basis_t + sigma_t`; `lower_t = basis_t - sigma_t`.
3. True range is standard prior-close TR. ATR5 is Wilder RMA: the first ATR is
   SMA of the first five valid TR values, then
   `ATR_t = (4*ATR_(t-1)+TR_t)/5`.
4. `BBSignal_t = +1` only when `close_t > upper_t`, `-1` only when
   `close_t < lower_t`, otherwise zero. Equality is inside/no update.
5. Follow Line starts uninitialized to avoid a price-sign bias from a numeric
   zero seed. The first nonzero BBSignal initializes the line to
   `low-ATR` for `+1` or `high+ATR` for `-1`, sets the corresponding trend, and
   never emits an event. Initialization is tested in both directions.
6. After initialization:
   - if `BBSignal=+1`, `line_t=max(low_t-ATR5_t,line_(t-1))`;
   - if `BBSignal=-1`, `line_t=min(high_t+ATR5_t,line_(t-1))`;
   - otherwise `line_t=line_(t-1)`.
7. Trend starts neutral. If `line_t>line_(t-1)`, trend becomes `+1`; if lower,
   `-1`; equality retains the prior trend.
8. LONG only on `trend_(t-1)=-1` and `trend_t=+1`; SHORT is the exact inverse.
   First non-neutral initialization is not an event.

The source/decision timestamp is completed bar `t`; execution availability is
stored separately and is timestamp-only at the exact next native M15 open
`t+900s`. A missing next bucket consumes the raw event. Calendar-year gates use
the decision timestamp `t`, never availability. No session, weekday, direction,
cooldown, quota, HTF, volume, secondary indicator or outcome-derived filter
exists.

## Outcome-blind source gates

- Exact source SHA/schema/window/geometry, strict M1 order and deterministic
  same-frame replay pass.
- DESIGN has at least `150000` M15 rows and usable formula coverage `>=99%`.
- Exact-next coverage of raw events is `>=97%`.
- At least `500` executable events; pooled cadence is `2–5/week` over exact
  elapsed DESIGN calendar seconds.
- LONG and SHORT are each at least `30%`; no year exceeds `25%` of events.
- Every calendar year cadence is `1.25–6.5/week`; zero conflicts.

Any failed gate parks this exact mapping with no economic claim. Do not rescue
via BB/ATR parameters, threshold, clock/session, cooldown, direction, timeframe
or symbol after the count. Only a complete source pass may authorize a direct
MQL5 build and one untuned Model-0 baseline.
