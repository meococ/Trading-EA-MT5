# Deep Research V8 — Point-in-Time Carry / Funding Data-Contract Expansion

Use `GPT-5.6 Sol`, `Pro`, and `Nghiên cứu sâu`.

## Your role

Act as a senior quantitative FX researcher, discretionary macro/price trader,
and MT5/MQL5 systems designer. Search current primary sources and challenge the
request aggressively. Return `NO LEGAL CANDIDATE` if public short-term rates
cannot reconstruct the academic carry variable faithfully under the lag,
join, cadence, de-duplication, and cost contract below.

## Owner-authorized scope change

V7 returned `NO LEGAL H4/D1 CANDIDATE` on the retail price/tick-volume/spread
surface. Its primary-source audit ranked carry/funding among the strongest
medium-horizon FX families and rejected it solely for
`REJECT_MISSING_POINT_IN_TIME_CARRY_INPUT`: spot OHLC alone cannot reconstruct
historical interest differentials, forwards, funding, or positioning.

The Owner now authorizes **exactly one** data-contract expansion — and only
this one — after that V7 stop:

> Historically reconstructable **public short-term interest / policy /
> money-market rates** for **USD, EUR, GBP, and JPY**, joined with explicit
> publication lag, vintage rules, and no lookahead.

Do not reopen signed dealer/customer flow, COT/positioning, equity/bond
capital-flow proxies, surprise calendars, or proprietary paid feeds in this
packet. Those remain outside V8. Do not retry a price-only H4/D1 frontier under
a carry label.

## Objective

Find at most **one** legal carry/funding-linked portfolio hypothesis suitable
for a book over unsuffixed `EURUSD`, `GBPUSD`, and `USDJPY`, or return
`NO LEGAL CANDIDATE`.

A legal candidate must:

- decide only from completed **H4 or D1** bars;
- be non-repainting and implementable later in MQL5 without future data;
- derive directional state from a reconstructable public-rate carry
  differential (or a documented lawful money-market proxy that preserves the
  academic causal variable), not from mid-price path transforms;
- plausibly support **2–5 trades per elapsed calendar week** across the pooled
  book after realistic Bid/Ask costs, without weekend exposure under a scalp
  contract;
- be screenable first by **one** frozen cheap offline probe over 2018–2025;
- use no optimization, ML fitting, news prediction, or post-hoc filters;
- grant no EA-build, registry, prereg, compile, or Model 0 authority by itself.

If public series cannot faithfully reconstruct the carry variable used in the
primary sources (wrong tenor, missing lag, revised-only history without
vintage, currency-leg gaps, or forced collapse to spot momentum/rank), return
`NO LEGAL CANDIDATE`. Do not invent a price-only fallback to satisfy the
Owner mandate.

## Allowed data surface (V8 = V7 MT5 surface + one exogenous rates join)

**Still allowed (unchanged from V7 retail MT5):**

- MT5 H1/H4/D1 OHLC and tick volume; H4/D1 may be deterministically aggregated
  from lower bars when timestamps are complete;
- historical Bid/Ask quote ticks and spread for executable-entry/outcome
  reconstruction;
- synchronized bars across `EURUSD`, `GBPUSD`, and `USDJPY` from one broker;
- deterministic calendar fields already known at decision time;
- symbol metadata available in MT5 at test time.

**Newly allowed (Owner expansion — rates only):**

- public short-term **policy rates** and/or **money-market / T-bill / overnight
  reference rates** for USD, EUR, GBP, and JPY from official or widely archived
  free series (central-bank publications, FRED/ALFRED, ECB/BoE/BoJ/Fed/Treasury
  statistical releases);
- only when each series is named with exact URL or archival identifier,
  update frequency, timezone, publication lag, and whether the observation is
  available **before** the chosen closed H4/D1 decision timestamp;
