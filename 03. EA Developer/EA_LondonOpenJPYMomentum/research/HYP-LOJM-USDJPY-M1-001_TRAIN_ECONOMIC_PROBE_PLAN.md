# HYP-LOJM-USDJPY-M1-001 — Frozen TRAIN Economic Probe Plan

- EA package: `EA_LondonOpenJPYMomentum`
- Status: `FROZEN_EVALUATOR_BUILD_ONLY`
- Frozen at: `2026-07-29T16:20:00Z`
- Outcome access: `NOT_AUTHORIZED_UNTIL_REGISTRY_ROW_IS_HASH_BOUND`
- MQL5 / Model 0 / optimization: `NOT_AUTHORIZED`
- Validation / holdout / promotion / paper / live: `NOT_AUTHORIZED`

## Question and mechanism

Does the sign of USDJPY's first 30 completed minutes after the London cash
open persist through the remainder of the London session strongly enough to
clear conservative retail round-trip costs on the local FivePercent broker
DESIGN data?

The causal working thesis is that London-open risk rebalancing and JPY's role
as a carry-funding/risk-sentiment currency can create persistent same-session
order-flow pressure. The signal is deliberately simple. No RSI, moving average,
trend filter, weekday filter, volatility threshold, news veto, BOJ regime veto,
or post-outcome indicator may be added under this ID.

Primary research anchor:

- Leander Seeck (2026), *Intraday Momentum in Spot FX and Currency Futures:
  Signal Persistence, the JPY Amplification Mechanism, and the Cost Barrier to
  Retail Exploitability*, SSRN 7008318.

Only the public abstract was retrievable before freeze. It reports a London
Open 30-minute sign signal, stronger coefficients for JPY instruments, and
USDJPY as the only tested spot pair with positive cost-adjusted OOS results.
The PDF body was blocked by SSRN/browser policy, so the exit below is explicitly
the workspace's remainder-of-London-session translation, not a claim of exact
paper replication.

## De-dup and failure radius

The 2026-07-17 pure-OHLC screen classified generic early-to-late intraday
momentum as a design-only rebrand; it did not run a price probe. This fresh ID
is allowed by the Owner's current instruction and by new post-screen primary
evidence specific to the London-open 30-minute sign and JPY amplification.

If this probe fails, the exact object below is terminal. Forbidden rescues are:
changing the open/exit clock, using UTC instead of `Europe/London`, reversing
direction, deleting 2020/BOJ/news days, adding filters, changing costs, using a
different stop/target, or opening validation to tune the rule. A genuinely new
mechanism requires a new ID and preregistration.

## Frozen data and splits

Re-use the already exported close-only DESIGN parquet; do not launch MT5 or
decode HCC again:

- parquet: `02. AlphaFactory/data/fivepercent/TriangularConsensusLag/HYP-TRILAG-EURJPY-M1-002/design_m1_close.parquet`
- parquet SHA-256:
  `C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6`
- manifest: `02. AlphaFactory/data/fivepercent/TriangularConsensusLag/HYP-TRILAG-EURJPY-M1-002/design_m1_manifest.json`
- manifest SHA-256:
  `4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8`
- exact source contract: completed broker Bid M1 close, UTC bar-open timestamp,
  no interpolation or forward fill.
- TRAIN/DESIGN: `2016-01-01 00:00:00 UTC` through
  `2020-12-31 23:59:59 UTC`.
- internal validation: `2021-01-01` through `2024-12-31`, sealed and absent
  from this parquet.
- research holdout: every `2025+` payload, sealed and forbidden.

The evaluator may read only USDJPY rows from the frozen parquet. EURUSD and
EURJPY rows are irrelevant to this probe and must not enter any calculation.

## Frozen clock, signal, and execution proxy

Use IANA timezone `Europe/London`, including historical BST/GMT transitions.
For each Monday-Friday London-local date, require exact completed M1 bars at:

- `07:59` local bar close observed at `08:00`;
- `08:29` local bar close observed at `08:30`;
- `16:29` local bar close observed at `16:30`.

No nearest-bar match is allowed. Define:

1. `formation_log_return = log(close_08:29 / close_07:59)`.
2. Skip only an exactly zero formation return.
3. `direction = +1` for positive formation, `-1` for negative formation.
4. Decision/entry proxy is `close_08:29`, known only when the 08:29 bar has
   completed at 08:30 local.
