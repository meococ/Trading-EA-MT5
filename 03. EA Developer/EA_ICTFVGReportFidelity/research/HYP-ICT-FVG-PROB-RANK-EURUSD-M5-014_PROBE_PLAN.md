# HYP-ICT-FVG-PROB-RANK-EURUSD-M5-014 - frozen rolling-OOS probability/no-trade diagnostic

Status: **FROZEN BEFORE HYP-014 MODEL FIT, SCORE OR VERDICT**

Epistemic class: **DESIGN AFTER PARENT OUTCOME; ROLLING-OOS DIAGNOSTIC, NOT A
SEALED HOLDOUT OR PROMOTION TEST**.

## Object and boundary

- Parent HYP-012 is terminal and remains terminal. HYP-013 repaired Friday
  execution only and supplies no alpha claim.
- Input is the 3,385 actual HYP-012 context-state entries in
  `02. AlphaFactory/runtime/ictfvg_hyp012_context_forensics/positions_with_context.csv`,
  bytes `2,580,003`, SHA-256
  `1661ECE481CC1D52BE7751F445602ECE79AC1CA1F6F92AA6C2BF28594645B5B6`.
- One row is one opportunity. Rejecting a row earns `0R`; it is never removed
  from the `R/opportunity` denominator. This file does not contain all 6,416
  HYP-012 confirmations or gate-rejected sweeps, so conclusions apply only to
  ranking the 3,385 entries already accepted by HYP-012.
- The parent outcomes were already inspected before this child was designed.
  Annual expanding folds prevent within-fold leakage but do not create an
  untouched holdout. Every result remains diagnostic and
  `promotion_eligible=false`.

## Fixed costs and target

- EURUSD is treated as five-digit: `risk_pips = risk_pts / 10`.
- For cost multiplier `x`, row return is
  `r_gross - (1.5 * x) / risk_pips`; evaluate `x=1.0, 1.5, 2.0`.
- Classification target is `1` only when the training-row `x1.0` return is
  positive. Gross/commission outcomes are not features.

## Fixed information set

All features are available at the original decision/entry time and use the
closed-bar forensics already produced for HYP-012:

1. `direction`;
2. `confirmation_body_vs_prior20`;
3. `confirmation_directional_close_location`;
4. `confirmation_range_pips`;
5. `bars_after_sweep`;
6. `sweep_depth_pips`;
7. `sweep_reclaim_pips`;
8. `risk_pips`;
9. `h1_ema_spread_directional_atr`;
10. `h1_return5_directional_atr`;
11. `h4_ema_spread_directional_atr`;
12. `h4_return5_directional_atr`.

After train-median imputation, add exactly four interactions:

- confirmation body ratio x directional close location;
- sweep depth x sweep reclaim;
- H1 directional EMA spread x H4 directional EMA spread;
- H1 directional 5-bar return x H4 directional 5-bar return.

Do not use year, clock-mismatch label, outcome, exit, PnL, MFE/MAE, native
commission, later candles or another feature.

## Fixed rolling policy

- Evaluation years are 2020, 2021, 2022, 2023, 2024, 2025 and partial 2026.
  For each year, train on every earlier row beginning in 2018; fit transforms
  only on that training fold.
- Median-impute, standardize, then fit one deterministic L2 logistic regression:
  `C=0.1`, `solver=liblinear`, `max_iter=2000`, `random_state=560014`, no class
  weighting and no hyperparameter search.
- On the training fold calculate:
  - the linear-method 60th percentile of predicted probability;
  - average positive and negative `x1.0` R;
  - the probability required for `+0.05R` expected value from those two means.
- The test-year threshold is the maximum of those two values. Process rows in
  UTC order and accept a qualifying row only while fewer than five rows have
  already been accepted in its ISO calendar week. There is no forced minimum,
  hindsight weekly ranking, threshold relaxation or fallback trade.
- One model/policy only. Trial budget is exactly one. No feature ablation,
  threshold variant, fold deletion or rescue is allowed after the result.

## Frozen gates

All must pass on pooled 2020-partial-2026 rolling predictions:

1. at least 300 accepted rows;
2. cadence between 2.0 and 5.0 accepted rows per elapsed calendar week;
3. `x1.0` PF >= 1.30;
4. `x1.0` accepted expectancy >= +0.05R/trade;
5. `x1.0` R/opportunity > 0;
6. accepted expectancy exceeds the all-entry evaluation control by >=0.15R;
7. week-block bootstrap seed `560014`, 10,000 samples: lower 95% CI of policy
   `x1.0` R/opportunity > 0 and lower 95% CI of paired delta versus control > 0;
8. at least five positive evaluation years and no positive-year contribution
   concentration above 35%;
9. `x1.5` PF >=1.25 and `x2.0` PF >=1.00;
10. maximum drawdown at the frozen 0.01% HYP-012 risk scale <=8%.

Fail any gate: terminal `KILL_AT_ROLLING_OOS_DIAGNOSTIC_NO_CODE`. Passing every
gate only authorizes a fresh source/Model-0 preregistration with coefficients
and transforms frozen from this diagnostic; it does not itself authorize code,
backtest, paper/live use or promotion.

