# HYP-BKSR-XAUUSD-M5-001 - Frozen H1 Bollinger-Keltner Squeeze Release / M5 Decision Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

Informing evidence is limited to opportunity-clock failures: exact Alligator-Fractal M5 produced `14.44/week`; exact PSAR H1 produced `9.58/week`; the terminal Supertrend trade lane exposed non-authoritative diagnostics grossly below target and is not being recovered. No BKSR signal count, price outcome, return, PnL, PF, validation or holdout value informed this object.

## Identity and market thesis

- Hypothesis: `HYP-BKSR-XAUUSD-M5-001`
- Family: `h1-bollinger20x2-inside-keltner20x1p5-release-m5-decision`
- Trading lane: XAUUSD M5 EA using completed H1 setup bars and exact M5 decision clock
- H1 source state: exact native inception `2004-06-11T04:00:00Z` through `<2023`
- M5 clock state: exact native inception `2004-06-11T04:15:00Z` through `<2023`
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023-2024 and holdout 2025+ remain sealed
- Sole attempt: `BKSR001-SOURCE-ATTEMPT-001`

The thesis is volatility contraction followed by expansion, not another directional oscillator cross. TradingView documents that Bollinger contraction commonly precedes expansion, with standard BB parameters 20-period SMA and two population-standard-deviation bands. TradingView documents the modern Keltner Channel as a moving-average basis plus ATR envelopes. The frozen composite treats a strict BB-inside-KC cluster as contraction and emits only on its first release bar.

Canonical registry de-dup found zero Bollinger-Keltner, BBKC or squeeze-release hypotheses. This is materially different from compression breakouts that use fixed range thresholds, fractal sweeps/retests, Supertrend flips or oscillator polarity.

## Exact direct-formula H1 contract

Use every observed native H1 bar from inception. Normal closures do not reset indicator state and no synthetic bars are inserted. Every H1 row must have finite `high>=low`, `low<=close<=high`; flat bars are valid.

- BB basis at `t`: arithmetic mean of the last 20 closes.
- BB deviation: population standard deviation `sqrt(mean((close-basis)^2))` over the same 20 closes.
- BB upper/lower: `basis +/- 2*deviation`.
- KC basis: EMA20 of close, SMA-seeded at index 19; thereafter `EMA_t = EMA_(t-1) + (2/21)*(close_t-EMA_(t-1))`.
- True range: at bar 0, `high-low`; later `max(high-low,abs(high-prev_close),abs(low-prev_close))`.
- ATR20: Wilder RMA, SMA-seeded from the first 20 TR values; thereafter `ATR_t=(19*ATR_(t-1)+TR_t)/20`.
- KC upper/lower: `EMA20 +/- 1.5*ATR20`.
- `squeeze_on[t]` iff `BB_lower[t] > KC_lower[t]` and `BB_upper[t] < KC_upper[t]`, both strict. Equality is off.

The direct formula controls source acceptance. A later correctness child may compare direct BB/EMA/ATR values to MT5 `iBands`/`iMA`/`iATR`, but no native parity is claimed here.

## Exact release state machine

- A squeeze cluster begins on the first `squeeze_on` bar and remains active through consecutive squeeze-on bars.
- Only the first completed H1 bar after an active cluster for which `squeeze_on` is false is the release bar. The cluster is consumed immediately.
- LONG iff release-bar close is strictly above its current BB basis.
- SHORT iff release-bar close is strictly below its current BB basis.
- Equality consumes the cluster without an event.
- No minimum squeeze duration, intensity threshold, direction filter, breakout threshold, retest, persistence, cooldown or debounce exists.

## M5 decision mapping

For H1 source bar `t`, the decision clock is `t+1 hour`. An event is executable only if the frozen native M5 clock has one row with both:

- `time_utc == H1_time_utc + 1 hour`;
- `M5_source_epoch == H1_source_epoch + 3600`.

A raw event lacking that exact M5 row is consumed and never queued. Only M5 timestamp and source epoch are read; no M5 price and no post-event H1 price is read.

Forbidden: session/news filters, volume/ADX/RSI/MACD filters, alternate periods/multipliers, squeeze-duration/intensity thresholds, extra breakout confirmation, retest/reclaim, cooldown, stops/targets, outcomes and optimization.

## Frozen source and gates

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- XAUUSD H1 SHA256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`
- XAUUSD M5 SHA256: `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`
- PyArrow materializes only `time_utc<2023`; scoring uses `[2018,2023)`.

All gates must pass: hashes/one-shot/replay; H1 design rows >=25,000; H1 feature coverage >=99%; raw-event exact-M5-decision coverage >=97%; executable N>=500; cadence 2-5/week; each direction >=30%; max year <=30%; every year 1.25-6.50/week; zero conflicts; exact outcome-blind ledger.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_BBKC_SQUEEZE_RELEASE`. All pass gives `SCREENED_SOURCE_PASS_DIRECT_MQL5_PARITY_CHILD_AUTHORIZED`, permitting only a fresh direct-formula/native-indicator correctness child.

No source access may occur before preregistration, analyzer, tests and independent review are registry-bound. No MT5, MQL5, economics, validation, holdout, paper, promotion or live authority is granted.

References:

- https://www.tradingview.com/support/solutions/43000501840-bollinger-bands-bb/
- https://www.tradingview.com/support/solutions/43000502266-keltner-channels-kc/
- https://www.mql5.com/en/docs/indicators/ibands
- https://www.mql5.com/en/docs/indicators/ima
- https://www.mql5.com/en/docs/indicators/iatr
