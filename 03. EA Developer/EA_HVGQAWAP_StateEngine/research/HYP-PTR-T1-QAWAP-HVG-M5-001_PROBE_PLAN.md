# Probe Plan - HYP-PTR-T1-QAWAP-HVG-M5-001

Status: `FROZEN_PRE_PROBE` on `2026-07-30T20:05:00Z`, before any market-price,
trade, PnL, Profit Factor, MT5 outcome, validation or holdout access for this
hypothesis. This plan authorizes only deterministic synthetic estimator and
causality tests. It authorizes no `.mq5`, compile, Strategy Tester run, trading
simulation, economic selection, paper trading or live trading.

The plan is SHA-bound into the append-only candidate registry before execution.
It is immutable after binding. A failure cannot be rescued by changing a seed,
sample length, estimator, threshold, null family, graph statistic or gate under
this hypothesis ID.

## 1. Identity and object under test

- Hypothesis ID: `HYP-PTR-T1-QAWAP-HVG-M5-001`.
- EA package: `EA_HVGQAWAP_StateEngine`.
- Campaign / generation: `CAMPAIGN-PTR-E01 / T1`.
- Phase: `P5 PREREG`, synthetic capability probe only.
- Intended later universe, if every pre-outcome gate passes: `XAUUSD`,
  `BTCUSD`, `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`, `AUDUSD`,
  `NZDUSD`; M5; Model 0; all available FivePercentOnline-Real history through
  the frozen cutoff, with report History Quality strictly greater than 97%.
- Capability claim under probe: a fixed N=256 persistence classifier and a
  fixed N=64 directed-HVG implementation can distinguish declared synthetic
  structure from short-memory, volatility-clustered and break-contaminated
  nulls without future access.
- Null: the proposed memory/HVG machinery does not meet the frozen finite-sample
  false-positive, power, bias, determinism or causality requirements.

The synthetic probe is not a trading backtest. It may not load any MT5 price
history, broker bar export, report, trade ledger, PnL field or strategy outcome.
All later economic backtests, if authorized, must be produced by MT5 only.

## 2. De-dup and failure radius

Checked before freeze:

- prior single-window classical R/S Hurst filter on USDJPY M15;
- Hurst substitution inside a killed regime-gated mean-reversion object;
- session-VWAP bounce/reclaim/standard-deviation-band families;
- terminal VRAS seven-gap and one-bar path-confirmation objects;
- post-outcome session, weekday, year, direction, stop, target and cost rescue.

This object is materially different only if all of the following remain true:

1. memory is a jointly calibrated uncertainty state, not `H > 0.5`;
2. QAWAP is a causal activity-weighted location control, not a directional
   story by itself;
3. directed-HVG features encode ordering and are prefix-stable;
4. a pooled fixed model has no symbol identifier or symbol-specific strategy
   parameters;
5. five predeclared arms, not a readout-selected indicator combination, own the
   later economic family.

Failure of this probe closes the exact N=256/m=32/DFA/Lo and N=64 directed-HVG
capability object. It does not prove that all long-memory, anchored-price,
visibility-graph, discretionary or professional trading systems lack edge.

## 3. Frozen software and randomness contract

- Runtime: workspace Python with NumPy and SciPy only; no network and no
  package installation during the probe.
- Base seed: unsigned integer `20260731` through
  `numpy.random.SeedSequence`; every family/replicate child seed is derived by
  fixed indexed spawning and recorded.
- Float type: IEEE-754 binary64.
- Input length for memory estimators: exactly 256 observations after burn-in.
- Input length for HVG: exactly 64 contiguous observations.
- Non-finite input, zero variance, failed optimizer, non-positive DFA
  fluctuation, non-positive Lo HAC variance or inconsistent array length makes
  the replicate invalid. Any invalid-replicate fraction above `0.1%` in any
  family fails the probe; invalid replicates are never silently dropped from a
  rate denominator.
- Execution is resumable by fixed family/batch identity, but replay with the
  same environment and seed must reproduce the canonical JSON payload and
  SHA256 exactly.

## 4. Exact memory estimators

### 4.1 Local Whittle

For demeaned returns `x_t`, `t=0..255`, use frequencies
`lambda_j = 2*pi*j/256`, `j=1..32`, and periodogram
`I_j = |sum_t x_t exp(-i*lambda_j*t)|^2 / (2*pi*256)`.

Minimize on the closed interval `d in [-0.45, 0.45]`:

`R(d) = log(mean_j(I_j * lambda_j^(2d))) - 2d*mean_j(log(lambda_j))`.

Use SciPy bounded scalar minimization with `xatol=1e-8` and `maxiter=500`.
The estimate is `H_LW = 0.5 + d_hat`. Boundary solutions or unsuccessful
optimization are invalid replicates.

### 4.2 DFA1

