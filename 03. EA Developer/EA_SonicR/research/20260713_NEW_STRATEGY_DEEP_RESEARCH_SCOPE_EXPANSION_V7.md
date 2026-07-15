# Deep Research V7 — H4/D1 Multi-Pair FX Scope Expansion

Use `GPT-5.6 Sol`, `Pro`, and `Nghiên cứu sâu`.

## Your role

Act as a senior quantitative FX researcher, discretionary macro/price trader,
and MT5/MQL5 systems designer. Search current primary sources and challenge the
request aggressively. Return `NO LEGAL CANDIDATE` if no mechanism survives the
data, causality, cadence, and local de-duplication contract.

## Owner-authorized scope change

The previous V6 frontier was limited to retail MT5 mechanisms expected to work
at M5–H1 latency. It correctly returned `NO LEGAL CANDIDATE`: the closest
families required signed/participant order flow, dealer/venue liquidity state,
or tick/sub-second triangular-arbitrage latency.

The Owner now explicitly asks research and EA development to continue. This V7
packet therefore opens one genuinely different frontier instead of retrying
V6: medium-horizon, closed-bar, multi-pair FX mechanisms at H4 or D1. A legal
candidate must derive its causal state from information actually observable at
that horizon; it may not disguise unavailable microstructure data as a slower
price indicator.

## Objective

Find exactly one top-ranked independent hypothesis suitable for a portfolio EA
over unsuffixed `EURUSD`, `GBPUSD`, and `USDJPY` that can plausibly produce
2–5 trades per elapsed calendar week across the pooled book, after realistic
Bid/Ask costs, without weekend exposure.

The candidate must:

- decide only from completed H4 or D1 bars;
- be non-repainting and implementable in MQL5 without future data;
- use a medium-horizon economic/behavioral mechanism supported by primary
  evidence at a compatible sampling horizon;
- be screenable first by one cheap offline probe over 2018–2025;
- use no optimization, ML fitting, news prediction, or post-hoc filters;
- have a path to an EA, but grant no EA-build authority by itself.

## Allowed data surface

- MT5 H1/H4/D1 OHLC and tick volume; H4/D1 may be deterministically aggregated
  from lower bars when timestamps are complete;
- historical Bid/Ask quote ticks and spread for executable-entry/outcome
  reconstruction;
- synchronized bars across `EURUSD`, `GBPUSD`, and `USDJPY` from one broker;
- deterministic calendar fields already known at decision time;
- symbol metadata available in MT5 at test time.

Do not require or silently assume:

- signed transactions, CVD, participant/dealer flow, order-book depth, venue
  queue position, or sub-second latency;
- futures, options, CLS, analyst expectations, economic-release surprises, or
  proprietary sentiment/positioning;
- historically reconstructable swap/carry, funding, or interest-rate series
  unless the exact lawful point-in-time source is identified and can be joined
  without lookahead;
- current symbol properties as substitutes for historical costs;
- live order placement.

## Immutable failure and de-dup boundary

Reject cosmetic variants of all of the following:

- V5 `Impact-per-Pressure` and round-number release/rejection;
- V6 news order-flow assimilation, retail spread/liquidity direction, and
  M5–H1 triangular/stale-quote convergence;
- benchmark/fix/session-timing reversal or continuation;
- retail tick-volume/order-flow/CVD/toxicity proxies;
- ICT/liquidity-sweep/order-block/FVG renaming;
- generic RSI/MACD/EMA/ATR/Bollinger/Donchian/inside-bar/breakout/moving-average
  strategies whose novelty is only threshold, timeframe, symbol, or session;
- macro surprise or official action without point-in-time expectations and
  exact timestamps;
- QFSI/GVBCI/SCFIS families whose external data remain unavailable;
- the existing `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`, which is a frozen M15
  common-USD impulse, strongest-pair router, and pullback-break architecture;
- local negative-control families `S555` predictive lead-lag, `S618` fixed-
  target consensus, `S619` cross-asset catch-up, `S621` low-frequency basis
  convergence, and `S670` laggard divergence.

A slower timeframe, different normalization, pair rank, volatility filter,
trend wrapper, or new indicator name is not an independent mechanism.

## Known local evidence

- The workspace portfolio audit contains 217 identity-valid non-empty runs
  across 34 EAs. Zero jointly meet PF >1.30 and 2–5 trades/week.
- Existing H4/D1 and generic trend/breakout EAs in the local catalog are not
  evidence that a newly named technical wrapper is novel.
- The existing M15 cross-sectional USD-factor idea remains cost-data blocked
  and may not be restated at H4 as the V7 answer.
- Same-broker commission and independent slippage provenance remain incomplete.
  V7 may design a conservative kill-only cost stress for an initial offline
  probe, but a pass cannot promote or authorize a meaningful MT5 outcome run
  until broker-specific cost provenance is restored.

## Required research method

1. Search primary sources only for the causal claim: peer-reviewed papers,
   central-bank/exchange publications, and official MT5 documentation.
2. State what each source actually observed, its sampling horizon, asset class,
   data vintage, and whether the effect is gross or net of implementation cost.
3. Map every source variable to an allowed field. Mark any proxy. Reject the
   candidate if the proxy changes the causal variable rather than measuring it.
4. Explain why the mechanism should survive H4/D1 retail latency and why it is
   not ordinary price momentum, mean reversion, volatility timing, or calendar
   seasonality under a new label.
5. Calculate expected structural cadence before testing. The pooled portfolio
   must plausibly fall near 2–5 trades/week without an optimized threshold.
6. Design exactly one frozen cheap offline probe plus one mechanism-matched
   negative control. The control must distinguish the claimed mechanism from a
   generic return, trend, volatility, or pair-ranking effect.
7. Use train 2018–2022 and untouched holdout 2023–2025. Do not inspect holdout
   unless train passes. No hour/day/month/year/pair/direction veto after seeing
   outcomes.
8. Include a degrees-of-freedom count. Prefer source-default constants and at
   most three genuine numeric strategy choices beyond standard lookbacks.

## Required output

Return exactly one headline:

- `ONE LEGAL H4/D1 CANDIDATE; PROBE EXACTLY THIS`, or
- `NO LEGAL H4/D1 CANDIDATE`.

If one candidate exists, provide:

- name, independent mechanism family, and strongest falsifiable causal claim;
- primary-source URLs and an evidence-transfer table;
- exact allowed inputs, completed-bar formula, and pseudocode;
- exact portfolio arbitration when more than one symbol signals;
- entry, stop, target, time exit, weekend exit, same-bar ordering, spread,
  commission, and slippage rules;
- structural cadence calculation before testing;
- frozen symbols, timeframe, train/holdout windows, constants, and trial count;
- exactly one mechanism-matched negative control;
- hard train and holdout gates for sample, cadence, PF, expectancy, drawdown,
  concentration, year stability, and superiority to control;
- explicit de-dup table against V2–V6, the existing M15 cross-sectional factor,
  and the listed local controls;
- the strongest reason the candidate will probably fail;
- the minimum evidence that would justify writing an EA after the probe.

Do not write MQL5 code. Do not recommend optimization. Do not authorize a
registry append, preregistration, EA build, compile, Strategy Tester run,
deployment, or live trading. The local coordinator alone decides whether one
candidate earns one cheap probe and whether a probe survivor earns EA work.
