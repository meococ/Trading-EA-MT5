# New Strategy Deep Research Packet V2 — 2026-07-12

Status: `PRE-RESEARCH / NOT PREREGISTERED / NO EA CODE AUTHORIZED`

This packet supersedes V1 for research intake. V1 was submitted with `Pro`
visible but without the separate `+ -> Nghiên cứu sâu` tool being verified;
its output is not valid Deep Research evidence.

## Required ChatGPT UI contract

- Model: `GPT-5.6 Sol`.
- Intelligence mode: `Pro`.
- Tool: select `Nghiên cứu sâu` from the `+` menu before submission.
- If any of these three states is not visibly available, do not submit and do
  not relabel a normal answer as Deep Research.

## Research objective

Find a genuinely new, falsifiable intraday FX mechanism that could support a
new MT5/MQL5 EA. A useful answer may be `NO LEGAL CANDIDATE`. Do not force three
cosmetic variants when the data, execution contract, or local de-duplication
gate makes them invalid.

Workspace promotion target, which every train and one-time holdout must meet:

- PF strictly above 1.30 after verified same-broker full cost at x1.
- PF at least 1.25 at x1.5 cost and at least 1.00 at x2 cost.
- 2-5 completed trades per elapsed calendar week, never active-week cadence.
- No weekend exposure and preferably no overnight exposure.
- Closed-bar/non-repaint decisions and next-bar executable-price semantics.
- Stable out-of-sample expectancy and tolerable tail risk; PF alone is not a
  promotion argument.

## Local evidence: failure families that must remain closed

The local catalog contains 217 identity-valid non-empty runs across 34 EAs.
Zero runs meet both PF > 1.30 and 2-5 trades per elapsed week. Treat the
following as falsification controls, not a menu for threshold tuning.

### Near misses that still failed

1. `EA_SonicR` short XAU seed: PF 1.3976 but only about 1.23 trades/week;
   robustness 57.1%, equity `REJECT`, top 5% of trades contributed about
   199.9% of profit, and the longer same route fell to PF 1.1535. This is a
   favorable-regime pocket, not a backbone.
2. `EA_SilverBullet`: PF 1.3255 at 1.993 trades/week in 2021-2025, but PF
   1.2594 at 1.936/week over 2019-2025, weak equity concentration, missing
   broker-calibrated cost proof, overnight/weekend violations, and The5ers
   transfer PF 1.018939 / cost-x1.5 PF 0.998852. Do not round cadence to pass.
3. `EA_LondonNY`: PF 1.960412, holdout PF 1.396754, strong cost stress and MC
   DD, but only about 0.3 trades/week; the USDJPY+XAUUSD book remained about
   0.42/week and cross-pair transfers failed. It is a sparse sleeve only.

### Strategy and feature families already killed or parked

- London/Asian range stop-hunt, Asian manipulation, sweep/reclaim,
  session-only reversal, generic opening momentum/drift, and hour/day vetoes.
- Sonic Classic/PVSRA/Dragon/Trend reconstruction, context-fail rescue,
  sideway classifier, scanner alignment, PVA/SR/source-parity qualification.
- ATR impulse, Dragon-anchor compression, microstructure casebook, H1 sweep,
  H1 velocity coordination, S/R runway, and counter-extension filters.
- Generic compression breakout/retest, value drift to EMA89, and range/mean
  reversion. EUR Asian manipulation reached 2.21/week but cost PF was only
  about 1.078; GBP value drift holdout cost PF was about 0.817.
- Other-pair predictive lead-lag (`S555`), same-bar USD consensus into a fixed
  pair (`S618`), laggard catch-up (`S670`), and the cost-blocked strongest-pair
  common-USD router. Do not rename these as factor rotation.
- Gap fill: historical entry spread and rollover erased the apparent edge;
  later compiled probe PF about 0.477.
- Management rescue: MFE/BE/TP/trailing/max-hold/weekend-flat changes are not a
  new entry mechanism and cannot rescue a failed family.
- Shelf failures: ITSM holdout PF 1.05484 with decay; ChopRegime untouched OOS
  PF 1.025976; Gotobi corrected treatment PF 0.910317; Spark about 1.00/0.93;
  H4Ribbon pooled PF about 0.357; TrendBook portfolio PF about 0.496.

