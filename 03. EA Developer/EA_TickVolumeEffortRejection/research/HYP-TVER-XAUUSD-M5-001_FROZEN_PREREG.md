# HYP-TVER-XAUUSD-M5-001 — Frozen Source/Cadence Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`  
Frozen before any scan of the specified 2018–2022 source window.

## Identity and economic thesis

- Hypothesis ID: `HYP-TVER-XAUUSD-M5-001`
- Package: `EA_TickVolumeEffortRejection`
- Family: `unsigned-broker-activity-low-progress-single-bar-rejection`
- Symbol/timeframe: FivePercent `XAUUSD`, native M5 Bid bars
- Public design window: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation: 2023–2024 sealed
- Final holdout: 2025+ sealed
- Attempt: `TVER001-SOURCE-ATTEMPT-001`, exactly one source-only attempt

Market thesis: an unusually high number of broker quote updates that produces less price range than the prior local volatility baseline, while the completed bar rejects one extreme, may represent high effort with poor directional result. Direction is fixed opposite the rejected extreme and a future economic child, if authorized, may decide only after this M5 bar has closed and enter no earlier than the following M5 open.

This is not exchange volume, real traded volume, buy/sell pressure, aggressor flow, CVD or order-flow imbalance. It is an unsigned broker-activity state derived from MT5 `tick_volume`.

## Indicator mapping

TradingView documents Relative Volume as current volume divided by an average of prior volumes. This hypothesis freezes the completed M5 bar's `tick_volume` divided by the arithmetic mean of the immediately preceding 10 completed M5 bars. The current bar is excluded from the denominator.

The source is the native FivePercent M5 bar export. TradingView is research inspiration only and is not an acceptance or parity source. Any later deployable implementation must be an MQL5 indicator plus EA and must be verified in MT5.

## Exact causal formation

For completed source bar `t`:

1. `RV10(t) = tick_volume(t) / mean(tick_volume(t-10..t-1))`.
2. Wilder-style true range input is `TR(i) = max(high-low, abs(high-prev_close), abs(low-prev_close))`.
3. `ATR14_prev(t)` is the arithmetic mean of `TR(t-14..t-1)`; the event bar is excluded.
4. `range_ratio(t) = (high(t)-low(t)) / ATR14_prev(t)`.
5. `close_location(t) = (close-low)/(high-low)`.
6. `lower_wick_ratio(t) = (min(open,close)-low)/(high-low)`.
7. `upper_wick_ratio(t) = (high-max(open,close))/(high-low)`.

A bar is source-usable only when all required current/prior fields are finite, prices are geometrically valid, `tick_volume > 0`, both baselines are positive, UTC is unambiguous and the immediately following source timestamp is exactly five minutes later. The next row's prices are forbidden; the timestamp check proves only that a following M5 decision/open exists without a gap.

Frozen event:

- common effort gate: `RV10 >= 2.00`;
- low-progress gate: `range_ratio <= 0.80`;
- LONG: `lower_wick_ratio >= 0.45` and `close_location >= 0.60`;
- SHORT: `upper_wick_ratio >= 0.45` and `close_location <= 0.40`;
- simultaneous LONG and SHORT is invalid and rejected;
- no session, weekday, news, trend, spread, direction or volatility-regime filter;
- no debounce, daily cap or subgroup pruning.

Decision time is the event bar open plus five minutes. A later economic child may enter only at or after that timestamp and must define gaps and execution before accessing outcomes.

## Frozen source data

- Manifest: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json`
- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- Data: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet`
- Data SHA256: `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`
- Required input columns only: `symbol`, `timeframe`, `source_epoch`, `time_utc`, `utc_ambiguous`, `open`, `high`, `low`, `close`, `tick_volume`
- Explicitly forbidden input columns: `spread`, `real_volume`, all future returns, entry/exit prices, MFE/MAE, labels, trades, PnL, PF and drawdown

The manifest states that the bar-data spread column is not cost truth. Therefore no cost or economic conclusion can be made from this attempt.

## Source-only gates

All gates must pass:

1. exact manifest and Parquet hashes match;
2. all selected rows are XAUUSD/M5, UTC-unambiguous, unique and strictly increasing;
3. at least 300,000 design-window rows;
4. source-usable feature coverage at least 99.0% after the 14-bar warm-up;
5. exact-next-M5 timestamp coverage at least 97.0% of feature-usable rows excluding the final row;
6. at least 500 candidates;
7. pooled cadence from 2.0 through 5.0 candidates per elapsed calendar week;
8. LONG share and SHORT share each at least 30%;
9. no calendar year contributes more than 30% of candidates;
10. each design year has cadence from 1.25 through 6.50 candidates per elapsed week;
11. output ledger contains only source-bar timestamp/direction/current-bar features and no future or economic field;
12. deterministic replay of the same frozen source and code produces byte-identical canonical report and candidate ledger, excluding only the separate runtime receipt timestamps.

If any gate fails, verdict is `PARK_SOURCE_FEASIBILITY_EXACT_TVER_MAPPING`; no threshold relaxation, same-ID rerun, outcome read, MQL5 build or economics is allowed. A materially different mechanism requires a fresh ID.

If all gates pass, verdict is `SCREENED_SOURCE_PASS_MQL5_INDICATOR_BUILD_AUTHORIZED`. This authorizes only an exact MQL5 indicator/collection implementation and its correctness/parity audit. It does not authorize trade economics.

## De-duplication and failure radius

This object is materially distinct from:

- VCEX: no volume clock, early impulse, late exhaustion, session or 120-minute fade;
- ECRS: no Kaufman ER shift, ATR compression state, range breakout or EMA bias;
- ASRS: no pivot, sweep depth, reclaim, ADX, retest or sweep-extreme stop;
- ARUC: no signed delta-close activity, same-slot business-date baseline, H1 response or continuation direction;
- TFCVD: no tick polarity, quote-delta, aggressor proxy or real-tick dependency.

Failure applies only to the exact XAUUSD M5 2018–2022 RV10/high-effort, prior-ATR14/low-progress, single-bar wick-rejection decision surface above.

## Authority exclusions

This attempt authorizes no post-event OHLC reference, return, trade simulation, stop, target, position sizing, commission, spread, slippage, PF, drawdown, optimization, validation, holdout, chart selection, MT5 tester launch, MQL5 build, paper trading, promotion or live trading.