- vintage-aware history when revisions exist (prefer ALFRED or equivalent
  point-in-time vintages; never silently use last-revision as if it were
  contemporaneous).

**Still forbidden / fail-closed:**

- signed transactions, CVD, participant/dealer flow, order-book depth, venue
  queue, or any “flow” proxy built from mid moves or quote ticks;
- futures, options, CLS, analyst expectations, proprietary sentiment/
  positioning, CFTC COT, equity-index or bond-yield capital-flow surfaces
  (not authorized in this packet);
- historically reconstructable **broker swap** tables treated as academic
  carry unless proven identical to the public-rate differential and available
  point-in-time (do not assume);
- current symbol properties as substitutes for historical Bid/Ask costs;
- treating missing commission/slippage provenance as zero cost;
- live order placement.

## Immutable failure and de-dup boundary

Reject cosmetic variants of all of the following:

- V5 `Impact-per-Pressure` and round-number release/rejection; any
  `sign(Δmid)`, efficiency, move-per-tick, or quote-direction “flow” rename;
- V6 news order-flow assimilation, retail spread/liquidity direction, and
  M5–H1 triangular/stale-quote convergence;
- V7 price-only H4/D1 momentum, reversal, trend, pair-rank, consensus,
  compression/breakout, or volatility-gated wrappers — including any that
  merely attach a rate series as garnish while decisions remain driven by
  spot returns;
- benchmark/fix/session-timing reversal or continuation;
- retail tick-volume/order-flow/CVD/toxicity proxies;
- ICT/liquidity-sweep/order-block/FVG renaming;
- generic RSI/MACD/EMA/ATR/Bollinger/Donchian/inside-bar/breakout strategies
  whose novelty is only threshold, timeframe, symbol, or session;
- macro surprise or official action without point-in-time expectations;
- QFSI/GVBCI/SCFIS families whose external data remain unavailable;
- the existing `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`, a frozen M15
  common-USD impulse, strongest-pair router, and pullback-break architecture
  that remains cost-data blocked — do **not** rename it as carry;
- local negative-control / killed families `S555` predictive lead-lag,
  `S618` fixed-target consensus, `S619` cross-asset catch-up, `S621`
  low-frequency basis convergence, `S670` laggard divergence, `S693` H4
  ribbon, and `S694`/`S695` D1 compression.

A slower timeframe, different normalization, pair rank, volatility filter,
trend wrapper, or new indicator name is not an independent mechanism. A carry
claim that reduces, under the stated formula, to ranking recent spot returns
or strongest-USD pairs is a duplicate, not a rates thesis.

## Known local evidence

- V6: `NO LEGAL CANDIDATE` on M5–H1 retail flow/liquidity/latency families.
- V7: `NO LEGAL H4/D1 CANDIDATE`; carry/funding cited as strong but blocked
  without point-in-time rates.
- Workspace portfolio audit: 217 identity-valid non-empty runs across 34 EAs;
  zero jointly meet PF >1.30 and 2–5 trades/week.
- Same-broker commission and independent slippage provenance remain incomplete.
  V8 may design a conservative kill-only cost stress for an initial offline
  probe, but a probe pass **does not** waive broker cost provenance and
  **does not** authorize a meaningful MT5 Model 0 outcome run until that
  provenance is restored.
- Local exogenous rate archives are not assumed present. The research answer
  must specify exact public URLs and join rules; local acquisition is a
  coordinator step after a legal candidate, not a GPT-granted authority.

## Required research method

1. Search primary sources for the carry claim: Menkhoff et al. (*Carry Trades
   and Global Foreign Exchange Volatility*) and closely related peer-reviewed
   / central-bank FX carry literature; official MT5 docs only for
   implementability hygiene, not as evidence of an edge.
2. State what each source actually observed: sampling horizon, currency
   universe, interest/forward variable definition, gross vs net of cost, and
   whether the effect is cross-sectional rank, time-series differential, or
   volatility-conditioned.
