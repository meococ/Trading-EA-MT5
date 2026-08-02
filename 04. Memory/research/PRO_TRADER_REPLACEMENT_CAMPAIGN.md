# Pro-Trader Replacement Campaign - Master Minute

Status: `ACTIVE / T2_P2_FROZEN_P3_CAPABILITY_IMPLEMENTATION /
P4_DATA_CONTRACT_BOUND_0_OF_9 /
GOAL_UNMET`  
Opened: `2026-07-31 Asia/Saigon`  
Owner intent: build a market decision system from research, mathematics,
probability, causal implementation and MT5 evidence - not from shallow EA
assembly or post-outcome filter tuning.

This is the single campaign-level planning and session minute. It does not
replace `01. GOAL/GOAL.md`, the candidate registry, a frozen preregistration,
task packet, EA-package evidence, or AlphaFactory artifacts.

## 1. North star and sequential generations

The north star is not an indicator collection. It is a decision policy:

`observe -> infer state -> quantify uncertainty -> trade/skip -> size -> execute
-> manage -> exit -> learn without rewriting exposed history`.

`T1, T2, ... T100` are sequential strategy generations, not research teams and
not evidence levels. Only one generation may own build or MT5 outcome authority
at a time:

1. `T1`: Hurst + advanced VWAP + quantitative/visibility-graph state model.
2. `T2`: Bob Volman-inspired causal price-action grammar; queued until T1 has a
   valid non-PASS verdict.
3. `T3`: causal SMC/market-structure/liquidity model; queued until T2 verdict.
4. `T4..T100`: selected adaptively from the prior generation's demonstrated
   capability gap, not from an indicator wishlist.

Sub-agents may fan out research, mathematical review, data audit and QC inside
the active `Tn`. EA writes, compile ownership and MT5 runs remain serial. A
valid fail advances learning and may open `T(n+1)`; it kills only the exact
tested object and never proves the market or professional traders have no edge.

The generation sequence stops only when one symbol-sleeve reaches the minimum
target in `01. GOAL/GOAL.md`. Portfolio expansion and live deployment remain
separate post-success stages.

## 2. Phase machine applied to every Tn

Every generation uses the same complete phase machine. Research is not a
substitute for building; building is not allowed before research survives.

| Phase | Required decision/output |
|---|---|
| `P0 CHARTER` | Freeze `Tn`, capability to replace, mechanism, primary M5/M15 symbol/TF, family/run budget, minimum observations and pre-outcome verdict boundaries. |
| `P1 RESEARCH` | Primary/lawful sources, forum discovery, causal mechanism, payer/forced participant, expected horizon, failure conditions and unresolved facts. |
| `P2 FORMALIZE` | Decision-time state, action including `skip`, estimand/null, uncertainty, entry/exit/invalidation, cost/risk geometry and requirement-to-code matrix. |
| `P3 DE-DUP` | Compare registry, failure radius and trial history; prove a materially new mechanism/information set/decision surface or stop before outcome. |
| `P4 DATA/FIDELITY` | Verify all available MT5 history, >97% quality eligibility, symbol mapping, M5/M15 construction, ticks/model, clock/DST, volume semantics and cost provenance for every required symbol. |
| `P5 PREREG` | Create hypothesis ID, registry row and SHA-frozen plan: symbols, splits, finite setups/arms, controls, parameters, costs, seeds, PASS/KILL/INSUFFICIENT/repair rules. |
| `P6 OOP BUILD` | Build one canonical EA with replaceable market-state, signal, entry, exit, risk, execution, management and telemetry modules. |
| `P7 ENGINEERING` | Compile, deterministic smoke, closed-bar/non-repaint audit, estimator/feature parity, clock/data fidelity, lifecycle and log completeness. |
| `P8 MT5 ECONOMICS` | Serial MT5 control then challenger on all available history for every required symbol, with 2018-current attribution where covered, followed only by preregistered OOS/WFA/cost cells. One run answers one question. |
| `P9 QUANT ANALYSIS` | Per-symbol PF/expectancy/cadence, power/CI, time/regime/direction stability, control lift, cost sensitivity, parameter neighborhood, WFA, overfit debt and Monte Carlo/tail risk. |
| `P10 FORENSICS` | At least 100 seed-frozen random executed trade episodes for a PASS candidate, with `decision_asof` and anatomy images bound 1:1 to report/log IDs. |
| `P11 INDEPENDENT QC` | Read-only reviewer recomputes identity, costs, PF/cadence, leakage, sample selection, charts, robustness and the winning market mechanism. |
| `P12 VERDICT/LEARN` | Close with `TARGET_PASS`, `VALID_FAIL`, `INVALID_REPAIR` or `INSUFFICIENT`, produce failure/capability packet, improve the process, clean scratch and route the next action. |

Transition rules:

- `TARGET_PASS`: at least one symbol passes every frozen economic, cadence,
  robustness, overfit, forensic and QC gate. Stop creating `T(n+1)` and freeze
  the survivor package. It does not authorize live trading.
- `VALID_FAIL`: engineering/data-valid evidence breaches a fatal gate or misses
  target with sufficient observations. Kill the exact object, record its
  failure radius and open a materially new `T(n+1)`.
