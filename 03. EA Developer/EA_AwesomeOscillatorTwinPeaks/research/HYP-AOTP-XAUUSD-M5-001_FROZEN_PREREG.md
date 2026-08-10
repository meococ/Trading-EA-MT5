# HYP-AOTP-XAUUSD-M5-001 - Frozen Awesome Oscillator Twin Peaks Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

Informing evidence: exact perfected TD Setup 9 on H1 was parked only because exact-next coverage was 95.14% below the frozen 97% gate. No AO count, price outcome or economic metric informed this object.

## Identity and thesis

- Hypothesis: `HYP-AOTP-XAUUSD-M5-001`
- Family: `awesome-oscillator-5-34-median-twin-peaks`
- Symbol/timeframe: native FivePercent XAUUSD M5 Bid bars
- Source state: exact inception `2004-06-11T04:15:00Z` through `<2023`
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023-2024 and holdout 2025+ remain sealed
- Sole attempt: `AOTP001-SOURCE-ATTEMPT-001`

TradingView and MetaQuotes define Awesome Oscillator as the difference between 5- and 34-period simple moving averages of median price. TradingView defines bullish Twin Peaks as two valleys below zero with the second valley higher than the first and a green reversal bar; bearish Twin Peaks is the strict inverse above zero.

Repository de-dup found no Awesome Oscillator, `iAO`, SMA5-minus-SMA34 median-price or Twin Peaks object in the registry or failure catalog. Same-side oscillator topology is materially distinct from TD9 run-length exhaustion, WPR extreme re-entry, TRIX zero crossing and price-MFI joint-pivot divergence.

## Exact causal calculation and FSM

For each completed M5 bar `t`:

- `median[t] = (high[t] + low[t]) / 2`.
- `AO[t] = SMA5(median)[t] - SMA34(median)[t]`.
- The first finite AO value is index 33. Full inception continuity is required; state is never seeded at 2018.

For confirmation bar `c`, candidate pivot is `p=c-1`:

- Bullish valley is confirmed iff all `AO[c-2]`, `AO[p]`, `AO[c]` are strictly below zero and `AO[c-2] > AO[p] < AO[c]`.
- The first confirmed bullish valley initializes the bullish anchor only.
- Each later consecutive bullish valley emits LONG iff `AO[p] > bullish_anchor`; equality does not signal.
- Every confirmed valley replaces the bullish anchor whether or not it signals.
- Bearish peak is symmetric: all three values strictly above zero, `AO[c-2] < AO[p] > AO[c]`, and a later peak emits SHORT iff `AO[p] < bearish_anchor`; every confirmed peak replaces the bearish anchor.

The confirmation bar itself is the required green/red reversal because LONG requires `AO[c] > AO[p]` and SHORT requires `AO[c] < AO[p]`. No extra delayed bar is used.

`AO==0`, crossing zero, nonfinite AO or invalid source input resets the incompatible same-side chain; no zero crossing may occur between the two paired pivots. Both chains reset on nonfinite/zero. The first mathematically possible second-pivot event is index 37, but dependency is stateful from inception or the last zero reset plus each AO value's 34-bar window. No fixed `t-N..t` dependency is claimed.

## Execution mapping

- decision only at the exact next physical M5 row, both `source_epoch+300` and UTC `+5 minutes`;
- a raw gap event is consumed, never delayed, while the current pivot remains the new anchor;
- decision time is `c+5 minutes`;
- next price is never read.

Forbidden: zero-line crossover entries, saucer, extra color bar, minimum peak separation, magnitude/zero-distance thresholds, alternate AO periods, sibling timeframe tournament, session/news/ATR/ADX/volume/trend filters, cooldown/debounce, stops/targets, outcomes and optimization.

## Frozen source and gates

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- XAUUSD M5 SHA256: `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`
- PyArrow materializes only `time_utc<2023`; scoring uses `[2018,2023)`.

All gates must pass: hashes/one-shot/replay; design rows >=300,000; feature coverage >=99.9%; exact-next >=97%; executable N>=500; cadence 2-5/week; each direction >=30%; max year <=30%; every year 1.25-6.50/week; zero conflicts; exact outcome-blind ledger.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_AO_TWIN_PEAKS`. All pass gives `SCREENED_SOURCE_PASS_DIRECT_MQL5_PARITY_CHILD_AUTHORIZED`, permitting only a fresh direct-formula plus native-`iAO` parity child.

No source access may occur before preregistration, analyzer, tests and independent review are registry-bound. No MT5, MQL5, economics, validation, holdout, paper, promotion or live authority is granted.

References:

- https://www.tradingview.com/support/solutions/43000501826/
- https://www.mql5.com/en/docs/indicators/iao