5. Exit proxy is `close_16:29`, known when the 16:29 bar completes at 16:30.
6. `gross_pips = direction * (exit_close - entry_close) / 0.01`.

There is exactly one candidate trade per complete eligible date. No overnight
or weekend holding exists. The close-only proxy has no executable Bid/Ask path,
SL, TP, intrabar excursion, or fill model; therefore this stage can falsify the
economic thesis but cannot establish deploy readiness or risk-budget compliance.

## Frozen controls, costs, and statistics

- Matched reverse control: exact same dates and prices with `-direction`.
- Round-trip cost x1: `1.50 pips` per trade.
- Cost x1.5: `2.25 pips` per trade.
- Cost x2: `3.00 pips` per trade.
- Net pips: `gross_pips - round_trip_cost_pips`.
- Profit factor: sum positive net pips divided by absolute sum negative net
  pips; zero-loss denominator is invalid, never infinity-as-pass.
- Expectancy: arithmetic mean net pips per trade.
- Elapsed weeks: exact TRAIN wall-clock span divided by seven days; active-week
  denominators are forbidden.
- Annual result: sum x1 net pips by London-local decision year.
- Sign-persistence permutation: fixed seed `20260729`, exactly `10,000`
  permutations of the frozen directions across the same signed entry-to-exit
  price moves;
  one-sided p-value `(1 + count(null_mean >= observed_mean)) / 10001`.
- No parameter search, optimization, subperiod selection, or multiple candidate
  directions are allowed. This is one performance trial plus its locked
  reverse-direction control.

## Source and cadence gates

All must pass before economic metrics may support a survivor:

1. Parquet and manifest bytes match the two frozen SHA-256 values; manifest
   schema, row count, symbol set, DESIGN bounds and parquet hash reconcile.
2. USDJPY timestamps are unique and strictly increasing; closes are finite and
   positive; no row is from 2021 or later.
3. At least `1,000` complete eligible dates exist.
4. Complete eligible-date coverage is at least `95%` of Monday-Friday London
   dates between the first and last eligible London date.
5. Cadence is between `2.0` and `5.0` trades per elapsed calendar week.
6. LONG and SHORT each contain at least `300` trades and at least `25%` of the
   population.
7. No one local calendar year contains more than `25%` of trades.

Any failure of gates 1-2 is `ENGINEERING_INVALID_NO_MARKET_VERDICT`. Any valid
source failure of gates 3-7 is `KILL_STRUCTURAL_NO_ECONOMICS_SURVIVOR`.

## Economic survivor gates

All must pass together on the same frozen population:

1. Primary PF at x1 cost is strictly greater than `1.30`.
2. Primary PF at x1.5 cost is at least `1.25`.
3. Primary PF at x2 cost is at least `1.00`.
4. Primary x1 expectancy is strictly positive.
5. At least `4 of 5` local calendar years have positive x1 net pips.
6. One-sided permutation p-value is at most `0.05`.
7. Primary x1 PF and expectancy both exceed the matched reverse control.

If all source/cadence/economic gates pass:
`PASS_TRAIN_PROXY_AUTHORIZE_FRESH_MQL5_MODEL0_PACKET_ONLY`.

Otherwise, with valid source:
`KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED`.

A PASS authorizes only a fresh, hash-bound MQL5/Model-0 task packet with native
OHLC, executable spread/cost provenance, a predeclared catastrophe stop, code
parity and non-repaint audit. It does not authorize validation, optimization,
promotion, paper trading or live trading.

## Attempt and evidence contract

- Exactly one economic attempt: `LOJM001-TRAIN-ECON-001`.
- Evidence root:
  `03. EA Developer/EA_LondonOpenJPYMomentum/research/evidence/HYP-LOJM-USDJPY-M1-001/LOJM001-TRAIN-ECON-001/`.
- Before real execution, the evaluator/tests must pass, their SHA values plus
  this plan SHA must be frozen in the latest registry row, and the evaluator's
  one-use registry-row sentinel must be armed with that exact row SHA.
- Create-new outputs: `attempt_started.json`, `trades.jsonl`,
  `train_economic_terminal.json`.
- The terminal must bind plan, evaluator, test, registry row, dataset manifest,
  parquet and output hashes; it must record all forbidden counters at zero.
- MT5 launches, HCC decodes, MQL5 files, Model 0/4 runs, validation/holdout
  reads, network calls, paid requests, optimization, paper and live actions
  remain zero/false.