- `INVALID_REPAIR`: no economic inference is legal because data, implementation,
  model, parity, cost, log or identity is invalid. Repair the same frozen Tn
  within its retry budget; do not change market logic.
- `INSUFFICIENT`: the frozen evidence boundary cannot decide PASS or FAIL.
  Extend only when that extension was preregistered; otherwise park the cell,
  audit the missing capability and advance to `T(n+1)`. If 2018-current is
  structurally below cadence, classify goal mismatch rather than waiting.

After every non-PASS verdict, the Process Auditor classifies the gap as
`research | mathematics | data/fidelity | implementation | execution/cost |
statistics | forensics/QC | goal/cadence`, proposes the smallest reusable
harness/process improvement, and verifies it before the next generation opens.
No loop may reopen an exposed object by changing threshold, weekday, session,
symbol, timeframe, stop, target or cost assumption. A fresh ID does not reset
trial history or make an exposed holdout unseen again.

## 3. Session and artifact hygiene

- This file is the only campaign plan/minute. Do not create parallel master
  plans, daily status documents or duplicate agent summaries.
- Candidate-specific preregistration, code and evidence belong only inside its
  canonical `03. EA Developer/<EA>/research/` package after a legal candidate
  identity is opened.
- Raw data persists only under `02. AlphaFactory/data/`; run artifacts persist
  only under `02. AlphaFactory/runs/`; temporary inspection output uses the
  existing scratch/temp convention and is removed after evidence capture.
- Every session begins by reading this minute, GOAL, INDEX, current registry,
  relevant failure radius, AlphaFactory status and exact active artifacts.
- Every session ends by appending one ledger row below with: decision delta,
  `active_T`, phase/gate, verdict state, trial/holdout exposure, evidence paths,
  files changed, cleanup result and the single next executable action.
- Before the first outcome is opened, the dedicated machine ledger
  `04. Memory/research/CAMPAIGN_EXPOSURE.jsonl` must bind `data_epoch`, every
  arm/control viewed, design/OOS/holdout exposure, alpha/trial budget spent and
  remaining, multiplicity family, charter SHA and exact reopen condition. It is
  not a second human plan: the ledger exists separately because many legacy
  `CANDIDATE_REGISTRY.jsonl` readers assume every row is a hypothesis. Both
  ledgers are append-only and fail-closed under their own validators.
- Research progress is measured by a better specified mechanism, a capability
  gap closed, an executable checkpoint or a new economic verdict - never by
  number of documents, agents, charts or tests.
- MT5 and all writes are serial. Read-only research may fan out. The Lead Quant
  owns the final interpretation and must not let an agent promote its own work.
- Only the active `Tn` may have hypothesis/build/outcome work. Later generations
  may retain a one-line queue and lawful source pointers, but may not begin a
  competing research contract, build or backtest before the active verdict.
- Reuse persistent functional agents across generations when available so
  failure context and harness knowledge are retained. Builder and promotion
  reviewer remain separate.
- Git is observational unless the Owner explicitly requests commit/push in the
  current message. Existing unrelated changes are preserved.

## 4. Generation T1 - Hurst, VWAP and quantitative graph state model

Working name: `HVG-VWAP Probabilistic State Engine`  
Current state: `T1_CLOSED_PRE_ECONOMIC / T2_ACTIVE /
GOAL_UNMET / NO_MARKET_OUTCOME_EXPOSURE`

Frozen P0 authority:

- charter:
  `04. Memory/research/PRO_TRADER_REPLACEMENT_E01_T1_P0_CHARTER.json`
  (`SHA256 30C82B65EB4660C24D9E4C2A280E6E84BCFDDAB009939B5D7DB146AA0457D65F`);
- exposure ledger: `04. Memory/research/CAMPAIGN_EXPOSURE.jsonl`, first raw-row
  SHA256 `156979B6F37B71EC063BB96524FC1FD78D90E5500296873D30B06B8576D2BFFC`;
- frozen family: five arms on all nine mandatory symbols, M5, 45 performance
  cells, Model 0 requested from `1970.01.01` through the frozen 2026-07-30
  cutoff, with Strategy Tester quality strictly `>97%`;
- split, arm and outcome exposure remain sealed. No hypothesis, source, prereg,
  task packet, MT5 outcome, paper or live authority exists yet.

### 4.1 New mechanism boundary

This track is not:

- the prior single-window R/S Hurst filter on USDJPY M15;
- an ADX/CI/Hurst substitution inside a killed mean-reversion object;
- a Session-VWAP bounce, reclaim or SD-band strategy;
- the terminal VRAS seven-gap object, its one-bar continuation child, or a
  stop/R:R/session rescue;
- a claim that VWAP itself predicts price.

The proposed new information/decision surface is a probabilistic state engine:

1. estimate persistence only when multiple estimators and surrogate controls
   agree within a declared uncertainty bound;
2. represent price location relative to a causal session or event anchor;
3. convert the recent normalized path into a visibility graph and transition
   state;