Do not use post-hoc thresholds, shorter favorable windows, outcome-selected
symbols, rounded cadence, zero cost, fixed toy cost, duplicate reruns, or old
validator `PASS` labels as evidence.

## Data and execution reality

- Preferred execution: M5/M15; HTF may be closed-bar context only.
- Canonical unsuffixed symbols: EURUSD, GBPUSD, XAUUSD. USDJPY is permitted
  only under a new frozen contract.
- Historical same-broker cost coverage is currently inadequate: about 4% of
  2024-2025 M15 bars have non-zero spread fields; commission evidence has two
  EURUSD lifecycles and none for GBPUSD/USDJPY; usable independently referenced
  slippage samples are zero.
- Missing spread, commission, slippage, swap, fee, bid/ask path, timezone, or
  event timestamp is missing evidence, never zero cost.
- Reject mechanisms requiring unavailable order book, options positioning,
  dealer flow, news timestamps that cannot be reconstructed, discretionary
  chart labels, or synthetic ask-high/ask-low from one bar spread.

## Deep Research task

Use primary sources first: peer-reviewed papers, BIS/central-bank research,
exchange/official benchmark methodology, and official broker/market
specifications. Forums are idea provenance only.

### Phase A — mechanism search and hard de-duplication

1. Propose at most three economically distinct mechanisms. Each must explain
   why a retail-CFD implementation could retain edge after spread, commission,
   slippage, and swap.
2. For each mechanism, provide a de-duplication matrix against every closed
   family above. Mark `REJECT` if the new proposal differs only by a threshold,
   indicator proxy, symbol, session, or management rule.
3. Apply a data-availability gate before ranking. Mark `REJECT` if the required
   historical inputs cannot be supplied by synchronized OHLC/ticks plus
   official public timestamps/specifications.
4. Rank surviving mechanisms by independence, expected elapsed-week cadence,
   cost tolerance, data availability, implementation complexity, and ease of
   falsification. Do not rank by imagined PF.

### Phase B — exact rules for survivors

For each survivor give exact closed-bar rules for universe, timeframe,
timezone/DST, warmup, state calculation, direction, entry, next-bar execution,
SL, TP, time stop, forced flat, conflict arbitration, missing-data behavior,
and one-position policy. Identify every source-backed parameter and every
research degree of freedom.

Maximum research budget: one fixed rule set per mechanism. A source may justify
one predeclared sensitivity pair only when the paper itself supplies both
values. No grid search and no post-result rescue.

### Phase C — one cheap offline probe for the top survivor

Define a train-first, one-time-holdout offline population probe using only
existing OHLC/tick artifacts and conservative cost assumptions. Freeze:

- exact input paths/schema and hash requirements;
- train/holdout dates;
- executable bid/ask convention;
- cost x1/x1.5/x2;
- minimum observations and minimum elapsed-week cadence;
- PF/expectancy gates for both splits;
- year/half-year/regime concentration limits;
- drawdown/tail diagnostics;
- no-lookahead checks;
- exact kill conditions and rule that a failure becomes a new idea, never an
  edit to the current hypothesis.

If cost provenance is insufficient even for a conservative falsification
probe, return `BLOCKED_BY_COST_DATA` and specify the smallest safe data-acquiry
contract. Do not invent costs.

### Phase D — build contract, not code

Only for a probe-eligible survivor, provide an MQL5 build contract: module
boundaries, indicator/data handles, shift discipline, new-bar gating, risk in
account currency via `OrderCalcProfit`, tick/point/volume normalization,
position state, telemetry fields, source/input/config hashes, compile receipt,
and non-repaint audit points. Do not generate EA code and do not claim expected
profitability.

## Required sources table

For every material claim include title, author/publisher, publication date,
direct URL, accessed date, source type, and label it `FACT`, `INFERENCE`, or
`MODEL SUGGESTION`. State explicitly when no primary source supports a rule.

The answer is research input only. It does not authorize a hypothesis ID,
registry row, prereg freeze, analyzer, EA edit, compile, backtest, or promotion.
