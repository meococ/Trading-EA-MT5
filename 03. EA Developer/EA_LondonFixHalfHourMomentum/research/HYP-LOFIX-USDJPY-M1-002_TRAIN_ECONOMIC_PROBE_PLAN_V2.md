# TRAIN ECONOMIC PROBE PLAN — HYP-LOFIX-USDJPY-M1-002

Status: **FROZEN V2 2026-07-29 after a pre-run sentinel-test repair and before
any 15:30-16:00 London target return was read or computed for this object.** This document is immutable after its SHA-256
is bound into the append-only candidate registry. Any outcome-driven clock,
direction, filter, threshold, or cost change requires a new hypothesis ID.

## Identity and decision use

- Hypothesis: `HYP-LOFIX-USDJPY-M1-002`
- Research-only package: `EA_LondonFixHalfHourMomentum`
- Symbol/timeframe: `USDJPY`, completed Bid `M1` closes
- TRAIN/DESIGN window: 2016-01-01 through 2020-12-31
- Validation: 2021-2024, sealed and forbidden
- Research holdout: every 2025+ payload, sealed and forbidden
- Owner objective: identify a cost-adjusted FX sleeve with PF above `1.30` and
  cadence between `2` and `5` trades per elapsed calendar week. This proxy can
  kill the thesis or authorize a later native MQL5/Model-0 packet; it cannot
  promote or deploy an EA.

## Mechanism and primary-source boundary

The frozen thesis is that the sign of USDJPY's first London half-hour contains
directional information that is expressed specifically in the final half-hour
before the 4 p.m. London FX benchmark, when benchmark and rebalancing flow is
concentrated:

1. Elaut, Lampaert and Frömmel define FX intraday momentum as a positive
   relation between the first and last half-hour return in an FX market with
   explicit trading hours. Their instrument is RUB-USD, not USDJPY:
   https://doi.org/10.1016/j.finmar.2016.09.002
2. Gao, Han, Li and Zhou document first-half-hour predictability of the last
   half-hour return in exchange-traded equity instruments:
   https://doi.org/10.1016/j.jfineco.2018.04.030
3. Baltussen, Da, Lammers and Martens find that the last 30 minutes are
   predicted by the rest-of-day return across futures, including currency
   futures, and connect the effect to hedging demand:
   https://doi.org/10.1016/j.jfineco.2021.04.029
4. The WMR methodology defines 4 p.m. UK time as its Closing Spot benchmark,
   while FCA evidence documents concentrated activity, larger price impact and
   more aggressive HFT behavior around the fix:
   https://www.fca.org.uk/publications/occasional-papers/occasional-paper-no-46-fixing-fix-assessing-effectiveness-4pm-fix

This is a prospective **workspace translation**, not an exact replication of
any paper. OTC USDJPY has no exchange close; the 4 p.m. WMR benchmark supplies
the explicit London anchor. The predicted target is only `15:30-16:00`
London-local, not the full remainder of the London session.

## De-duplication and adverse prior

`HYP-LOFIX-USDJPY-M1-001` was parked before execution because its test only
handled the evaluator's disarmed sentinel form. It consumed zero attempts and
opened zero target outcomes. This V2 successor changes only hypothesis/file/
attempt identity and the sentinel test; its market decision surface is unchanged.


`HYP-LOJM-USDJPY-M1-001` is terminal. It used the same 08:00-08:30 sign but
held from 08:30 to 16:30. That exact object had gross PF `0.907704` and x1 PF
`0.793002`; changing its exit, direction, year set, or adding an indicator under
that ID is forbidden.

This fresh root hypothesis is materially different because its entry, holding
interval, causal claim, and cost-to-opportunity geometry are different:

- LOJM001 tested the noisy eight-hour remainder-session path.
- LOFIX002 tests only the pre-fix last half-hour where the cited literature and
  benchmark evidence place concentrated late-day flow.

Adverse priors are explicit: the opening sign already failed over the full
remainder session; a 30-minute move is smaller and a fixed 1.50-pip round trip
can dominate it; evidence from RUB-USD, equities, or currency futures may not
transfer to broker Bid-close USDJPY. “Almost 1.30” is a kill, not a reason to
tune.

## Frozen data contract

Reuse the already exported close-only public DESIGN parquet; do not launch MT5,
decode HCC, export another dataset, or access a later split:

- parquet: `02. AlphaFactory/data/fivepercent/TriangularConsensusLag/HYP-TRILAG-EURJPY-M1-002/design_m1_close.parquet`
- parquet SHA-256: `C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6`
- manifest: `02. AlphaFactory/data/fivepercent/TriangularConsensusLag/HYP-TRILAG-EURJPY-M1-002/design_m1_manifest.json`
- manifest SHA-256: `4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8`
- source contract: completed broker Bid M1 close, UTC bar-open timestamp, no
  interpolation, nearest-bar matching, or forward fill
- exact projection: only USDJPY rows in 2016-2020; every 2021+ row is forbidden

The known historical spread field is unusable. Costs therefore remain a
conservative fixed proxy, not verified same-broker executable cost.

## Frozen clock, signal, and execution proxy

