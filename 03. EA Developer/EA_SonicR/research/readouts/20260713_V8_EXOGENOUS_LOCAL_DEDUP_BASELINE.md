# V8 Exogenous Local De-Dup Baseline — 2026-07-13

Status: `BASELINE_FROZEN_PRE_RESULT / NO_AUTHORITY`

## Purpose

This memo freezes the local family boundary **before** any Deep Research V8
ChatGPT result is read. It prevents a later proposal from gaining novelty by:

- renaming a V2–V7 killed price-only family and attaching an exogenous label;
- reducing a claimed carry/funding/positioning/capital-flow mechanism to
  spot OHLC, tick volume, spread, or calendar clocks already falsified;
- resurrecting `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` under a new name;
- treating V7's "needs exogenous data" finding as authorization to probe or
  build.

It does **not** inspect V8 outcomes, declare any exogenous candidate legal,
authorize an offline probe, registry row, preregistration, EA source, compile,
or Strategy Tester run.

## Binding inputs (pre-result only)

| Artifact | Role |
|---|---|
| `03. EA Developer/EA_SonicR/research/20260713_NEW_STRATEGY_DEEP_RESEARCH_DATA_CONTRACT_V8.md` | Owner-authorized data-contract expansion packet |
| `03. EA Developer/EA_SonicR/research/readouts/20260713_DEEP_RESEARCH_V7_COORDINATOR_AUDIT.md` | V7 stop: strongest families need carry/funding/positioning or external capital-market series |
| `03. EA Developer/EA_SonicR/research/readouts/20260713_V7_H4_D1_LOCAL_DEDUP_BASELINE.md` | Pre-result price-only H4/D1 family lock |
| `03. EA Developer/EA_SonicR/research/readouts/20260713_DEEP_RESEARCH_V6_COORDINATOR_AUDIT.md` | Flow/liquidity/latency near-miss stop |
| `03. EA Developer/EA_SonicR/research/readouts/20260713_IMPACT_PRESSURE_PROXY_PROBE_READOUT.md` | V5 Impact-per-Pressure kill at offline probe |
| `03. EA Developer/EA_SonicR/research/readouts/20260713_DEEP_RESEARCH_V5_COORDINATOR_INTAKE.md` | Round-number duplicate kill; proxy-mismatch audit |
| `03. EA Developer/EA_SonicR/research/readouts/20260713_DEEP_RESEARCH_V2_COORDINATOR_AUDIT.md` | Fix/benchmark family kill |
| `03. EA Developer/EA_SonicR/research/readouts/20260713_DEEP_RESEARCH_V3_COORDINATOR_AUDIT.md` | Macro/official-action frontier stop under prior contract |
| `02. AlphaFactory/STRATEGY_LOG.md` | Local near-miss / killed EA catalog |
| `03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl` | Existing nonterminal USD-factor idea row |

Conversation or result URLs for V8 are **out of scope** for this baseline.
Any later intake must compare the frozen map below against the report after
this file's hash identity is established in the coordinator audit.

---

## A. Hard-closed killed families (V8 must reject as duplicates)

Any V8 proposal that is mechanically the same family under a new timeframe,
pair set, exogenous garnish, threshold, or portfolio wrapper is
`KILL_AT_INTAKE_DUPLICATE` (or `KILL_AT_INTAKE_PROXY_MISMATCH` if it only
pretends to use exogenous data).

### A1. Price-only / retail-MT5 families already closed (V2–V7 + local)

