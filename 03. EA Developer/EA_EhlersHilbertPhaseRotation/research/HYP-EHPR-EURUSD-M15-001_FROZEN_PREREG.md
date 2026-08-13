# HYP-EHPR-EURUSD-M15-001 — frozen source-feasibility preregistration

Status: `FROZEN_SOURCE_FEASIBILITY_ONLY`  
Attempt: `EHPR001-SOURCE-ATTEMPT-001`

## Thesis and novelty boundary

The candidate tests whether a causal estimate of the dominant M15 cycle can
identify alternating trough/peak rotation on EURUSD. It uses Ehlers' Hilbert
homodyne discriminator to estimate phase from completed `HL2` bars, enters at
the next exact M15 open after a phase-bin crossing, and reverses/exits at the
opposite crossing. The market premise is inventory/liquidity rotation in a
cycle-valid state; the first fatal falsifier is that the estimator rails or its
phase crossings cannot form a stable, balanced, executable event population.

This is not the Fisher-extreme + EMA pullback contract, classic Schaff Trend
Cycle MACD-stochastic continuation, AIRQMB/RSF band/regime fusion, or the
generic five-bar/ATR/1.5R/12-bar indicator-transition engine. The exact delta is
`Hilbert I1/Q1 phase bin + opposite half-cycle lifecycle`, with no trend,
session, weekday, direction, news, threshold or indicator-vote filter.

Grok Build rejected the proposal as a broad single-oscillator duplicate and
correctly challenged phase degeneracy and gap handling. The Lead rejects the
blanket de-dup because local terminal verdicts close exact decision surfaces,
not every OHLC transform. The valid engineering objections are frozen here:
phase is unusable when amplitude degenerates or the period rails, unexpected
intraday gaps reset the estimator, and no event may cross a non-exact next-open
boundary. This decision is pre-source and has read no market outcome.

Formula references are specification inputs only, not parity or profitability
evidence:

- local implementation: `06.Indicator Alpha/Modern_Bollinger_Bands_GBB.mq5`;
- MetaQuotes article: `https://www.mql5.com/en/articles/23444`;
- MetaQuotes Sine Wave CodeBase description: `https://www.mql5.com/en/code/577`.

## Frozen source and clock

- Symbol/timeframe: FivePercent `EURUSD`, derived M15 from native M5.
- Source manifest SHA256:
  `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.
- EURUSD M5 Parquet SHA256:
  `6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8`.
- Prehistory read: `[2015-01-01, 2016-01-04)` only for deterministic state.
- DESIGN scored: `[2016-01-04, 2021-01-01)`.
- Validation `2021-2024` and holdout `2025+` remain sealed.
- A derived M15 bar exists only for an exact UTC-aligned M5 triplet at offsets
  `0, 300, 600` seconds. Open=first, high=max, low=min, close=last.
- The indicator advances only on complete derived bars. Scheduled weekend gaps
  pause market-time state; any other gap resets the full estimator and requires
  fresh warm-up. A signal lacking the exact next M15 bar is consumed and cannot
  be shifted.

## Frozen estimator and event

For each completed M15 bar use `HL2=(high+low)/2`.

1. Smooth with `(4*HL2_t + 3*HL2_t-1 + 2*HL2_t-2 + HL2_t-3)/10`.
2. Apply the 7-tap Hilbert FIR at lags `0,2,4,6` with coefficients
   `0.0962, 0.5769, -0.5769, -0.0962`, multiplied by
   `(0.075*prior_period + 0.54)`.
3. Construct Detrender, `I1`, `Q1`, phase-advanced `jI/jQ`, smoothed `I2/Q2`,
   and homodyne `Re/Im` in the same operation order as local GBB.
4. Raw period is `2*pi/atan(Im/Re)` when both are nonzero, otherwise the prior
   period. Apply `0.67x/1.5x` rate limits, clamp `6..50`, smooth `0.2/0.8`, then
   smooth dominant period `0.33/0.67`.
5. After at least 40 valid segment bars, phase is `atan2(Q1,I1)`. It is usable
   only when `sqrt(I1^2+Q1^2)>1e-12`, all values are finite, and dominant period
   is below `42.5` (the local GBB non-railed validity boundary).
6. `Sine=sin(phase)` and `LeadSine=sin(phase+pi/4)`.
7. LONG when prior valid `Sine<=LeadSine` and current valid
   `Sine>LeadSine`. SHORT is the exact inverse. Equality arms but never fires
   without a strict current-side change. No simultaneous direction is valid.

On a deterministic 20-bar unit sine, LONG must occur near the cycle trough and
SHORT near the peak; this synthetic parity fixture contains no market data.

## Source-only acceptance

The single attempt may emit source-side phase/event fields and counts only. It
must not read any post-event price, calculate a return/PnL/PF, simulate a trade,
or open validation/holdout.

All gates must pass:

- source/manifest hashes and selected columns match the frozen contract;
- complete-derived-M15 coverage is at least `99%` of alignable M5 triplets;
- at least `80%` of DESIGN derived bars are estimator-usable;
- raw-event exact-next-open coverage is at least `97%`;
- at least `1,000` executable events total and at least `100` in every DESIGN
  year, providing an estimation sample without imposing a default weekly cap;
- LONG and SHORT are each at least `45%` of executable events;
- no DESIGN year contributes more than `25%` of events;
- zero direction conflicts, nonfinite outputs or event-ledger schema breaches;
- deterministic replay bytes match exactly.

Fail any gate: park this exact phase mapping before MQL5/economics. Pass all:
the attempt may authorize a separately reviewed MQL5 build and one untuned
Model-0 DESIGN baseline, never promotion.

## Provisional economic child contract (sealed until source pass)

- Entry/reversal at the first tick of the exact next M15 bar after a phase
  cross. One owned position; close old direction before opening the opposite.
- Exit/reverse only on opposite phase cross; fail-safe maximum hold freezes
  `ceil(dominant_period_at_entry)` completed bars.
- Protective stop `1.5*ATR14` at entry, no TP/trailing/breakeven/partial exit.
- Risk `0.25%`, daily loss lock `3.5%`, account DD lock `8%`, Friday 20:00
  server flatten and no weekend hold.
- DESIGN baseline gates: PF `>1.30` after report costs, positive expectancy,
  DD `<=8%`, direction/year stability, then x1.5 PF `>=1.25`, x2 PF `>=1.00`.
  Cadence is reported and judged against cost/sample/capacity, not a default
  `2-5/week` rule.

No optimizer, threshold/session/direction selection, same-ID retry, validation,
holdout, paper, promotion or live authority exists at this stage.
