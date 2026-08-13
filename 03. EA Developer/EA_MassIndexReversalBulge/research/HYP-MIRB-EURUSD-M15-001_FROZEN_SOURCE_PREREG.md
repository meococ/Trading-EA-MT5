# HYP-MIRB-EURUSD-M15-001 — frozen source preregistration

Status: frozen before the sole source scan. No outcomes, costs, trade simulation,
MT5 execution, optimization, validation or holdout are authorized.

## Thesis and novelty

The Mass Index measures expansion and contraction of the bar high-low range. A
classic reversal bulge occurs after the 25-period index rises strictly above 27
and later falls strictly below 26.5. The signal reverses the prevailing EMA9
close slope: falling slope emits LONG; rising slope emits SHORT.

This is a range-volatility state transition. It does not reuse volume profile,
value-area reentry, directional price oscillator extremes, initial balance,
cross-asset residuals, sweep/retest or indicator voting. Repository de-dup found
no prior Mass Index / Dorsey reversal-bulge object. Formula provenance:
https://www.tradingview.com/support/solutions/43000589169-mass-index/ and
https://www.tradingview.com/support/solutions/43000502589-moving-averages/.

## Frozen mapping

- Symbol/timeframe: EURUSD M15, deterministically aggregated from complete
  broker-native FivePercent M5 triplets.
- Source preload: `2015-01-01T00:00:00Z`; score only
  `[2016-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`.
- Range `R=high-low`.
- EMA9 uses multiplier `2/(9+1)` and an SMA9 seed. `EMA1=EMA9(R)`;
  `EMA2=EMA9(EMA1)`.
- `MassIndex=sum25(EMA1/EMA2)`. Division requires finite positive EMA2.
- FSM: IDLE arms on `MassIndex > 27`. ARMED waits through all values `>=26.5`;
  first `MassIndex < 26.5` completes and resets the bulge.
- At completion, EMA9(close) slope `<0` emits LONG and `>0` emits SHORT.
  Equality emits nothing but still consumes/resets the completed bulge.
- Decision/execution timestamp is the immediate next native M15 open exactly
  `+900` seconds. Missing exact next consumes the raw event without persistence.
- Normal market closures do not reset EMA/FSM state. Invalid/nonfinite price or
  indicator input resets the FSM and EMA seed chain fail-closed.
- No session, weekday, direction, ATR, volume, threshold variant, cooldown,
  debounce, price outcome or post-event field.

## Source gates

- Design rows at least 190,000; feature coverage at least 99%.
- Exact-next coverage at least 97%.
- Executable events at least 730.
- Pooled cadence 2–5 events per elapsed week.
- LONG and SHORT each at least 30%.
- Maximum calendar-year share at most 20%.
- Every calendar year cadence 1.25–6.5/week.
- Zero direction conflicts.

Any failed gate parks this exact mapping before MQL5/economics. No threshold,
period, timeframe, session or trend-direction rescue is allowed under this ID.

## Frozen data and attempt

- Manifest: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json`
  SHA256 `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.
- Data: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_M5_ALL_AVAILABLE_20260801.parquet`
  SHA256 `6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8`.
- Sole source attempt: `MIRB001-SOURCE-001`.
- Paid data used: false.