| Locked family | Canonical local evidence | V8 reject rule |
|---|---|---|
| Europe / WMR fix–benchmark fade or post-fix reversal | `S214–S217`, `S532 / EA_FixFade` (965t, PF 0.87), `S564 / EA_PostFixRevert` (1905t, PF 0.85); V2 coordinator `KILL_AT_INTAKE_DUPLICATE`; V3 failure packet locks entire fix/benchmark/session-timing family | No fix-window, benchmark-calendar, or post-fix fade/continuation dressed as “macro” or “carry.” |
| Gold / FX round-number release or persistence | `S558 / EA_GoldRound`; V5 intake `KILL_AT_INTAKE_DUPLICATE` | Symbol switch (XAU→EUR/GBP/JPY) or H4/D1 bar does not create novelty. |
| Impact-per-pressure / price-path “flow” proxy | V5 probe `KILL_AT_OFFLINE_PROBE`: 74,178 trades, gross PF 0.598, holdout stress-B PF 0.340, lost to matched return-z control | Any `sign(Δmid)`, efficiency, move-per-tick, or return-shock rename is closed. |
| Retail tick-volume / M1 microstructure “institutional flow” | `S624` PF 0.94; `S625` PF 1.04→0.78 decay; STRATEGY_LOG invalidation of pure tick-volume flow; V6 `REJECT_PROXY_MISMATCH` | Tick volume, spread compression, or quote-count acceleration ≠ signed dealer/customer flow. |
| News / event clock without reconstructable surprise | V3 `NO LEGAL CANDIDATE`; `S703 / EA_NewsMomentum` sparse then PF collapse at larger N; local pre-announcement drift negative after 2 bps haircut | Calendar timestamps alone remain illegal; surprise-less event momentum/fade is closed. |
| H4 ribbon / MA pullback trend | `S693 / EA_H4Ribbon` PF 0.87 | Exogenous series cannot be a cosmetic wrapper on EMA/ribbon pullback. |
| D1 / H1 inside-day or compression breakout | `S694` PF 0.83 (20t); `S695` 1 trade; `S232/S235/S237` cadence fail | Compression/inside-bar family stays closed. |
| Autocorrelation / regime switch (momentum vs mean-reversion) | `S548 / EA_ACF` PF 0.88, DD 100% | ACF/Hurst/entropy switches are not a new exogenous mechanism. |
| Choppiness / ATR / RV-gated generic trend | `S628`, `S629` and weekday/session filter descendants | Volatility gates on ordinary trend ≠ independent thesis. |
| Multi-pair consensus / common-currency direction / pair ranking | `S618 / EA_MultiJPY` PF 1.02; CrossLead `S555`; V7 baseline | Consensus, strongest-pair routing, or rank-from-spot-returns is closed as novelty. |
| Predictive lead-lag / laggard catch-up (price-only) | `S619` DXY–gold catch-up PF 0.86; `S670` divergence PF 0.95; USD-factor prereg negative controls | Leader/laggard ordering from spot returns alone is closed. |
| Low-frequency cross-market / basis convergence without venue data | `S620/S621 / EA_COMEXRevert` PF 0.87 / 1.04; V4 GVBCI cost-quote-only, not strategy | CFD gap/basis fade is not lawful venue basis. |
| Cross-day same-interval momentum | `S689` PF 0.22; `S690` implementation-contaminated | Calendar-aligned interval momentum stays closed. |
| Open-range / session breakout as “new” H4/D1 edge | `S678` PF 1.14 with blockers; `S691` PF 0.95 | Wider bar or different session ≠ new causal state. |
| Asian-range manipulation / London reclaim | EUR London Asian Manip V1 offline kill (cost PF ~1.08, year concentration fail) | Range-sweep/reclaim family stays closed. |
| Dragon / Trend distance or EMA-channel vetoes | `S360` Dragon invalidated; XAU S1 Dragon compression / micro-structure / HTF velocity offline kills | EMA34/89 distance or Dragon channel as decision logic stays closed. |
| ICT / FVG / order-block cosmetic renames | Exhausted SilverBullet/Sonic pattern mining under current gates; not reopened by V8 | Pattern taxonomy rename without new exogenous causal variable is duplicate. |
| Generic RSI / MACD / EMA threshold mining | Repeated STRATEGY_LOG invalidations of indicator threshold mining | Parameter mining on closed-bar price indicators is not V8 novelty. |
| Triangular parity / stale-quote / sub-second latency | V6 `REJECT_TIMESCALE_MISMATCH` | M15–D1 closed-bar cannot host tick-latency arbitrage. |
| Liquidity-shock directional from retail spread | V6 `REJECT_UNOBSERVABLE_CAUSAL_STATE`; STRATEGY_LOG spread-compression invalidation | Retail spread is not CLS/dealer liquidity state. |

### A2. Existing registry idea that must not be renamed

| ID | State | V8 rule |
|---|---|---|
| `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` | `idea` / cost-data blocked | Remains a **separate** cost-provenance problem. V8 may not rename common-USD rank/pullback/break architecture as a “carry,” “COT,” or “risk-on” candidate. If the only remaining work is unblocking that idea’s cost contract, return `NO LEGAL CANDIDATE` and say so. |

### A3. Still unavailable causal surfaces (not “allowed” by V8 expansion)

These remain fail-closed even under V8. They are not investigation families for
this packet unless the Owner later supplies possession proof:

