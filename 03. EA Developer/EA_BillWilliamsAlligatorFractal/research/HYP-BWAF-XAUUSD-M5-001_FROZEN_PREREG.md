# HYP-BWAF-XAUUSD-M5-001 - Frozen Bill Williams Alligator-Fractal Breakout Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

Informing evidence is limited to source cadence: exact AO(5,34) M5 Twin Peaks produced `43.09/week`, and exact standard PSAR H1 flips produced `9.58/week`. No price outcome, return, PnL, PF, validation or holdout value informed this object.

## Identity and thesis

- Hypothesis: `HYP-BWAF-XAUUSD-M5-001`
- Family: `bill-williams-alligator-opening-regime-first-fractal-breakout`
- Symbol/timeframe: native FivePercent XAUUSD M5 Bid bars
- Source state: exact inception `2004-06-11T04:15:00Z` through `<2023`
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023-2024 and holdout 2025+ remain sealed
- Sole attempt: `BWAF001-SOURCE-ATTEMPT-001`

TradingView documents the Williams Alligator as three shifted smoothed moving averages of median price and describes Williams Fractal breakouts as more useful when combined with the Alligator to avoid weak, trendless conditions. MetaQuotes exposes the later native-correctness dependencies through `iAlligator` and `iFractals`.

Repository de-dup found no Alligator/Gator object in the canonical registry or failure catalog. Existing fractal objects use sweep/reclaim/retest or close-break/hold/retest mechanics. This object is materially different: one first eligible fractal breakout per newly opened Alligator mouth, with no sweep, reclaim, retest, session, ATR, ADX, volume, threshold or outcome filter.

## Exact direct-formula indicator contract

Use full observed native-M5 history from inception. All rows must have finite `high>=low`, `low<=close<=high`; flat bars are valid. Normal market closures do not reset indicator state and no synthetic bars are inserted.

- median price: `M_t=(high_t+low_t)/2`;
- SMA-seeded SMMA of period `n`: first value at `n-1` is the arithmetic mean of `M_0..M_(n-1)`; thereafter `SMMA_t=((n-1)*SMMA_(t-1)+M_t)/n`;
- displayed Jaw at bar `t`: raw SMMA13 from `t-8`;
- displayed Teeth at bar `t`: raw SMMA8 from `t-5`;
- displayed Lips at bar `t`: raw SMMA5 from `t-3`.

Never read raw line values from `t+shift`. Positive plot displacement means the value displayed at `t` was calculated at the older index `t-shift`.

At completed confirmation bar `c`, center `f=c-2` is a strict upper fractal only when `high[f]` is strictly greater than highs at `f-2,f-1,f+1,f+2`. Lower fractal is the exact strict inverse. Equality never qualifies.

The direct formula controls source acceptance. Native `iAlligator`/`iFractals` buffer parity is a later correctness child only if every source gate passes; no native parity is claimed here.

## Sparse-by-construction state machine

At a completed bar `t`, bullish mouth-open alignment requires `Lips[t] > Teeth[t] > Jaw[t]` and every displayed line strictly higher than its own prior displayed value. Bearish alignment is the exact inverse.

- A fresh bullish regime begins only on transition from not-bullish to bullish alignment. It clears all anchors, records the regime-start index and is unconsumed.
- A fresh bearish regime begins symmetrically. A neutral or broken alignment clears the active regime and all anchors.
- Within a bullish regime, store only the first subsequently confirmed strict upper fractal whose pivot index is not earlier than the regime start and whose `high[f] > Teeth[f]`. Ignore later upper fractals until the regime ends.
- Within a bearish regime, store only the first subsequently confirmed strict lower fractal with `low[f] < Teeth[f]`.
- LONG on the first later completed bar `t>c` whose `high[t]` is strictly above the stored upper-fractal price while bullish alignment still holds.
- SHORT is the exact inverse using `low[t]` strictly below the stored lower-fractal price.
- Equality gives no event. Any event consumes the regime and clears both anchors; no further event is possible until alignment breaks and a fresh regime begins.
- Simultaneous-direction conflict is rejected and consumes both anchors, though strict line ordering should make it impossible.

This one-event-per-new-mouth rule is part of the pre-outcome market thesis, not a cooldown or post-hoc frequency deletion.

## Execution mapping

- source signal uses completed M5 bar `t` only;
- decision exists only at the exact next physical row where both `source_epoch[t+1]=source_epoch[t]+300` and UTC is `t+5 minutes`;
- a raw event without that exact row is consumed and never queued;
- the next row's price is never read.

Forbidden: session/news/time filters, ATR/ADX/volume filters, alternate Alligator periods/shifts, alternate fractal width, delayed confirmation, retest/reclaim, cooldown/debounce, sibling timeframe tournament, stops/targets, outcomes and optimization.

## Frozen source and gates

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- XAUUSD M5 SHA256: `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`
- PyArrow materializes only `time_utc<2023`; scoring uses `[2018,2023)`.

All gates must pass: hashes/one-shot/replay; design rows >=300,000; feature coverage >=99.9%; exact-next >=97%; executable N>=500; cadence 2-5/week; each direction >=30%; max year <=30%; every year 1.25-6.50/week; zero conflicts; exact outcome-blind ledger.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_BW_ALLIGATOR_FRACTAL_REGIME_BREAKOUT`. All pass gives `SCREENED_SOURCE_PASS_DIRECT_MQL5_PARITY_CHILD_AUTHORIZED`, permitting only a fresh direct-formula/native-indicator correctness child.

No source access may occur before preregistration, analyzer, tests and independent review are registry-bound. No MT5, MQL5, economics, validation, holdout, paper, promotion or live authority is granted.

References:

- https://www.tradingview.com/support/solutions/43000592305-williams-alligator/
- https://www.tradingview.com/support/solutions/43000591663-williams-fractal/
- https://www.mql5.com/en/docs/indicators/ialligator
- https://www.mql5.com/en/docs/indicators/ifractals
