# HYP-TRIX-XAUUSD-M5-001 — Frozen TRIX-18 Zero-Line Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

Informing evidence: exact Aroon-25 M15 polarity was parked for 75.12% feature coverage and 13.98 events/week. No TRIX event count, threshold, outcome or profit metric informed this object.

## Identity and thesis

- Hypothesis: `HYP-TRIX-XAUUSD-M5-001`
- Family: `trix-18-triple-ema-momentum-zero-cross`
- Symbol/timeframe: native FivePercent XAUUSD M5 Bid bars
- Source state: exact inception `2004-06-11T04:15:00Z` through `<2023`
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole attempt: `TRIX001-SOURCE-ATTEMPT-001`

TradingView documents standard TRIX as EMA-18 of close, EMA-18 of that EMA, EMA-18 of the second EMA, followed by one-period percentage change of the triple-smoothed EMA. Positive TRIX represents upward momentum and negative TRIX downward momentum. This object tests only a zero-line state transition; it does not add the optional signal line, divergence, price confirmation or any filter.

MetaTrader 5 exposes one-buffer native `iTriX`. TradingView supplies formula provenance; the frozen direct calculation controls source screening. If and only if source gates pass, a fresh correctness child must prove every-bar parity with native `iTriX` before any EA/economic run.

Repository de-dup found no prior TRIX/iTriX hypothesis. Triple-EMA momentum zero transition is materially distinct from Aroon extreme-recency polarity, CRSI extreme re-entry, Supertrend band-state flips, Vortex directional-range crossovers and volume-flow objects.

## Exact formula and seed

Freeze `n=18`, close source and `alpha=2/(n+1)`.

For each EMA stage:

1. the first EMA value is the simple average of the first 18 finite consecutive input values;
2. earlier output is unavailable;
3. later `EMA[t] = alpha*input[t] + (1-alpha)*EMA[t-1]`;
4. no rounding, digit normalization, reseed or gap reset is allowed.

Because the full close series is required finite and positive from inception through 2022:

- EMA1 first exists at index 17;
- EMA2 first exists at index 34;
- EMA3 first exists at index 51;
- `TRIX[t] = 100*(EMA3[t]-EMA3[t-1])/EMA3[t-1]` first exists at index 52;
- current/prior zero-line state first permits an event at index 53.

Normal market closures do not create synthetic bars and do not reset recursive state. Any nonfinite/nonpositive close, null/ambiguous identity, unordered/duplicate timestamp or epoch, or broken frozen inception fails the attempt before indicator analysis.

## Signal and execution mapping

- raw LONG on completed M5 bar `t`: prior `TRIX<=0` and current `TRIX>0`;
- raw SHORT: prior `TRIX>=0` and current `TRIX<0`;
- prior equality arms; current equality emits nothing;
- executable only if the immediate next physical row is exactly `source_epoch+300` and UTC `+5 minutes`;
- a raw gap event is consumed, never delayed;
- decision time is `t+5 minutes`;
- next price is never read.

Forbidden: signal-line crossover, threshold magnitude, divergence, dwell/confirmation, session/news/ATR/ADX/volume/VWAP/price filter, cooldown/debounce, position state, stop/target, outcomes and optimization.

## Frozen source and gates

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- XAUUSD M5 SHA256: `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`
- PyArrow materializes only `time_utc<2023`; scoring uses `[2018,2023)`.

All gates must pass:

1. hashes/authority/one-shot and deterministic replay;
2. at least 300,000 design rows;
3. feature coverage at least 99.9% of design rows;
4. exact-next coverage at least 97%;
5. at least 500 executable events;
6. pooled cadence 2–5/week;
7. each direction at least 30%;
8. no year above 30% of events;
9. each 2018–2022 year cadence 1.25–6.50/week;
10. zero direction conflicts;
11. exact outcome-blind ledger allowlist.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_TRIX18_ZERO_CROSS`. All pass gives `SCREENED_SOURCE_PASS_NATIVE_ITRIX_PARITY_CHILD_AUTHORIZED`; this permits only a fresh correctness/parity child, never economics directly.

No source access may occur until exact preregistration, analyzer, tests and independent review are registry-bound. No MQL5, MT5, economics, validation, holdout, promotion, paper or live authority is granted.

References:

- TradingView TRIX calculation: https://in.tradingview.com/support/solutions/43000502331/
- TradingView EMA seed/calculation: https://www.tradingview.com/support/solutions/43000502589-moving-averages/
- MetaQuotes native iTriX: https://www.mql5.com/en/docs/indicators/itrix
