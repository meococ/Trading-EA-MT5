# HYP-WPR-XAUUSD-H1-001 — Frozen Williams Percent Range 14 Re-Entry Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

Informing evidence: exact TRIX-18 M5 zero-line crossing was parked only for 27.47 events/week. No WPR event count, price outcome or economic metric informed this object.

## Identity and thesis

- Hypothesis: `HYP-WPR-XAUUSD-H1-001`
- Family: `williams-percent-range-14-extreme-reentry`
- Symbol/timeframe: native FivePercent XAUUSD H1 Bid bars
- Source state: exact inception `2004-06-11T04:00:00Z` through `<2023`
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole attempt: `WPR001-SOURCE-ATTEMPT-001`

TradingView documents Williams %R as close location inside the rolling highest-high/lowest-low range, with default period 14 and traditional oversold/overbought boundaries `-80/-20`. MetaTrader 5 exposes the one-buffer native `iWPR`. This object tests only the completed-bar transition out of a traditional extreme.

Repository de-dup found no canonical WPR/iWPR/Williams %R hypothesis in the registry or failure catalog. The feature is materially different from TRIX triple-EMA momentum and Aroon extreme recency. It shares an extreme re-entry topology with CRSI/MFI, but its information set is only close location within the current 14-bar high-low range.

## Exact formula

Freeze period `n=14` and, for completed H1 bar `t`:

- `HH[t] = max(high[t-13..t])`
- `LL[t] = min(low[t-13..t])`
- `WPR[t] = -100 * (HH[t] - close[t]) / (HH[t] - LL[t])`

If `HH[t]==LL[t]`, WPR is unavailable and fails closed. No rounding, digit normalization, alternative price source or smoothing is allowed. First WPR is index 13; current/prior state first permits an event at index 14.

Full inception rows must have finite geometry `high>=low` and `low<=close<=high`. Flat `H=L=C` bars are valid source bars and remain in the rolling window. Normal market closures do not create synthetic bars and do not reset the rolling state.

## Signal and execution mapping

- raw LONG on completed H1 bar `t`: prior `WPR<=-80` and current `WPR>-80`;
- raw SHORT: prior `WPR>=-20` and current `WPR<-20`;
- prior equality arms; current equality emits nothing;
- executable only if the immediate next physical row is exactly `source_epoch+3600` and UTC `+1 hour`;
- a raw gap event is consumed, never delayed;
- decision time is `t+1 hour`;
- next price is never read.

Forbidden: alternate thresholds, M15/M30 sibling scan, dwell/failure-swing, divergence, session/news/ATR/ADX/volume/VWAP/trend/price filter, cooldown/debounce, position state, stop/target, outcomes and optimization.

## Frozen source and gates

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- XAUUSD H1 SHA256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`
- PyArrow materializes only `time_utc<2023`; scoring uses `[2018,2023)`.

All gates must pass:

1. hashes/authority/one-shot and deterministic replay;
2. at least 25,000 design rows;
3. feature coverage at least 99% of design rows;
4. exact-next coverage at least 97%;
5. at least 500 executable events;
6. pooled cadence 2–5/week;
7. each direction at least 30%;
8. no year above 30% of events;
9. each 2018–2022 year cadence 1.25–6.50/week;
10. zero direction conflicts;
11. exact outcome-blind ledger allowlist.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_WPR14_EXTREME_REENTRY`. All pass gives `SCREENED_SOURCE_PASS_NATIVE_IWPR_PARITY_CHILD_AUTHORIZED`; this permits only a fresh every-bar native `iWPR(14)` correctness child, never economics directly.

No source access may occur until exact preregistration, analyzer, tests and independent review are registry-bound. No MQL5, MT5, economics, validation, holdout, promotion, paper or live authority is granted.

References:

- TradingView Williams %R: https://www.tradingview.com/support/solutions/43000501985-williams-r-r/
- MetaQuotes native iWPR: https://www.mql5.com/en/docs/indicators/iwpr