4. forecast a six-completed-bar close-path outcome with calibrated uncertainty;
5. trade only when posterior edge after cost exceeds the frozen abstention
   boundary.

### 4.2 Mathematical objects

Use log returns rather than raw prices for memory estimation:

`r_t = log(P_t / P_{t-1})`.

The research candidate must compare, not casually average:

- Lo modified rescaled-range statistic for short-memory-robust long-memory
  testing;
- local-Whittle, detrended fluctuation analysis or another justified estimator
  whose finite-sample behavior is tested before selection;
- block-bootstrap/surrogate confidence intervals under short-memory and
  volatility-clustered nulls.

No state may be called persistent merely because a point estimate has
`H > 0.5`. The output is an uncertainty-bearing state such as
`P(persistent | information_t)`, not a binary Hurst threshold.
Lo modified R/S is an independent rejection flag, not a posterior generator.
The candidate contract must separately define the estimator, its null/test,
the probability-calibration method and the assumptions under which `H` is
interpretable.

For price-volume location:

`VWAP_t = sum_{i=a..t}(p_i * v_i) / sum_{i=a..t}(v_i)`.

The anchor `a`, price definition, volume proxy, clock/reset rule and missing
volume behavior must be frozen before outcomes. For OTC FX, broker tick volume
is a broker-specific activity proxy, not centralized traded volume. Mandatory
controls are equal-weight/TWAP, shuffled-volume VWAP and a price-only anchor.

The normalized path may be mapped to a natural or horizontal visibility graph.
For a natural visibility graph, observations `i < j` connect only if every
intermediate `k` satisfies:

`y_k < y_i + (y_j - y_i) * (k - i) / (j - i)`.

Candidate graph features are restricted to a small preregistered set such as
degree distribution, motif frequencies, local clustering and graph entropy.
They describe path geometry; they are not assumed to be predictive.
Directed horizontal-visibility time-irreversibility is a preferred research
candidate because it tests path ordering rather than merely adding another
trend score. Any graph threshold must be learned only on a sealed design fold
from session-slot-preserving surrogate paths.
At decision time `t`, the graph contains nodes and edges observable by `t`
only. Features of old nodes may not be recomputed with future edges. Intraday
slot scaling, clustering/codebooks and graph thresholds are fit on the design
fold and then frozen.

The causal state vector is provisionally:

`S_t = [persistence posterior, VWAP distance/slope, robust volatility,
graph geometry, session age, spread/cost state]`.

A fixed L2 logistic model estimates the probability of the favorable
close-threshold occurring before the adverse close-threshold or six-bar
timeout. Entry and every exit execute at the next M5 open. No broker SL/TP,
trailing, break-even, partial exit or intrabar first-hit rule is permitted, so
generated Model-0 tick order cannot select the primary label. The charter
freezes the 256-return memory window, 64-node directed HVG, 1R/1.25R close
thresholds, six-bar horizon, train/calibration split, proper scores and
`p_BE + 0.05` abstention boundary.

### 4.3 Mandatory controls and ablations

- `A0_SIMPLE` equal-weight/variance-ratio control.
- `A1_QAWAP` strict QAWAP control.
- Frozen `A1 | +memory | +graph | full` matched ablation through
  `A2_QAWAP_MEMORY`, `A3_QAWAP_GRAPH` and `A4_FULL`, so the full object cannot
  survive merely by inheriting an anchored-QAWAP effect.
- Equal-weight/TWAP and shuffled-volume controls.
- Time-shifted, sign-shuffled and moving-block surrogate paths.
- Hurst point-estimate filter identical in spirit to the prior failed R/S arm.
- Full ablation of persistence, VWAP and graph components.
- Fixed simple execution/risk geometry during the mechanism test.

The complex model must beat the simple control by a frozen margin. If it only
reduces exposure or cadence, it has not created edge.

### 4.4 Data and fidelity prerequisites

- Start with the existing FivePercent EURUSD closed-bar shelf for outcome-blind
  estimator diagnostics and parity work only; its historical spread column is
  not cost truth and the bar shelf cannot authorize economic evidence.
- Inventory broker tick-volume semantics and missing/partial bars before using
  VWAP weights.
- Do not label generated MT5 Model 0 ticks as real ticks. Intrabar claims require
  Model 4 evidence plus real-tick/fallback coverage; T1 avoids that dependency
  through completed-bar decisions and next-open execution.
- XAUUSD, BTCUSD, EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD and NZDUSD are
  mandatory cells. They share the explicitly frozen UTC 00:00 reset and
  Monday-Friday 07:00-15:30 decision clock; BTC weekend data is observed but no
  weekend-specific arm or silent FX-clock inheritance is allowed.
- AlphaFactory now fail-closes a task-packet-bound `data_quality_contract`:
  `all_available_asof`, frozen `1970.01.01` sentinel, cutoff-date equality,
  numeric History Quality strictly above a threshold no lower than 97, exact
  tester-journal synchronized bounds, run-local complete journal delta, and a
  separately recomputed data-quality fingerprint. Legacy packets remain
  compatible but cannot acquire T1 data authority.