Build the profile `Y_k = sum_{t=0..k}(x_t - mean(x))`. For each scale
`s in [8,16,32,64]`, partition both from the start and from the end into
non-overlapping complete boxes. In each box fit an intercept plus linear time
trend by ordinary least squares on integer coordinates `0..s-1`. Let `F(s)` be
the square root of the unweighted mean of every squared residual across both
directions and all complete boxes. `H_DFA` is the unweighted OLS slope of
`log(F(s))` on `log(s)`. No overlapping boxes and no scale weighting are
allowed.

### 4.3 Lo modified R/S

For each frozen lag `q in [1,3,6,12]`, use demeaned `x`, population-denominator
autocovariance `gamma_j = sum_{t=j..255}(x_t*x_(t-j))/256`, and Bartlett HAC
variance:

`S2_q = gamma_0 + 2*sum_{j=1..q}(1-j/(q+1))*gamma_j`.

The statistic is the range of the cumulative demeaned series divided by
`sqrt(S2_q * 256)`. The four lag statistics remain separate; they are not
averaged and no single lag may create support.

## 5. Synthetic path population

Each null family has exactly 20,000 independently seeded paths: the first
10,000 are calibration-only and the final 10,000 are verification-only.
Each fractional alternative has exactly 10,000 verification paths. Burn-in is
4,096 observations where recursion is used; only the final 256 are observed.
Innovations are standard Gaussian unless stated otherwise. Every final series
is demeaned but not variance-normalized before estimation.

Null families:

1. `IID_GAUSSIAN`: iid N(0,1).
2. `AR_NEG_03`: AR(1), phi=-0.30.
3. `AR_POS_03`: AR(1), phi=+0.30.
4. `AR_POS_06`: AR(1), phi=+0.60.
5. `ARMA_11`: `x_t=0.40*x_(t-1)+e_t-0.30*e_(t-1)`.
6. `GARCH_0590`: `h_t=0.05+0.05*x_(t-1)^2+0.90*h_(t-1)` and
   `x_t=sqrt(h_t)*e_t`, initialized at unconditional variance 1.
7. `VOLATILITY_BREAK`: first 128 observations N(0,0.5^2), final 128
   N(0,2.0^2).
8. `MEAN_BREAK`: first 128 observations N(0,1), final 128 N(0.5,1), followed
   only by the common whole-path demeaning.
9. `BLOCK_PERMUTED_AR06`: generate the AR(1) phi=0.60 path, divide the final
   256 observations into 32 ordered blocks of length 8, then apply one seeded
   random permutation of complete blocks.

Fractional alternatives are exact Davies-Harte fractional Gaussian noise with
`H in [0.60,0.65,0.70]`, corresponding to `d in [0.10,0.15,0.20]`. A negative
circulant eigenvalue below `-1e-12` is invalid; values in `[-1e-12,0)` are set
to zero. No approximate ARFIMA shortcut is allowed.

## 6. Calibration and memory decision rule

