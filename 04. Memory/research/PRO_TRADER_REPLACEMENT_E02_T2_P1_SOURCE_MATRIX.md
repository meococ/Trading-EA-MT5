# T2 P1 Source-to-Requirement Matrix

Status: `P1_SOURCE_RESEARCH_COMPLETE / P2_FORMALIZATION_REQUIRED /
NO_BUILD_OR_OUTCOME_AUTHORITY`  
Campaign: `CAMPAIGN-PTR-E01` · Generation: `T2`  
Bound charter:
`PRO_TRADER_REPLACEMENT_E02_T2_P0_CHARTER.json`, SHA256
`D63F782926DEC4F12EA8EBB17B3511BC08C249A0AE4ECD9C1F25F5C611386E9E`.

This is research evidence, not a second campaign plan. It records what the
sources support, what T2 adapts and what must not be claimed. It grants no
hypothesis, source-code, MT5, economic, validation, holdout, paper or live
authority.

## 1. Source register and evidence grade

| ID | Source | Grade and permitted use |
|---|---|---|
| `S1` | Bob Volman, author-hosted [Understanding Price Action page](https://upabook.wordpress.com/) and [free official excerpt](https://upabook.wordpress.com/wp-content/uploads/2014/09/excerpts-upa.pdf) | Primary lawful source for the second-book five-minute framework, chapter/setup inventory and the author's explanation of pressure, buildup, barriers, pullbacks, EMA25, round levels and trade skipping. It is an excerpt, not the full book. |
| `S2` | Bob Volman, author-hosted [Forex Price Action Scalping page](https://infofpas.wordpress.com/) and [free official excerpt](https://infofpas.wordpress.com/wp-content/uploads/2011/10/excerpts-fpas-hr-3-6-121.pdf) | Primary lawful source for the separate first-book fast 70-tick contract. It is a comparison boundary only; T2 does not implement it. |
| `S3` | MetaQuotes [Strategy Tester tick-generation reference](https://www.mql5.com/en/docs/runtime/testing) and [generated-vs-real-tick article](https://www.mql5.com/en/articles/2612) | Official platform authority for Model-0 limitations. It supports completed-bar/next-open claims, not ordered real-tick or stop-entry fidelity. |
| `S4` | Carol Osler, [New York Fed Staff Report 150](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf) | Research support for the plausibility that clustered stop/limit orders around technical or round levels can affect FX price dynamics. It does not prove T2, XAU or BTC edge. |
| `S5` | Cont, Kukanov and Stoikov, [order-flow imbalance paper](https://arxiv.org/abs/1011.6402) | Research support that short-horizon order-flow imbalance can relate to price changes in limit-order-book markets. T2 has no order book, so OHLC `pressure` is only a path proxy. |
| `C1` | [Forex Factory Volman 70-tick thread](https://www.forexfactory.com/thread/578183-volman-style-70-tick-chart), [five-minute notes thread](https://www.forexfactory.com/thread/733640-understanding-price-action-by-bob-volman-notes-and), and [five-minute community summary](https://www.forexfactory.com/thread/post/14385709) | Community discovery only: terminology, disagreement, feed/timeframe adaptation and failure modes. No authoritative definition or profitability claim. |
| `C2` | [Reddit tick-chart discussion](https://www.reddit.com/r/Forex/comments/15he7bt) and related price-action discussions | Community discovery only. Useful for platform and discretion questions, never evidence of edge. |

No pirated book mirror, third-party PDF or copied chart is an admissible T2
source. A lawfully available full copy is still required before a claim of
complete book-to-code coverage; until then the implementation claim remains
`Volman-inspired`.

## 2. Requirement matrix

| Source proposition | Evidence | T2 machine requirement | Explicit non-claim / falsifier |
|---|---|---|---|
| The second book analyzes EURUSD on a five-minute chart and separately lists pattern break, pattern-break pullback, pattern-break combi, pullback reversal, skipping and breaks-for-failure. | `S1`, official table of contents and excerpt context. | T2 primary/economic timeframe is M5. The economic family may contain PB, PBC and PR plus a full union policy; PBP/retest is excluded because of the local SCC failure radius, and trade-for-failure remains outside the family. | No M15, 70-tick, PBP or failure-fade outcome can be introduced into T2 after exposure. Source inclusion does not require testing a locally duplicated mechanism. |
| The first book's scalping examples use a fast 70-tick chart. | `S2`; `C1` illustrates feed/platform disagreement. | Keep the first-book contract reference-only. A genuine later 70-tick test must freeze tick event type, quote side, duplicates, reconnect/gap behavior and ordered broker-tick availability under a fresh generation. | Model 0, M1 OHLC or interpolated ticks cannot substantiate 70-tick fidelity. |
| Pattern lines and boxes are visual aids; line placement contains discretion, while a bar break is more objective. | `S1`. | Replace discretionary drawing with an immutable barrier identity derived only from already confirmed completed bars. Freeze search window, clustering, tolerance, lock time, expiry and tie-break in P2. Trigger only from a completed-bar rule and enter at the next M5 open. | A barrier moved after seeing the break, a future-confirmed zigzag or an intrabar perforation invalidates the object. The resulting rule is a project adaptation, not the author's exact drawing. |
| Favorable breaks are discussed in the context of pressure, buildup/tension and room; unsupported or extended breaks may fail. | `S1`; `S4` provides only an FX plausibility bridge. | Preserve order and duration in a finite-state grammar: locked barrier → pressure/correction → buildup or reversal → completed trigger → enter/skip. Log every transition and reject reason. Matched A0 removes pressure/buildup/room so incremental value can be tested. | OHLC pressure is not actual order flow. If shuffled event order performs semantically the same or T2 candidate identities mostly reproduce ECRS, the mechanism fails before build. |
| A pullback around 40–60 percent can coincide with EMA25 and prior technical structure, but the average alone is not support or resistance. | `S1`. | PR requires a causal preceding leg, frozen 40–60 percent correction, EMA25-or-pre-existing-structure contact, loss of counter-pressure and completed directional release. EMA25-only remains a non-selectable diagnostic. | EMA25 touch alone can neither trade nor promote. Post-outcome changes to depth, EMA length or structure are forbidden. |
| Small blocks, repeated tests, higher lows/lower highs and contraction can increase pre-break tension. | `S1`. | P2 must define touch identity, minimum separation, contraction, overlap and directional-extrema progression dimensionlessly with ATR14 known at decision time. Barrier and buildup fixtures must pass prefix invariance. | A generic ER/compression/range-break reconstruction is duplicate ECRS surface. Exact ECRS trigger overlap is measured outcome-blind before P5. |
| Inside-bar hesitation can form a combi setup. | `S1`; `C1` only helps identify ambiguity. | PBC requires a fully completed mother/pressure bar, a fully completed inside bar and a later completed release under a frozen ordering and containment rule. | Same-bar or intrabar entry, hindsight choice of the mother bar, or relaxed containment after outcomes invalidates PBC. |
| Round levels may behave as magnets or obstacles. | `S1`; `S4` supports FX clustering plausibility. | Round-grid distance starts as telemetry. A universal train-only order-of-magnitude grid across FX, XAU and BTC must be defined before it can become a feature; it is never hand-picked per symbol. | Source evidence does not establish a profitable round-number rule, and Osler does not establish XAU/BTC transfer. If a universal scale fails, the field stays telemetry-only. |
| Trade quality includes the option to skip ambiguous or obstructed breaks. | `S1`. | `AMBIGUOUS` and exact `SKIP_REASON` enums are first-class outputs. Missing/gapped bars, stale barrier, direction conflict, cost unavailable, excessive cost/R or insufficient opposing room produce deterministic abstention. | Free-text hindsight, discretionary manual exit and outcome-derived vetoes are forbidden. Lower DD from fewer trades is not incremental edge. |
| The book demonstrates consecutive sessions rather than only isolated examples. | `S1`. | T2 reports all available MT5 history, the 2018-current intersection and chronological train/calibration/validation/OOS/T2-holdout for every mandatory symbol. No chart case selects a market outcome. | Source examples are education, not backtest proof. A pretty casebook cannot override PF, cadence, cost, robustness or all-nine no-skip gates. |
| Original tactics include price passing a signal bar and examples with pip-based bracket geometry. | `S1`; community summaries are secondary. | T2 deliberately adapts to completed-close trigger, next-M5-open entry and completed-close +2R/-1R/12-bar exits to make the primary Model-0 claim independent of intrabar order. | T2 is not a faithful stop-entry/bracket execution and cannot claim the original fixed-pip geometry across FX, XAU and BTC. |

## 3. Community findings used only as adversarial questions

- Traders disagree on setup names and whether buildup, traffic and room are
  sufficient. Therefore two independent outcome-hidden raters and a disjoint
  reliability set are capability gates, not decoration.
- Community users switch between 70, 100, 240-tick and five-minute charts and
  between EURUSD, gold and other instruments. Therefore no chart/feed setting
  or coefficient transfers silently across symbols.
- Recent community reports describe reduced opportunity density and subjective
  execution. Therefore T2 must pass the frozen pre-outcome minimum of three
  structural opportunities per elapsed week and 300 design candidates per
  symbol before source build; the anecdotes do not set a session or volatility
  filter.
- Manual early exits and post-chart explanations are common. T2 excludes them
  from the economic object so anatomy cannot leak back into entry or management.

## 4. P1 verdict and remaining gates

Verdict: `PASS_TO_P2_FORMALIZATION_ONLY`.

The lawful official excerpts are sufficient to define a narrow M5 research
adaptation and to distinguish it from the 70-tick book. They do not establish
profitability, complete book fidelity, XAU/BTC transfer or a professional-
trader benchmark.

P2 must now freeze exact equations and deterministic fixtures for barrier,
pressure, buildup, PBC, PR, room, risk, gaps, conflict priority, cost-aware
break-even probability and state telemetry. P3 must complete the outcome-blind
ECRS and SCC/PBP identity mirrors. P4 must bind the generic all-history MT5 data
epoch for all nine symbols with History Quality strictly greater than 97.

No market outcome, trade, PnL, MT5, MQL5, compile, validation or holdout was
opened to produce this matrix.
