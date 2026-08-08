# Five-indicator native MT5 census closeout — 2026-08-08

## Economic decision

- Engineering-valid: **PASS** for the zero-trade M5 and native-M15 census wrappers, deterministic closed-bar exports, compile contracts and non-repaint audits.
- Economic-valid: **FAIL**. Seven preregistered discovery hypotheses produced zero survivor.
- Promotion-ready: **NO**. No 2023+ validation, holdout, paper or live gate was opened.
- Campaign verdict: `FRONTIER_STOP_NATIVE_PRICE_FIVE_INDICATOR_FUSION_NO_EDGE`.

This is not a universal claim that the five indicators are useless. It is a bound verdict: their current causal, closed-bar M5/M15 state, transition and event-acceptance surfaces did not create positive expectancy after observed dynamic costs on the tested FX contracts.

## What was actually tested

The census retained every closed-bar state needed from:

1. **QQE MOD** — secondary trend/RSI, zero/threshold relation and up/down impulses;
2. **Modern Bollinger Bands** — adaptive basis, robust bands, regime, squeeze and S1/S2/S3 events;
3. **AI Regime Detection** — four-state posterior, held regime and confidence;
4. **Volatility Regime Classifier** — Hurst, ADX, CHOP, volatility percentile, direction and composite regime;
5. **TB Smart Money Concept** — structure, displacement, sweep/reclaim, bias and structural levels.

The production EA was not modified to manufacture telemetry. Two zero-trade wrappers exported one row per completed bar. M15 was computed natively; M5 output was never resampled into fake M15 indicator state.

| ID | Symbol / TF | Frozen decision surface | Best discovery result | Verdict |
|---|---|---|---|---|
| HYP-012 | EURUSD M5 | simultaneous five-indicator state, Ridge/HGB, 3/6/12 bars | PF 0.7554, -215.70R | KILL |
| HYP-013 | EURUSD M5 | five-indicator state transitions | PF 0.8207, -114.89R | KILL |
| HYP-014 | USDJPY M5 | pair-native simultaneous state | gross PF 1.3276, but net PF 0.9429 and -56.07R | KILL |
| HYP-015 | USDJPY M15 | native-M15 simultaneous state | PF 0.8623, -111.42R | KILL |
| HYP-016 | USDJPY M15 | all-bar paired first-hit barrier acceptance | PF 0.8766, -40.21R | KILL |
| HYP-017 | USDJPY M15 | MBB S1/S2/S3 rising-edge clock + five-indicator acceptance | PF 0.7948, -80.81R | KILL |
| HYP-018 | USDJPY M15 | TB structure/displacement/sweep rising-edge clock + five-indicator acceptance | PF 0.8571, -60.32R | KILL |

Every hypothesis used expanding-year discovery folds and kept 2023+ sealed. Event types, directions and sessions were not deleted after outcomes. Thresholds targeted a practical 2–5 trades/week; adjacent thresholds were required to remain stable.

## What each indicator contributed

### QQE MOD

QQE supplied useful directional/momentum state but did not become an independent event separator. Its 2022 grouped permutation MSE increase was 0.00336 on EURUSD M5, 0.00589 on USDJPY M5 and 0.00146 on USDJPY M15. The signal is measurable, but small and unstable across pair/timeframe. It must not be double-counted by treating primary and secondary RSI as independent votes.

### Modern Bollinger Bands

MBB was the strongest predictive family on USDJPY: grouped permutation MSE increase 0.01471 on M5 and 0.02119 on M15. Moving from M5 to native M15 also reduced median spread/ATR from 0.0769 to 0.0426. Neither improvement converted into net expectancy. Its 10,941 S1/S2/S3 rising-edge events were stable and balanced, yet the best accepted subset had PF 0.7948. MBB therefore describes geometry/regime well but is not a profitable clock by itself under this contract.

### AI Regime Detection

AIRD had the largest indicator-family diagnostic on EURUSD M5 (MSE increase 0.00704), almost no contribution on USDJPY M5 (-0.00009), then a modest contribution on USDJPY M15 (0.00462). This pair/timeframe instability is exactly why a universal confidence cutoff is unsafe. AIRD is suitable as context telemetry, but no confidence threshold earned economic authority.

### Volatility Regime Classifier

VRC was informative on EURUSD M5 (MSE increase 0.00634) but negative/noisy on USDJPY M5 (-0.00297) and M15 (-0.00561). The volatility state still matters for execution cost—the USDJPY M5 apparent gross edge was consumed by spread/slippage—but VRC regime labels did not reliably identify the profitable subset. It should remain a cost/risk context rather than an extra bullish/bearish vote.

### TB Smart Money Concept

TB state contributed little on USDJPY M5 (0.00021) but more on native M15 (0.00859). Its structural clock was extremely stable: 32,678 events, 125.41/week, 50.44% long, with annual density 122.41–127.26/week. After frozen acceptance, the best 799-trade subset still lost -60.32R at PF 0.8571; all four discovery years were negative. TB structure provides coherent chart annotation and event timing, but the tested direction rules do not forecast enough follow-through to overcome costs.

Grouped permutation values are post-outcome diagnostics of one 2022 fold, not optimization authority. They explain behavior; they cannot justify removing a family or mining a new threshold on this data.

## Pair and timeframe lesson

- **EURUSD M5:** time/regime context carried more model information than structural/momentum families, yet both simultaneous-state and transition models were clearly negative.
- **USDJPY M5:** the raw movement forecast contained weak gross information, dominated by MBB and QQE, but the cost burden was larger than the gross edge.
- **USDJPY M15:** relative cost improved materially and TB/MBB feature contribution increased, but realized first-passage and event-acceptance PF remained below 0.88. Increasing timeframe improved friction, not discrimination.

This is the legitimate pair-specific tuning conclusion: pair/timeframe characteristics changed feature usefulness and cost, but no tested setting crossed the preregistered stability gates. Optimizing the internal lengths/thresholds of five indicators now would select noise from a losing family. Such a grid is intentionally not opened.

## Failure radius and next legal route

Closed:

- majority voting and simultaneous-state scoring;
- indicator transition clocks;
- all-bar barrier classification;
- MBB S1/S2/S3 clocks;
- TB structure/displacement/sweep clocks;
- session, direction, event-type, parameter and threshold rescue on the same census.

The next candidate must introduce a materially new causal information set, ideally quote/order-flow or licensed point-in-time event data with a frozen cost/latency contract. It must begin with a zero-trade source-semantics and cadence probe. More indicator conjunctions, more currency pairs or finer parameter grids on this closed family would increase the multiple-testing count without repairing the missing edge.

## Canonical evidence

- M5 package: `03. EA Developer/EA_RegimeStructureFusionStateCensus/`.
- Native M15 package: `03. EA Developer/EA_RegimeStructureFusionStateCensusM15/`.
- HYP-018 terminal result: `03. EA Developer/EA_RegimeStructureFusionStateCensusM15/research/HYP-RSF-USDJPY-M15-TB-EVENT-ACCEPTANCE-018_RESULT.md`.
- Candidate states: `04. Memory/research/CANDIDATE_REGISTRY.jsonl`.