- The frozen epoch contract is
  `04. Memory/research/PRO_TRADER_REPLACEMENT_E01_T1_DATA_EPOCH.json`
  (`SHA256 DB2C8E08F68FA88BD6B6F96FDB19231BEFE73797F5DBF361A511BFB5A5DCA29C`).
  Its append-only evidence ledger currently contains only the header: no symbol
  has been run or selected. `validate_data_epoch.py --require-complete` remains
  fail-closed until exactly one selected PASS receipt exists for every one of
  the nine mandatory symbols. Runtime synchronized ranges and HQ are therefore
  still unknown, but that expected per-run proof no longer blocks opening P5.

### 4.5 T1 gates before P6 OOP build

1. Estimator implementations pass synthetic fractional, short-memory, GARCH
   and regime-break controls without systematic false persistence.
2. Python/reference and intended MQL5 closed-bar features match within frozen
   tolerances.
3. Graph features are causal, deterministic and stable enough for the declared
   window; missing bars fail closed.
4. Outcome-blind state counts and dwell times can support the target cadence.
5. Trial axes and degrees of freedom are finite and logged at campaign level.
6. The track has a materially new identity versus prior Hurst and VRAS failures.
7. UTC reset/decision scheduling, actual broker calendar and all-available
   synchronized boundaries are manifest-bound; no server-hour approximation or
   hindsight anchor is allowed.

Passing these gates does not finish T1. It grants progression through P5 prereg,
P6 OOP build, P7 engineering, P8 MT5 economics, P9 statistics, P10 100-trade
forensics, P11 QC and P12 verdict. Failing them yields a pre-outcome T1 verdict
and capability packet; only then may T2 open.

## 5. Generation T2 - Bob Volman price-action quantification

Working name: `Volman Causal Price-Action Grammar`  
Current state: `T2_P0_FROZEN / P1_SOURCE_COMPLETE / P2_FORMAL_SPEC_FROZEN /
P3_REFERENCE_AND_DEDUP_PREP /
P4_DATA_CONTRACT_BOUND_0_OF_9 / GOAL_UNMET / NO_MARKET_OUTCOME_EXPOSURE`

T2 opened after the valid T1 terminal pre-economic capability closeout. Its P0
charter is frozen at
`04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P0_CHARTER.json`
(`SHA256 D63F782926DEC4F12EA8EBB17B3511BC08C249A0AE4ECD9C1F25F5C611386E9E`)
and canonical machine exposure row 5 (`EPOCH_REOPEN/P0`, raw SHA256
`7251EA6B0D5F90A61687E17DA8293DF66DDC5BA859640D9B6302EB2AF83AEABD`)
resets trial, alpha, split and market exposure to zero. Two concurrently
appended reopen rows were never valid; their raw hashes, zero-exposure audit
and repair are preserved in
`CAMPAIGN_EXPOSURE_REPAIR_20260731_T2_REOPEN_RACE.json` without weakening the
validator. The material below is now the active T2 research
boundary, but it still grants no hypothesis ID, `.mq5` source, MT5, economic,
validation, holdout, promotion, paper or live authority.

Pre-market research bindings:

- P1 lawful source matrix:
  `PRO_TRADER_REPLACEMENT_E02_T2_P1_SOURCE_MATRIX.md`, SHA256
  `9F82D03AA90DDAE694CA6716631354543BA21CC16D78CBD2B5E5A5DE6C5956BD`;
- P2 exact causal grammar:
  `PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md`, SHA256
  `CB1DDA2B678D2F450BB2DDE05327D2734E2A430BBBC4809BB08C71110FA0BA7D`,
  independently reviewed after cost/risk, grid, PR-depth and duplicate-barrier
  defects were corrected;
- P4 data epoch:
  `PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH.json`, SHA256
  `F47901F60E4314321B4B201ACED1D8D7366AC5D64589C487E893F0153332F648`,
  ledger still header-only at 0/9 selected PASS. Runtime evidence and economics
  remain closed.

### 5.1 Source boundary

Use the author's/publisher's lawful excerpts and a lawfully available copy of
the books for fidelity. Forum posts are discovery and trader-context evidence,
not authoritative definitions and not profitability proof. Do not use pirated
book copies or reproduce copyrighted text/figures into the repository.

The first book's 70-tick chart and the second book's 5-minute framework are
different data contracts. They cannot be silently merged.

### 5.2 Quantification target

Convert discretionary observations into a causal event grammar rather than
hard-code pattern names. Provisional tokens include:

- directional pressure leg and loss of pressure;
- pullback depth, duration, overlap and counter-pressure;
- buildup/block compression near a barrier;
- barrier identity and prior tests;
- squeeze quality and available path to target;
- break and failed-break telemetry;
- adverse magnet, round-number proximity and opposing structure;
- explicit `skip` state when context is ambiguous or cost geometry is poor.

Each token must have a decision-time definition, invalid state, missing-data
behavior and observable telemetry field. Pattern labels may be derived only
from those tokens.

A semi-Markov/event-grammar model is preferred over a single bar classifier so
that duration and event order remain part of the state. The output is a
probability and abstention decision, not a retrospective chart narrative.