- signed dealer/customer flow, CVD, order-book depth, venue queue;
- proprietary paid feeds without a named free/lawful reconstructable substitute;
- synthesizing ask high/low from one bar spread; treating missing cost as zero;
- tester-zero slippage as live execution proof;
- V4 QFSI live target-broker evidence (still `DATA_NOT_READY` /
  `STOP_DATA_FRONTIER`); SCFIS remains excluded without segmented customer flow.

---

## B. Allowed exogenous families to **investigate** under V8

“Allowed to investigate” means Deep Research may examine primary sources and
data contracts in these buckets. It does **not** mean any bucket is legal,
probe-ready, cadence-viable, or de-duplicated. No candidate in these families
is pre-cleared.

| Investigation bucket | Packet-allowed surface | Hard intake constraints (still fail-closed if violated) |
|---|---|---|
| B1. Point-in-time short-term interest / policy / OIS–T-bill differentials | Official or widely archived public G3 series (e.g. central-bank policy rates, FRED, ECB/BoE/BoJ statistical releases) | Exact URL/archive ID, release lag, timezone, pre-bar availability, missing-obs fail-closed, license. Spot OHLC alone is insufficient (V7 carry reject). |
| B2. Reconstructable FX forward points / implied carry | Free lawful archive with timestamps | Same reconstructability/lag/join rules. Must not collapse to spot-only momentum or USD-factor ranking. |
| B3. Delayed positioning (CFTC COT or equivalent) | Public delayed positioning with **exact publication lag honored** (no same-day peek) | Lag must be point-in-time; COT “as of” vs “released” confusion = lookahead kill. Weekly cadence must still show a structural path to 2–5 trades/week or fail honestly. |
| B4. Synchronized public equity-index or bond-yield differentials | Capital-flow / risk-on proxies with point-in-time closes and FX-session alignment rules | Must be mechanistically independent of `S619` price-only DXY–gold catch-up and of USD-factor rank/pullback. Synchronization and lag must be specified. |
| B5. Official economic-calendar timestamps **only with** reconstructable pre-release expectation / surprise | Calendar + expectation surface | Calendar-only or post-hoc surprise reconstruction from the same price path remains V3-closed. |

### Explicit non-claims

- No bucket above is declared to have a lawful, historically complete, joinable
  series in this workspace yet.
- No bucket is declared to survive North-Star PF, cadence, cost-stress, or
  holdout gates.
- No bucket authorizes a cheap offline probe, analyzer, registry append,
  prereg, MQL5 code, compile, or backtest.

---

## C. Coordinator intake rules (apply after V8 result is read)

A V8 proposal passes **local de-dup intake** only if all are true:

1. **Exogenous causal variable:** the claimed driver is one of B1–B5 with a
   named series contract (source, lag, join key, fail-closed missingness), not
   a transform of spot OHLC / tick volume / spread / event clock alone.
2. **Not a locked family:** it is not any row in Section A under a new
   timeframe, pair, threshold, exogenous garnish, or portfolio wrapper.
3. **Independent of USD-factor architecture:** it is not a rename of
   `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`.
4. **No lookahead:** decision uses only information available before the
   chosen closed bar’s decision time under the stated timezone/lag rules.
5. **Negative control design stated:** the probe plan must isolate the
   exogenous claim from ordinary return, trend, volatility, calendar, and
   pair-ranking effects.
6. **Authority hygiene:** the research text itself grants no compile/backtest
   authority.

Failure of any condition → `KILL_AT_INTAKE_DUPLICATE_OR_CAUSAL_MISMATCH` /
`NO LEGAL CANDIDATE` as appropriate. Passing intake still does **not**
authorize probe/code until a separate coordinator freeze says so.

---

## D. Authority boundary

Until a post-result coordinator audit explicitly opens the next step:

- no candidate-registry append;
- no hypothesis_id minting treated as build-ready;
- no preregistration freeze;
- no analyzer / offline probe implementation;
- no MQL5 source or include change;
- no MetaEditor compile or Strategy Tester run;
- no claim that GOAL is met or that an EA is production-ready.

Owner mandate for autonomous push expands **lawful research effort** under
this data contract; it does **not** waive scientific falsification, de-dup,
cost provenance, or closed-bar/non-repaint rules.

---

## E. Status

`BASELINE_FROZEN_PRE_RESULT / NO_AUTHORITY`