3. **Map every academic rate/forward input to exact public series URLs**
   (FRED/ALFRED and/or Fed, ECB, BoE, BoJ, U.S. Treasury) for USD, EUR, GBP,
   and JPY. For each series give:
   - series id / archival path and URL;
   - observation frequency;
   - known publication lag and timezone;
   - vintage rule (first release vs revised);
   - join key to the closed H4/D1 FX decision bar;
   - fail-closed missing-observation rule (no silent forward-fill across
     policy changes unless source-justified and frozen).
4. Explain why the mechanism is **carry differential**, not ordinary price
   momentum, mean reversion, volatility timing, calendar seasonality, or
   pair-ranking under a new label.
5. Calculate expected structural cadence before testing. The pooled portfolio
   must plausibly fall near 2–5 trades/week without an optimized threshold.
   Sparse monthly policy steps alone are insufficient unless the formula
   produces a lawful higher-frequency decision state without lookahead.
6. Design **exactly one** frozen cheap offline probe plus **one**
   mechanism-matched negative control that separates the interest-rate carry
   differential from plain momentum/rank (e.g. identical portfolio rules using
   lagged spot-return ranks or strongest-pair routing with rates zeroed or
   shuffled under a frozen seed). The candidate must beat the control on the
   frozen gates; otherwise kill.
7. Use train 2018–2022 and untouched holdout 2023–2025. Do not inspect holdout
   unless train passes. No hour/day/month/year/pair/direction veto after seeing
   outcomes.
8. Include a degrees-of-freedom count. Prefer source-default constants and at
   most three genuine numeric strategy choices beyond standard lookbacks.

## Required output

Return exactly one headline:

- `ONE LEGAL CARRY/FUNDING CANDIDATE; PROBE EXACTLY THIS`, or
- `NO LEGAL CANDIDATE`.

If one candidate exists, provide:

- name, independent mechanism family, and strongest falsifiable causal claim;
- primary-source URLs (Menkhoff et al. and related) and an evidence-transfer
  table mapping each source variable to the public series URL, lag, and join;
- exact allowed inputs, completed-bar formula, and pseudocode;
- exact portfolio arbitration when more than one of `EURUSD` / `GBPUSD` /
  `USDJPY` signals;
- entry, stop, target, time exit, weekend exit, same-bar ordering, spread,
  commission, and slippage rules (stress-only if provenance incomplete;
  state that Model 0 remains blocked until same-broker cost provenance exists);
- structural cadence calculation before testing;
- frozen symbols, timeframe (H4 or D1 only), train/holdout windows, constants,
  and trial count;
- exactly one mechanism-matched negative control that isolates carry
  differential from plain momentum/rank;
- hard train and holdout gates for sample, cadence, PF, expectancy, drawdown,
  concentration, year stability, and superiority to control;
- explicit de-dup table against V5, V6, V7 locks and
  `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`;
- the strongest reason the candidate will probably fail;
- the minimum evidence that would justify writing an EA after the probe.

If no candidate exists, state which rate families were examined, why each fails
reconstructability, lag, tenor fidelity, cadence, cost, or de-dup, and the
single cheapest lawful data-acquisition step that would reopen research — if
any — without expanding beyond public short-term rates.

## Authority boundary (non-negotiable)

Do not write MQL5 code. Do not recommend optimization. Do not authorize a
registry append, preregistration, EA build, compile, Strategy Tester run,
AlphaFactory Model 0, deployment, or live trading. A GPT Deep Research answer
alone grants **none** of those. The local coordinator alone decides whether one
candidate earns one cheap offline probe and whether a probe survivor earns EA
work after frozen prereg and cost-provenance checks.

## Draft status

`DRAFT / NOT SUBMITTED`. Owner must confirm before Browser -> ChatGPT
submission with UI readback of `GPT-5.6 Sol` + `Pro` + `Nghiên cứu sâu`.