Use IANA `Europe/London` with historical GMT/BST transitions. For each complete
Monday-Friday London-local date require exact completed bars at:

- `07:59` close, observable at `08:00`;
- `08:29` close, observable at `08:30`;
- `15:29` close, the decision/entry proxy observable at `15:30`;
- `15:59` close, the exit proxy observable at `16:00`.

Definitions:

1. `formation_log_return = log(close_08:29 / close_07:59)`.
2. Skip only an exactly zero formation return.
3. `direction = +1` when formation is positive and `-1` when negative.
4. Enter at `close_15:29`; the opening signal has been known for seven hours.
5. Exit at `close_15:59`; do not trade the post-fix interval.
6. `raw_move_pips = (exit_close - entry_close) / 0.01`.
7. `gross_pips = direction * raw_move_pips`.

There is one candidate trade per complete eligible date. No overnight or
weekend exposure exists. This M1 close-only proxy has no Bid/Ask path, fill,
stop, target, intrabar excursion, or position sizing; it can falsify expectancy
but cannot establish execution or drawdown-percent validity.

## Frozen controls, costs, and trial accounting

- Matched reverse control: the exact same dates and prices with `-direction`.
- Round-trip proxy costs: x1=`1.50`, x1.5=`2.25`, x2=`3.00` pips per trade.
- Net pips: `gross_pips - cost`; a missing or zero-loss denominator never passes.
- Cadence denominator: exact 2016-2020 elapsed wall-clock weeks, never active
  weeks.
- Annual result: x1 net pips by London-local decision year.
- Sign-persistence permutation: exactly 10,000 direction permutations, seed
  `20260729`, one-sided p-value `(1 + null_mean >= observed_mean) / 10001`.
- Trial universe for DSR: four x1-cost arms—LOJM001 primary and locked reverse,
  plus LOFIX002 primary and locked reverse. Cost tiers are not extra trials.
- Prior LOJM001 ledger is hash-bound at
  `6985108DEEDF59A503F5A96285F7D5CC8D8CE303FC03A599B5C3E414E0ECDC98`.
- Canonical DSR implementation is hash-bound at
  `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`.
- Per-trade Sharpe uses mean/std with sample standard deviation; V[SR] is the
  sample variance across all four arms; PSR uses skew and non-excess kurtosis.
  DSR radicand failure is `0`, never skipped.
- No optimization, parameter grid, threshold search, or alternate clock is
  authorized.

## Structural gates

All must pass before economics can support a survivor:

1. Parquet/manifest bytes and manifest population match their frozen hashes.
2. USDJPY timestamps are unique/increasing; closes finite/positive; zero rows
   from 2021 or later.
3. At least 1,000 complete eligible dates.
4. At least 95% coverage of Monday-Friday dates between first and last trade.
5. Cadence from 2.0 through 5.0 trades per elapsed calendar week.
6. LONG and SHORT each have at least 300 trades and at least 25% share.
7. No one local year has more than 25% of the population.

Source-integrity failure is `ENGINEERING_INVALID_NO_MARKET_VERDICT`. A valid
source/population failure is `KILL_STRUCTURAL_NO_ECONOMICS_SURVIVOR`.

## Economic survivor gates

Every gate must pass on the same frozen population:

1. Primary PF at x1 cost strictly greater than `1.30`.
2. Primary PF at x1.5 cost at least `1.25`.
3. Primary PF at x2 cost at least `1.00`.
4. Primary x1 expectancy strictly positive.
5. At least four of five local years positive at x1 cost.
6. One-sided permutation p-value at most `0.05`.
7. DSR across the four declared x1 arms at least `0.95`.
8. Primary x1 PF and expectancy both exceed the matched LOFIX reverse control.

All eight pass:
`PASS_TRAIN_PROXY_AUTHORIZE_FRESH_MQL5_MODEL0_PACKET_ONLY`.

Otherwise, with valid source:
`KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED`.

A PASS only opens preparation of a new hash-bound MQL5/Model-0 packet with
native OHLC, verified same-broker costs, executable fills, catastrophe stop,
parity checks and non-repaint audit. It does not authorize validation,
optimization, promotion, paper, or live trading.

## One-shot evidence contract and prohibitions

- Attempt: `LOFIX002-TRAIN-ECON-001`, exactly once.
- Evidence root: `03. EA Developer/EA_LondonFixHalfHourMomentum/research/evidence/HYP-LOFIX-USDJPY-M1-002/LOFIX002-TRAIN-ECON-001/`.
- Create-new outputs: `attempt_started.json`, `trades.jsonl`, and
  `train_economic_terminal.json`.
- Before execution, evaluator/tests pass; plan/evaluator/test/data/DSR/prior
  ledger hashes are bound in the latest registry authority row; the evaluator
  is armed to that exact row hash.
- Forbidden after seeing this outcome: clock shift, direction flip, weekday,
  month, year, BOJ/news/regime veto, formation-size threshold, RSI/EMA/ATR or
  any indicator filter, cost reduction, stop/target retrofit, validation access,
  or same-ID rerun.
- MT5, HCC, MQL5, Model 0/4, validation/holdout, network/paid requests,
  optimization, orders, paper and live counters remain zero/false.

