# Deep Research V6 — Independent MT5 Strategy After V5 Falsification

Use `GPT-5.6 Sol`, `Pro`, and `Nghiên cứu sâu`.

## Your role

Act as a senior quantitative trading researcher, discretionary FX trader, and
MT5/MQL5 systems designer. Search current primary sources and propose a genuinely
new, testable strategy mechanism for a retail MT5 environment. Be skeptical:
return `NO LEGAL CANDIDATE` if the evidence does not support one.

## Objective

Find exactly one top-ranked, independent hypothesis that can plausibly deliver
2–5.5 trades per elapsed calendar week across EURUSD and/or GBPUSD, survives
realistic Bid/Ask costs, uses closed-bar/non-repainting decisions, and can first
be screened by one cheap offline probe over 2018–2025.

The allowed current data surface is:

- MT5 M1/M5/M15/H1 OHLC and tick volume;
- historical Bid/Ask quote ticks and spread;
- multi-symbol bars available in the same terminal;
- deterministic calendar fields known at decision time.

Do not require paid futures/order-book/CLS/segmented customer-flow data, future
calendar values, reconstructed analyst expectations, or live order placement.

## V5 failure packet — immutable facts

Deep Research V5 proposed `Impact-per-Pressure Continuation` using
`q=sign(mid[t]-mid[t-1])` and `Round-Number Release Persistence`.

The round-number candidate was killed at intake as a cosmetic variant of the
failed `S558 / EA_GoldRound` family: rejection PF 0.94; breakout PF 1.20 with
30.7% drawdown.

The Impact-per-Pressure candidate received exactly one frozen EURUSD+GBPUSD M15
probe on 2018–2025, with k=2.7, c=1.5, Nmin=30, stop 0.5x signal move, target 1x,
two-bar time stop, adverse-first same-bar policy, and 1.2-pip round-trip stress.
It was compared with a train-count-matched return-z control.

Observed result:

- 74,178 pooled trades / 177.70 trades per week;
- gross PF 0.598 before stress;
- holdout PF after stress 0.340;
- holdout expectancy -2.011 pips/trade;
- pooled net -158,649.725 pips after stress;
- matched return-control holdout PF 0.404, higher than the candidate;
- all six performance/identity gates failed.

The causal/source error was also confirmed: the cited papers use signed
transactions or participant-classified order flow, while retail FX quote ticks
contained Bid/Ask updates but no Last/Volume/Buy/Sell observations. The V5
statistic was a price-path transform, not independent order flow.

## Prohibited rescue paths

Do not propose any variation of the V5 candidates. Specifically, do not:

- change k/c/Nmin, stop/target/holding time, symbol, side, hour, weekday, or
  cost to rescue Impact-per-Pressure;
- rename the same formula as quote imbalance, pressure, CVD, flow toxicity,
  tick direction, microstructure momentum, directional efficiency, path
  efficiency, or a new indicator;
- use round/psychological levels, clustered-price release, round-number
  breakout, or round-number rejection;
- claim Bid/Ask quote changes are signed institutional order flow.

Also de-duplicate against these closed or exhausted families before proposing:

- benchmark/fix/session-timing reversal or continuation (`S214–S217`, `S532`,
  `S564`, and V2);
- retail flow/tick-volume proxies (`S617`, `S624`, `S625`, `S677`, `S679`);
- liquidity-sweep/ICT/order-block cosmetic variants;
- generic one-indicator RSI/MACD/EMA/ATR/Bollinger/Donchian momentum or mean
  reversion with only threshold/session changes;
- macro-surprise or official-action strategies lacking reconstructable
  real-time expectations/timestamps;
- QFSI/GVBCI/SCFIS ideas whose required external data remains unavailable.

## Required research method

1. Search current primary sources: peer-reviewed papers, central-bank or
   exchange publications, and official MT5 documentation where relevant.
2. State the causal mechanism and why it can survive at M5–H1 retail latency.
3. Map each source variable to an actually available MT5 field. Label every
   proxy and explain why the source evidence transfers; if it does not, reject
   the candidate yourself.
4. Check novelty against every prohibited/closed family above. A new name,
   indicator wrapper, symbol, timeframe, session, or parameter is not novelty.
5. Prefer mechanisms whose expected signal cadence is structurally near the
   2–5.5/week target before any optimization.
6. Design one frozen cheap probe with a matched negative control that tests the
   claimed mechanism rather than merely tests profitability.
7. Use train 2018–2022 and untouched holdout 2023–2025. No post-hoc weekday,
   hour, year, or volatility veto.

## Required output

Return exactly one of:

- `ONE LEGAL CANDIDATE; PROBE EXACTLY THIS`, or
- `NO LEGAL CANDIDATE`.

If there is one candidate, provide:

- name and independent family;
- primary-source URLs and what each source actually proves;
- exact MT5-available inputs and closed-bar formula/pseudocode;
- entry, exit, invalidation, cost, spread, slippage, and same-bar rules;
- expected structural cadence calculation before testing;
- frozen symbols, timeframe, train/holdout, thresholds, and degrees of freedom;
- one mechanism-matched negative control;
- hard sample, cadence, PF, expectancy, drawdown, concentration, and
  beats-control kill gates;
- explicit de-dup table versus V5 and all closed families;
- the strongest reason the hypothesis is likely to fail.

Do not write MQL5 code. Do not recommend optimization. Do not authorize a
registry row, preregistration, EA build, compile, backtest, demo, prop, or live
deployment. The local coordinator alone decides whether a proposal earns one
cheap probe.
