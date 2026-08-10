# HYP-ICH-XAUUSD-M5-001 — Frozen Ichimoku Full-alignment Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

## Thesis and provenance

- Hypothesis: `HYP-ICH-XAUUSD-M5-001`
- Family: `ichimoku-9-26-52-tenkan-kijun-cross-cloud-alignment`
- Symbol/timeframe: FivePercent XAUUSD native M5 Bid bars
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole attempt: `ICH001-SOURCE-ATTEMPT-001`

TradingView documents Ichimoku as one integrated indicator of support/resistance, trend and momentum, with price above/below the cloud and Span A/B ordering as trend evidence. MetaQuotes exposes the native `iIchimoku` buffers and standard 9/26/52 periods. The hypothesis is that a Tenkan/Kijun polarity cross is selective enough for an executable research lane only when current price and the displayed cloud agree with that direction.

This family is absent from the candidate registry, failure catalog and EA shelf. It is structurally distinct from compression breakouts, price sweep/retests, activity/volume response, MFI and quote-flow objects.

## Exact indicator calculation

On completed native M5 Bid bars:

- Tenkan at `t` = `(highest high over t-8..t + lowest low over t-8..t)/2`.
- Kijun at `t` = `(highest high over t-25..t + lowest low over t-25..t)/2`.
- raw Span A at `i` = `(Tenkan[i] + Kijun[i])/2`.
- raw Span B at `i` = `(highest high over i-51..i + lowest low over i-51..i)/2`.
- displayed cloud at `t` uses raw Span A/B from `t-26`, matching the 26-bar forward plot displacement.

No Chikou value is used. No future value is read. The complete current-event dependency is `t-77..t`; the first usable event row is index 77. Every required row must have finite/geometrically valid high, low and close. Bar-count windows intentionally span normal market closures; the only wall-clock execution requirement is the exact next source timestamp.

## Exact signal mapping

- raw LONG at completed bar `t`: prior Tenkan `<=` prior Kijun, current Tenkan `>` current Kijun, current close strictly above both displayed cloud spans, and displayed Span A strictly above Span B.
- raw SHORT: exact inverse — prior Tenkan `>=` prior Kijun, current Tenkan `<` current Kijun, current close strictly below both displayed spans, and Span A strictly below Span B.
- Equality never qualifies for current cross, cloud clearance or cloud polarity.
- Each cross is a single raw event; no position state, debounce, cooldown or signal deletion is applied.
- An executable source event additionally requires the immediately following timestamp to equal `t+5 minutes`. A raw event at a gap is consumed but not persisted. No next-row price is read.
- Decision timestamp is `t+5 minutes`, after bar `t` is complete.

Forbidden: alternative periods, Chikou filter, unshifted/future cloud, ATR/ADX/volume/MFI/wick/session/news filters, timeout, cooldown, debounce, daily cap, optimization, subgroup pruning and every outcome field.

## Frozen source

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- XAUUSD M5 Parquet SHA256: `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`
- Only symbol/timeframe/source epoch/time/UTC ambiguity/high/low/close columns may be read.
- PyArrow must materialize only `2018 <= time_utc < 2023`, followed by a fail-closed post-read assertion.
- Post-event OHLC and all return/trade/cost fields remain forbidden.

## Source gates

All must pass:

1. hash/registry/one-shot bindings and byte-identical in-memory replay;
2. at least 300,000 design rows;
3. feature coverage at least 99.0% after exactly 77 warmup rows;
4. exact-next timestamp coverage at least 97.0% of raw aligned crosses;
5. at least 500 executable events;
6. pooled cadence 2.0–5.0/week;
7. LONG and SHORT share each at least 30%;
8. no year above 30%;
9. each design-year cadence 1.25–6.50/week;
10. zero simultaneous direction conflicts;
11. ledger keys equal the frozen source-only allowlist.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_ICHIMOKU_FULL_ALIGNMENT`. All pass gives `SCREENED_SOURCE_PASS_MQL5_IICHIMOKU_BUILD_AUTHORIZED`, allowing only native `iIchimoku(9,26,52)` parity/correctness and signal-collector work. Economics remains unauthorized.

## Authority boundary

This preregistration authorizes no scan until its analyzer/tests/hashes receive independent static review and a matching registry probe row. It authorizes no outcome, MT5 tester, MQL5 build, validation, holdout, paper, promotion or live operation.