The frozen novelty claim is narrower than "box breakout": a barrier is
locked from past bars, then the grammar measures repeated tests, directional
higher-lows/lower-highs and contraction before a favorable closed-bar break.
If those sequential-pressure variables do not add information beyond a matched
range-break control, T2 is duplicate surface and must stop before EA build.
Pattern-break pullback/retest continuation is excluded from all economic T2
arms and the full policy because it overlaps the terminal SCC family. It
remains only an outcome-blind identity diagnostic. A false-break fade or PBP
economic object requires a future generation/search cell, not an arm added
after outcome.

The five selectable economic arms are `A0_LOCKED_BARRIER_BREAK`,
`A1_PATTERN_BREAK`, `A2_PATTERN_BREAK_COMBI`, `A3_PULLBACK_REVERSAL` and
`A4_CAUSAL_GRAMMAR_POLICY`. Nine additional diagnostics cover always-skip,
prevalence-matched random, EMA25-only, barrier/buildup semantics, shuffled/time-
reversed order, label agreement, exact ECRS identity and SCC/PBP identity.
Those diagnostics may kill a capability but cannot select, rescue, contribute
PnL or promote.

### 5.3 Fidelity and labeling contract

- A faithful 70-tick bar requires the ordered broker tick stream. M1 OHLC or
  generated tick interpolation cannot substantiate the original method.
- A closed-bar implementation is explicitly `Volman-inspired`, not a faithful
  replication of an intrabar barrier-break entry described in the source.
- Tick-bar construction must freeze quote/event type, duplicate handling,
  session gaps, reconnect behavior and broker clock.
- Labels are captured on `decision_asof` charts with outcome and PnL hidden.
- At least two independent reviewers label `trade/skip`, direction, setup
  token sequence, barrier, invalidation and confidence.
- Grammar/codebook development cases, blinded inter-rater reliability cases
  and unseen economic-evaluation cases are disjoint. The agreement metric must
  handle class imbalance and the disagreement/adjudication policy is frozen
  before reliability cases are opened.
- Agreement and calibration are measured before economic outcomes are opened.
  Low agreement identifies an unquantified capability gap rather than a rule
  to guess in code.
- Outcome charts are used only for anatomy after labels are locked.

### 5.4 Mandatory controls

- Simple locked-barrier break control with the same entry and cost geometry.
- 25-EMA-only contextual control where applicable.
- Barrier-only and buildup-only semantic ablations.
- Prevalence-matched random entry and always-skip policies.
- Time-reversed or sequence-shuffled negative controls where causally valid.
- Independent outcome-blind human/agent label benchmark on disjoint unseen
  cases; reviewers are not represented as professional-trader performance.

T2 may build an EA only after source fidelity, label reliability, tick-bar
parity, opportunity density and a finite grammar are demonstrated.

## 6. Queued generations T3 to T100

`T3` is provisionally a causal SMC/market-structure/liquidity generation and may
open only after a valid non-PASS T2 verdict. It must translate every discretionary
term into delayed, machine-observable state: swing confirmation, BOS/CHOCH,
displacement, liquidity sweep, FVG/imbalance, order-block provenance/expiry,
premium/discount and session context. Hindsight pivots and repainting structure
are forbidden; matched simple breakout/reversal controls must show incremental
lift.

`T4..T100` are selected adaptively from demonstrated capability gaps, ranking:

1. materially new market mechanism or information set;
2. M5/M15 cost survivability and plausible 2-5 trades/week/symbol;
3. causal data/fidelity availability from 2018-current;
4. cheap falsifiability and distance from prior failure radius;
5. ability to improve a pro-trader capability: state inference, abstention,
   timing, execution, risk, adaptation or portfolio interaction.

Possible families include execution/microstructure, session/auction transition,
volatility compression-expansion, cross-asset lead-lag, event/flow data and
new-information mean reversion. They are not reserved IDs and cannot be chosen
from a just-read winning/losing subgroup.

If T100 closes without PASS, do not claim a project frontier. Run an independent
campaign meta-review of research ability, data, execution, formalization,
harness, selection bias and repeated-test debt; preserve all holdout exposure
and multiplicity history, then open a new Phase-0 campaign epoch. Only Owner
stop, new cost/live-risk authority or a proven material blocker may halt it.

## 7. Campaign-wide economic and forensic acceptance

Research sources may include Forex Factory, Reddit and other practitioner
forums for vocabulary, failure modes and candidate discovery. A forum claim is
never profitability evidence. Mathematical definitions, market-data semantics
and implementation contracts must trace to primary research, official platform
documentation or lawful author/publisher material.

The final evidence path remains MT5/AlphaFactory only:

- meaningful economic tests run through the real MT5 Strategy Tester and
  `02. AlphaFactory/alpha.ps1`; offline work is estimator, data, cadence or
  falsification evidence, not a substitute backtest;
- every required symbol uses all MT5 history currently available; the
  2018-current subwindow is reported separately where covered. Strategy Tester
  history quality strictly greater than 97% is eligible, but the percentage
  does not waive clock, gap, bid/ask, cost or tick-order limitations;
- primary entry/economic timeframes are M5 and M15. H1/H4/D1 may provide only
  preregistered context/regime state;