For each scalar metric (`d_hat`, `H_DFA`, and each of the four Lo statistics`),
compute the Type-7 empirical 95th percentile separately on the 10,000
calibration paths of every null family. The frozen common critical value is the
maximum of those nine family quantiles. Calibration paths never enter reported
false-positive or power rates.

A verification path has `PERSISTENCE_SUPPORT=true` only when all conditions
hold:

1. `d_hat` strictly exceeds its common critical value;
2. `H_DFA` strictly exceeds its common critical value;
3. `abs((0.5+d_hat)-H_DFA) <= 0.10`;
4. at least three of the four Lo statistics strictly exceed their respective
   common critical values.

This is a calibrated support decision for the capability probe, not permission
to reduce the later market model to a binary Hurst threshold. The later state
vector retains continuous estimates, disagreement and uncertainty fields.

Hard memory PASS gates:

- for every null family, the one-sided Wilson 95% upper bound of the
  verification false-support rate is `<=0.05`;
- for `d=0.10`, the one-sided Wilson 95% lower bound of support power is
  `>=0.80`;
- for every fractional alternative, absolute median bias of local-Whittle
  `d_hat` and DFA-implied `d=H_DFA-0.5` is `<=0.05`;
- no Lo lag supplies the sole support: the frozen three-of-four rule is
  mandatory and the per-lag exceedance rates are reported;
- invalid-replicate rate is within the Section 3 limit.

There is no `almost pass`. Missing the d=0.10 power floor is a capability
failure even when false positives are low.

## 7. Exact directed-HVG contract

For values `y_0..y_63`, add a directed edge `i -> j`, `i<j`, iff every
intermediate `k` obeys `y_k < min(y_i,y_j)`. Equality blocks visibility. Edges
always point forward in observation time.

Compute exactly three features:

1. `degree_kl`: KL divergence from out-degree to in-degree histograms over bins
   `0..63`, using a Laplace pseudocount of `0.5` in every bin and natural logs;
2. `degree_entropy`: entropy of the undirected total-degree histogram over bins
   `0..63`, same pseudocount, divided by `log(64)`;
3. `motif4_imbalance`: for every consecutive four-node window encode all six
   possible undirected visibility edges as a six-bit mask in lexicographic pair
   order; reverse the four values and encode again; report one half of the L1
   distance between the two 64-bin mask-frequency distributions, each with
   pseudocount `0.5` and normalized to one.

Use the first 64 observations of the same null calibration/verification paths.
For `degree_kl` and `motif4_imbalance`, take the maximum of the nine per-family
Type-7 97.5th calibration percentiles as the common critical value. A path is
flagged irreversible if either statistic strictly exceeds its critical value.
`degree_entropy` is a continuous feature and has no direction threshold.

Hard graph PASS gates:

- for every reversible null family, the one-sided Wilson 95% upper bound of the
  verification irreversibility rate is `<=0.05`;
- all three features are finite and deterministic;
- each feature has non-zero empirical variance in every verification family;
- exact edge sets and all three features are invariant under appending arbitrary
  future observations when recomputed for the original 64-node prefix.

## 8. Causality fixtures and later parity boundary

The probe emits fixed synthetic OHLC/tick-volume fixture vectors covering:

- UTC 00:00 QAWAP reset;
- zero tick-volume and missing-bar rejection;
- gaps greater than 15 minutes and exclusion of the first post-gap return;
- ATR14 warm-up;
- equal-value HVG ties;
- prefix append/future mutation;
- long, short and abstain directional candidates.

For every decision index `t`, features may read completed bars `<=t` only.
Labels, future closes, next-open fills, costs after `t`, trade outcomes and
future graph edges are forbidden feature inputs. The probe creates Python
reference vectors only. Python-to-MQL5 parity remains a P7 gate after source
exists and must match exact graph integers plus frozen numeric tolerance
`max(abs_error) <= 1e-10` for QAWAP/ATR and `<=1e-8` for estimators/features.

## 9. Later economic family and trial accounting

Exactly 45 later economic performance cells are selectable:

`[A0_SIMPLE,A1_QAWAP,A2_QAWAP_MEMORY,A3_QAWAP_GRAPH,A4_FULL] x 9 symbols`.

The equal-weight/TWAP, shuffled-volume, time-shifted, sign-shuffled,
moving-block, classical-Hurst and component-removal objects outside those five
arms are non-selectable falsification diagnostics. They may invalidate a causal
interpretation but may never nominate, parameterize or promote a strategy. If
any additional object becomes economically selectable, campaign multiplicity,
trial budget and alpha debt must expand before it runs; 45 may not be retained.

No pooled PF can rescue a losing symbol. Every claimed sleeve must independently
pass all-history and split gates. Required later acceptance remains:

- verified-cost PF `>1.30`; x1.5 PF `>=1.25`; x2 PF `>=1.00`;
- 2 to 5 executed trades per elapsed calendar week on every relevant split;
- mean expectancy `>=0.08R`, historical DD `<=6%`, Monte Carlo P95 DD `<=8%`;
- long and short positive, temporal stability, calibration, WFA/PBO/DSR,
  parameter-neighborhood, execution, non-repaint and independent QC gates;
- at least 100 seed-frozen random executed-trade anatomy images for a candidate
  that otherwise reaches the forensic gate.

## 10. P5 artifacts and verdict routes

Required artifacts:

- `research/run_t1_math_probe.py` and tests;
- canonical `research/evidence/HYP-PTR-T1-QAWAP-HVG-M5-001_MATH_PROBE.json`;
- calibration critical values, family counts, Wilson bounds, bias tables,
  exact environment versions and reference-fixture hashes inside that JSON;
- one append-only registry transition with the probe verdict;
- one campaign exposure transition; no trial, arm or split is marked viewed by
  this outcome-free synthetic probe.

Verdicts:

- `PROBE_PASS_TO_P6`: every memory, HVG, determinism and causality gate passes.
- `PROBE_FAIL_CAPABILITY`: any statistical capability gate fails; no EA source,
  Model 0 or economic test under this ID.
- `PROBE_INVALID_REPAIR`: implementation, environment, replay, artifact or test
  invalidity prevents inference; only a logic-identical bounded repair is
  permitted.

Even `PROBE_PASS_TO_P6` grants only OOP build authority. Before any economic
MT5 packet opens, the epoch/data-quality process must select exactly one
hash-bound PASS receipt for every mandatory symbol, the aggregate
`validate_data_epoch.py --require-complete` gate must pass, source and prereg
must be hash-bound, and all task packet identities must be frozen. Missing or
sub-97-quality history is `INVALID_REPAIR`, never a no-edge result and never a
reason to skip XAUUSD, BTCUSD or any of the seven liquid FX symbols.
