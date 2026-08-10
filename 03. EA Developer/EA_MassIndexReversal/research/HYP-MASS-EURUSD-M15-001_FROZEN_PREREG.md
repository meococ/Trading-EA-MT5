# HYP-MASS-EURUSD-M15-001 — frozen source-feasibility preregistration

Status: `FROZEN_PRE_SOURCE_SCAN`

## Independent mechanism

This hypothesis is a materially new volatility-structure mechanism after the
terminal economic failure of classic STC. It does not reuse STC momentum,
thresholds, signals, stops or outcome breakdowns.

TradingView's Mass Index documentation defines the indicator from the
high-low range: EMA9(range) divided by EMA9 of that EMA, summed for 25 bars.
The classic reversal bulge arms above 27 and completes below 26.5:
`https://www.tradingview.com/support/solutions/43000589169-mass-index/`.
TradingView is formula provenance only; MT5 remains implementation and
acceptance authority.

## Frozen source mapping

- Symbol/timeframe: EURUSD native-broker M1 aggregated to M15, bid OHLC.
- Source: `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`,
  declared SHA256
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Prehistory begins at first available closed native M1 bar in 2015; score only
  completed M15 decisions in `2016.01.04 <= t < 2021.01.01`.
- M15 bars are derived by exact 900-second server/source-epoch buckets:
  open first, high max, low min, close last. No synthetic closure bars.
- EMA recurrence alpha is `2/(9+1)`, seeded from the first valid range/close.
- `ratio_t = EMA9(high-low)_t / EMA9(EMA9(high-low))_t`.
- `MassIndex_t = sum(ratio, 25)`; denominator nonpositive/nonfinite fails closed.
- IDLE -> ARMED only when Mass Index is strictly `>27`.
- First later completed bar strictly `<26.5` completes and resets the bulge.
- On completion: LONG only when EMA9(close)_t > EMA9(close)_(t-1); SHORT only
  when lower. Equality consumes/reset the bulge without a candidate.
- Candidate decision is completed M15 t; executable only if the next native M15
  timestamp is exactly t+900 seconds. Inspect next timestamp only, never price.
- No session, weekday, HTF, ADX, volume, cooldown, debounce, ATR, price-pattern,
  stop/target or outcome field.

## Outcome-blind source gates

- Source SHA/schema/window/geometry and deterministic replay must pass.
- Aggregated DESIGN rows `>=120,000`; usable indicator coverage `>=99%` after
  exact warmup.
- Executable candidates `>=500`; pooled cadence `2-5/week` using exact elapsed
  DESIGN seconds.
- LONG and SHORT each `>=30%`; no calendar year `>35%` of candidates.
- Each calendar year cadence `1.25-6.5/week`.

Any failed source gate parks this exact mapping only. No economic/no-edge
claim is allowed, and no threshold/session/filter rescue or same-ID scan is
authorized. Only a complete source pass may authorize an EA build with a
separately frozen ATR/risk/exit contract.