- the mandatory backtest universe is XAUUSD, BTCUSD and the seven liquid FX
  majors EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD and NZDUSD. EURUSD may
  lead P0-P7 feasibility, but P8 cannot close Tn without every required symbol
  cell. A Tn may test a finite preregistered set of setups/arms, but no fitted
  parameter set or session clock transfers silently across symbols;
- Model 0 may provide per-symbol economic evidence when its history quality is
  >97%. Model 4 remains mandatory for claims that depend on real-tick order,
  intrabar barrier ordering or microstructure. Missing Model 4 limits the claim;
  it does not authorize skipping that symbol's Model-0 backtest;
- a research survivor must satisfy `01. GOAL/GOAL.md`: PF greater than 1.30
  after verified x1 cost and cadence 2-5 executed trades per elapsed calendar
  week on the same claimed symbol in every relevant split. PF and cadence are
  never pooled across symbols. x1.5/x2 cost stress, positive stability,
  tail/Monte-Carlo risk, holdout, WFA/overfit controls and matched-control lift
  must also pass. PF alone never promotes;
- AlphaFactory must retain and reconcile the full tester report, exact config,
  source/EX5/compile receipt, lifecycle/deal/RunMeta telemetry, cost evidence,
  log triage and chart manifests;
- Heavy-Delivery visual forensics for a PASS claim requires at least 100
  seed-frozen random executed trade cases, with separate outcome-blind
  `decision_asof` and outcome `anatomy` images, exact ID coverage and image-open
  QC. If fewer than 100 trades exist, review the full executed population plus
  clearly labeled rejected diagnostics, but the candidate cannot make a PASS
  Heavy-Delivery claim; never invent or relabel trades to reach 100;
- an independent Quant Validator and Trade Forensics Reviewer challenge every
  promotion claim. The Lead Quant reconciles contradictions and owns the final
  `engineering-valid | economic-valid | promotion-ready` separation.

Failure returns the campaign to the smallest demonstrated capability gap. A
process audit may improve a harness, estimator or data contract, but it cannot
rescue the exposed strategy object or reset its trial/holdout history.

## 8. Agent operating structure

- Lead Quant / Owner delegate: final scope, trial budget, evidence and verdict.
- Persistent Program Integrator: maintains this minute, task queue and handoff
  context.
- Market/Mathematical Researcher: active-Tn mechanism, source fidelity,
  probability/grammar, synthetic controls and falsification.
- Data/Fidelity Researcher: broker data, clock, volume, cost, tester model and
  research↔MQL5 parity.
- OOP Builder: serial source owner after the active candidate is frozen.
- Compile/Fidelity Reviewer: compile, closed-bar/non-repaint, deterministic
  telemetry and requirement-to-code coverage.
- MT5 Runner: serial global-lock owner.
- Quant Validator: independent family-level statistics and cost evidence.
- Trade Forensics Reviewer: blinded decision-as-of and outcome anatomy.
- Process Auditor: reviews a failed cycle, identifies capability gap and
  proposes the smallest testable harness improvement.

Reuse these functional agents from T1 through T100 when available so they retain
context without creating a permanent heavy roster. Builder and promotion
reviewer remain separate whenever independence is material.

## 9. Source register

Primary/reliable starting points:

- Andrew W. Lo, "Long-Term Memory in Stock Market Prices" (1991):
  https://www.jstor.org/stable/2938368
- BIS, "Private information, stock markets, and exchange rates":
  https://www.bis.org/publ/work271.htm
- Evans and Lyons, "Order Flow and Exchange Rate Dynamics":
  https://www.bis.org/publ/bppdf/bispap02j.pdf
- Lacasa et al., "From time series to complex networks: The visibility graph"
  (PNAS 2008): https://doi.org/10.1073/pnas.0709247105
- Busseti and Boyd, "Volume Weighted Average Price Optimal Execution":
  https://stanford.edu/~boyd/papers/vwap_opt_exec
- Bob Volman author/publisher excerpt page:
  https://infofpas.wordpress.com/
- Bob Volman author-hosted FPAS excerpt PDF (70-tick reference only):
  https://infofpas.wordpress.com/wp-content/uploads/2011/10/excerpts-fpas-hr-3-6-121.pdf
- Bob Volman `Understanding Price Action` author excerpt page:
  https://upabook.wordpress.com/
- Bob Volman author-hosted UPA excerpt PDF (T2 five-minute source):
  https://upabook.wordpress.com/wp-content/uploads/2014/09/excerpts-upa.pdf
- Osler, stop-order clustering and exchange-rate dynamics:
  https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf
- Cont, Kukanov and Stoikov, order-flow imbalance (mechanism context only):
  https://arxiv.org/abs/1011.6402
- Publisher/book metadata for `Forex Price Action Scalping`:
  https://www.harvard.com/book/9789090264110
- Official MQL5 Strategy Tester tick-generation semantics:
  https://www.mql5.com/en/docs/runtime/testing
- MQL5 comparison of generated and broker-real-tick testing:
  https://www.mql5.com/en/articles/2612

Research warnings:

