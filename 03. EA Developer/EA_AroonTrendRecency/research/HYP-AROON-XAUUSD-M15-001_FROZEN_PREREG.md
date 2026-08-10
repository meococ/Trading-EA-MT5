# HYP-AROON-XAUUSD-M15-001 — Frozen Aroon-25 Polarity Crossover Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

Informing evidence: CRSI001 was parked only because its native-H1 immediate-next coverage missed the frozen gate. No Aroon outcome, threshold or event count informed this object.

## Identity and thesis

- Hypothesis: `HYP-AROON-XAUUSD-M15-001`
- Family: `aroon-25-most-recent-extreme-polarity-crossover`
- Symbol/timeframe: FivePercent XAUUSD M15 bars aggregated deterministically from the frozen native M5 source
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole source attempt: `AROON001-SOURCE-ATTEMPT-001`

TradingView documents Aroon as a pair of bounded measures of how many periods have elapsed since the most recent lookback high and low. A polarity cross therefore represents a change in which extreme is more recent: a trend-recency state transition, not an oscillator-extreme re-entry, ATR-band flip, volume-flow event or indicator vote.

Formula provenance is TradingView's official Aroon help page. TradingView is research provenance only. Source data, implementation, parity and acceptance remain MT5/AlphaFactory controlled. The official MQL5 built-in list has no native Aroon handle; any later pass may authorize only a separately reviewed direct MQL5 formula implementation.

Repository de-dup found no Aroon hypothesis in the EA shelf, candidate registry or failure catalog. Prior ADX uses are filters inside other mechanisms and do not overlap this highest/lowest-recency crossover.

## Exact M15 aggregation

Read only the frozen XAUUSD native M5 columns `symbol,timeframe,source_epoch,time_utc,utc_ambiguous,high,low,close` from exact inception through `<2023`.

- M15 bucket epoch is `floor(source_epoch/900)*900`.
- A bucket is complete only when it contains exactly three unique M5 rows at bucket offsets `0,300,600`, their UTC timestamps are exactly five minutes apart, all rows are XAUUSD/M5 and UTC-unambiguous, and every price is finite with `high>=low`, `low<=close<=high`, `close>0`.
- Complete M15 `high=max(high)`, `low=min(low)`, `close=last close`; timestamp and source epoch are the offset-zero row.
- An incomplete bucket remains represented as invalid. It is never deleted, filled or interpolated.
- Entire absent bucket ranges caused by normal market closure do not synthesize rows and do not reset bar-count lookbacks.

## Exact Aroon formula

Freeze `period n=25`. At completed M15 bar `t`, inspect exactly 26 existing M15 bucket rows `t-25..t`, allowing `days_since` to range from `0` through `25` and the output to span `100` through `0` as in the documented formula.

- `days_since_high` is the offset from `t` to the **most recent** occurrence of the maximum high in `t-25..t`.
- `days_since_low` is the offset from `t` to the **most recent** occurrence of the minimum low in `t-25..t`.
- Equal extrema therefore choose the occurrence closest to `t`.
- `AroonUp[t] = ((25-days_since_high)/25)*100`.
- `AroonDown[t] = ((25-days_since_low)/25)*100`.

Current and prior polarity require the union `t-26..t`; all 27 represented buckets must be complete and geometrically valid. The first possible event is index `26` of the aggregated inception frame.

## Signal and execution mapping

- raw LONG at completed M15 bar `t`: prior `AroonUp <= AroonDown` and current `AroonUp > AroonDown`;
- raw SHORT: prior `AroonUp >= AroonDown` and current `AroonUp < AroonDown`;
- prior equality arms either direction; current equality emits nothing;
- an executable event requires the immediately following represented M15 timestamp and source epoch to equal `t+15 minutes` and `source_epoch+900`;
- a raw event followed by a gap is consumed and not persisted;
- only next timestamp/epoch is inspected, never next price;
- decision time is `t+15 minutes`.

Forbidden: Aroon thresholds, oscillator magnitude filters, confirmation dwell, session/news/ATR/ADX/volume/VWAP/price filters, cooldown/debounce, position state, stop/target, outcomes or optimization.

## Frozen source and gates

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- XAUUSD M5 data SHA256: `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`
- Source path: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet`
- PyArrow materializes only `time_utc<2023`; scoring uses only `[2018,2023)` aggregated rows.

All gates must pass:

1. exact hashes/authority/one-shot and byte-identical replay;
2. exact M5 inception `2004-06-11T04:15:00Z` and at least 100,000 represented design M15 buckets;
3. feature coverage at least 99.0% of represented design buckets;
4. exact-next coverage at least 97.0% of raw crosses;
5. at least 500 executable events;
6. pooled cadence 2.0–5.0/week;
7. each direction at least 30%;
8. no year above 30% of executable events;
9. each 2018–2022 calendar year cadence 1.25–6.50/week;
10. zero direction conflicts;
11. exact source-only ledger allowlist.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_AROON25_POLARITY_CROSS`. All pass gives `SCREENED_SOURCE_PASS_DIRECT_MQL5_AROON_BUILD_AUTHORIZED`, which permits only a fresh direct-MQL5 correctness/parity child. Economics remains unauthorized.

## Authority boundary

No source data may be opened until preregistration, analyzer, tests and hashes receive independent review and the registry contains one exact unconsumed source-only authority row. No MQL5, MT5, economics, validation, holdout, promotion, paper or live authority is granted here.

References:

- TradingView Aroon formula and trend-recency interpretation: `https://www.tradingview.com/support/solutions/43000501801-aroon-indicator/`
- MetaQuotes built-in indicator list: `https://www.mql5.com/en/docs/indicators`