- Naive finite-sample Hurst estimates can report `H > 0.5` for Brownian data;
  every persistence claim needs a statistical null and uncertainty interval.
- VWAP is well established as an execution benchmark; that does not establish
  directional trading alpha.
- Community Volman setup abbreviations are useful as a vocabulary index only:
  https://www.forexfactory.com/thread/578183-volman-style-70-tick-chart
- Community Hurst discussions repeatedly surface finite-window bias,
  non-stationarity and bootstrap sensitivity; they are failure-mode discovery,
  not evidence of alpha:
  https://www.reddit.com/r/algotrading/comments/1hr77sy/ and
  https://www.reddit.com/r/algotrading/comments/1b5zh8e/

## 10. Session ledger

| Session | Date | Decision/evidence delta | Files changed | Cleanup | Next executable action |
|---|---|---|---|---|---|
| S0001 | 2026-07-31 | `SUPERSEDED_BY_S0002`: Owner established research-first mandate. Workspace audit found prior terminal VRAS objects, a failed simple R/S Hurst regime arm, existing EURUSD M1/H1/H4 data, invalid historical spread-cost provenance, MT5 stopped and a materially dirty pre-existing tree. Independent T1/T2 reviews bounded novelty, probability/leakage, controls, labeling separation and fidelity; neither track had build authority. | Master minute plus routing-only pointers in `INDEX.md` and `04. Memory/hot.md`. | No MT5, no run, no generated dataset, no temp artifact retained. | Historical next action was superseded because it incorrectly allowed T2 parallel work; S0002 is authoritative. |
| S0002 | 2026-07-31 | Owner superseded the parallel-track interpretation. T1..T100 are sequential complete strategy generations; T1 is the only active generation, T2 is queued, T3 is provisional SMC, and every Tn uses P0 charter through P12 verdict/self-improvement. Minimum stop target is one confirmed symbol-sleeve; every claimed symbol must independently deliver PF >1.30 after verified cost and 2-5 executed trades/elapsed week on each split, with M5/M15 priority. | Updated `01. GOAL/GOAL.md`, this master minute, `INDEX.md` and `04. Memory/hot.md`; no candidate/prereg/source/run files. | No MT5, compile, backtest, generated dataset or temp artifact. Existing unrelated dirty tree preserved. | Open T1 P0 charter and campaign-exposure record; no T2 active research/build/outcome work until a valid T1 non-PASS verdict. |
| S0003 | 2026-07-31 | Owner required all available MT5 history, Strategy Tester quality strictly >97%, and no skipped XAUUSD/BTCUSD/seven-major cells. T1 P0 froze one universal M5 completed-bar engine, five fixed arms, 45 arm-symbol cells, chronological split policy, non-intrabar exits and explicit PASS/FAIL/INVALID routes. Independent QC rejected a mixed hypothesis/campaign registry and three weaker ledger revisions before the dedicated SHA-chained exposure ledger passed. P1 mathematical/market research and P3 failure-radius review completed; P4 remains active because exact tester synchronized boundaries, numeric HQ gating and promotion-grade cost provenance are not yet closed. | Added the frozen T1 charter, dedicated exposure schema/validator/tests/ledger; corrected Model-0 wording in AlphaFactory source; updated campaign/goal routing docs. No hypothesis, prereg, EA source or outcome artifact. | No MT5 launch, compile, backtest, dataset, outcome, split opening or arm exposure. Ignored Python cache only; unrelated dirty tree preserved. | Implement and independently test the optional task-packet-bound `data_quality_contract` plus tester-journal capture, then bind the nine-symbol P4 data epoch before opening T1 P5. |
| S0004 | 2026-07-31 | Closed the P4 contract/capability gap without opening outcomes. AlphaFactory now enforces task-packet→receipt→manifest data quality, strict `HQ > threshold >=97`, the 1970 all-history sentinel, cutoff/as-of consistency, exact symbol journal bounds, run-local non-truncated deltas, semantic start/end dates and a separately recomputed DQ fingerprint. A frozen FivePercentOnline-Real M5/Model-0 epoch plus SHA-chained aggregate ledger prevents campaign completion until XAUUSD, BTCUSD and all seven FX symbols each have one selected hash-bound PASS. | Added the epoch contract/evidence ledger and aggregate validator/tests; appended campaign exposure row 2 (`DATA_BIND/P4`); hardened AlphaFactory data-quality capture and post-run research-loop verification. | No MT5 launch, compile, backtest, report, symbol PASS, outcome, split opening or arm exposure. Runtime HQ/ranges remain unknown by design; aggregate `--require-complete` correctly fails on all nine missing symbols. | Open T1 P5 identity/prereg/task-packet package against the already frozen charter and epoch; do not authorize MT5 until parity, synthetic false-persistence and cost contracts are bound. |
| S0005 | 2026-07-31 | Independent P4 re-QC closed receipt/report/locality/duplicate-journal and JSON-bool alias gaps; 46 targeted tests passed and aggregate remains correctly incomplete at 0/9. P5 opened `HYP-PTR-T1-QAWAP-HVG-M5-001` with SHA-frozen synthetic-only finite-sample probe. The plan resolves estimator/HVG ambiguity, keeps only 45 economic cells selectable and freezes the difficult joint false-positive/power gates before source. | Added the package probe plan; appended candidate registry row 439 and campaign exposure row 3 (`BIND_HYPOTHESIS/P5`); promoted the aggregate no-skip rule into `AGENTS.md`. | No MT5, market history, trade/PnL, source, compile, economic arm, split or alpha exposure. Registry/campaign/epoch validators pass; epoch is intentionally 0/9. | Implement, independently review and execute the deterministic synthetic math probe; PASS may open P6, capability FAIL closes this exact T1 object before any economic backtest. |
| S0006 | 2026-07-31 | T1 closed at P12 before market exposure. Two logic-identical 210,000-path synthetic attempts both ended `PROBE_INVALID_REPAIR`; the permitted observability repair proved all 389 invalid replicates were frozen local-Whittle boundary/optimizer events, while support was 0/10,000 at each simulated d=0.10, 0.15 and 0.20. Independent quant and code QC found no remaining same-ID repair. Verdict `INVALID_REPAIR_EXHAUSTED__P5_SYNTHETIC_CAPABILITY_FAILS_PRE_ECONOMIC_GATE` closes only the exact N256/m32/DFA/Lo/HVG capability object; it is not a market no-edge conclusion. | Added the P12 closeout; appended terminal candidate row 440 and campaign exposure row 4 (`GENERATION_CLOSE/P12`); updated failure radius, active-shelf record and two reusable process rules. | No market data, MT5, MQL5, compile, trade/PnL, economic trial, alpha spend or split opening. Both ledgers validate and the nine-symbol T1 data evidence remains unopened at 0/9. | Open T2 P0 with a fresh Bob-Volman-inspired M5 causal-grammar charter, lawful-source boundary and reset exposure ledger; do not reuse T1's future estimator or call the M5 object a 70-tick replication. |
| S0007 | 2026-07-31 | T2 opened at P0 after T1 terminal closeout. The frozen charter defines a Volman-inspired M5 causal price-action grammar rather than a 70-tick replication, keeps XAUUSD, BTCUSD and seven FX-major symbols mandatory, uses Model 0 all-history cells with History Quality strictly >97%, and fixes 5 arms x 9 symbols = 45 performance cells. | Added campaign exposure row 5 (`EPOCH_REOPEN/P0`), generalized `validate_data_epoch.py` from T1-only to T1..T100 generation identity, added T2/mismatch tests, and updated routing docs. | No MT5, market data, `.mq5`, compile, trade/PnL, economic trial, alpha spend, split opening or holdout. Campaign/candidate/source validators pass; data-epoch tests pass. | Continue T2 P1/P2: lawful source-to-requirement matrix, exact causal equations/fixtures, outcome-blind ECRS/PBP de-dup mirrors, then freeze the T2 data epoch before any MT5 economics. |
| S0008 | 2026-07-31 | T2 data epoch is now frozen before any T2 hypothesis/source/economic outcome: FivePercentOnline-Real, M5, Model 0, requested from `1970.01.01` through `2026-07-30T23:59:59Z`, History Quality strictly `>97%`, no-skip across XAUUSD, BTCUSD and seven FX-major symbols. Aggregate evidence remains deliberately incomplete at 0/9 selected PASS receipts. | Added `PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH.json`, `PRO_TRADER_REPLACEMENT_E02_T2_DATA_EVIDENCE.jsonl`; appended campaign exposure row 6 (`DATA_BIND/P4`); updated `hot.md` and `INDEX.md`. | No MT5 launch, backtest, report, `.mq5`, compile, trade/PnL, validation/holdout, alpha spend or split opening. `validate_data_epoch.py` passes incomplete mode and must fail `--require-complete` until all nine receipts exist. Campaign/candidate/source validators pass; 35 focused tests pass. | Continue T2 P1/P2/P5-prep: source matrix, exact equations/fixtures, de-dup mirrors and prereg/source contract; only then run serial MT5 all-history cells for every mandatory symbol. |
| S0009 | 2026-08-02 | Owner-directed VRAS V4 plan review ran as one outcome-blind P0 exception outside T2. The deterministic probe proved the claimed EURJPY headline values came from an unfiltered USDJPY tail of a combined three-symbol 2016-2020 DESIGN file; the proposed EURUSD transfer, true-flow primitives, frozen estimator/arbitration and production-async gates all failed. Verdict `PARK_PRE_EA_INVALID_PLAN_EVIDENCE_OR_CAPABILITY_NO_OUTCOME_READ`. | Added the V4 prereg, six-test harness, corrected forensic runner, hash-bound result/readout/failure packet and routing docs. No candidate row was retained because candidate schema requires a real canonical EA source. | Zero validation/holdout rows, trade outcomes, economics, `.mq5`, compile, MT5 launch, order, alpha spend or split exposure. Registry reconciled to 461 rows / 163 hypotheses; T2 authority remained unchanged. | Resume only the frozen T2 synthetic-fixture/de-dup route. Any V4 successor needs a fresh identity, one atomic mechanism and correct target-symbol/statistical/data/execution contracts before outcomes. |
