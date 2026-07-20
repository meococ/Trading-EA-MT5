# HYP-ICT-FVG-PROB-RANK-EURUSD-M5-014 - rolling-OOS diagnostic readout

Verdict: **KILL AT ROLLING-OOS DIAGNOSTIC; NO SIGNAL CODE**

## What was tested

One frozen L2-logistic policy ranked the 3,385 entries already accepted by
HYP-012. Annual expanding training began with 2018-2019 and produced untouched
within-fold predictions for 2020 through partial 2026. Rejected entries earned
`0R/opportunity`; the sequential weekly cap never selected later trades using
hindsight. Costs were fixed at 1.5, 2.25 and 3.0 pips round trip.

This is rolling-OOS only. Parent outcomes were known before HYP-014 design, so
it is not a sealed holdout or promotion test.

## Result

The policy accepted only 15 of 2,551 evaluation opportunities across 341.05
elapsed weeks: `0.044` trade/week. At the primary 1.5-pip cost it produced:

- PF `0.9577`;
- accepted expectancy `-0.01577R/trade`;
- `-0.0000927R/opportunity`;
- 95% week-block CI for R/opportunity `[-0.002599, +0.002550]`;
- three positive evaluation years, with 77.88% of positive-year R concentrated
  in 2020.

Stress worsened monotonically: PF `0.8571` at 2.25 pips and `0.7661` at 3.0
pips. Ten of fourteen frozen gates failed. Only the upper cadence bound,
relative expectancy improvement, paired-delta bootstrap and drawdown gates
passed.

The relative improvement is real but insufficient: accepted expectancy was
`+0.19218R` better than the all-entry evaluation control (`-0.20795R`), and the
paired R/opportunity delta CI was `[+0.16431, +0.25063]`. Avoiding most bad
trades is not the same as finding a positive tradable subset.

## Why it failed

The economic break-even threshold learned from each training fold was
`0.6048-0.6208`, while ordinary model scores clustered around `0.47`. Only 15
test scores cleared the threshold. Lowering it would be a post-outcome rescue
and would contradict the requirement for `+0.05R` expected value.

More fundamentally, ranking quality was absent: pooled rolling ROC AUC was
`0.4879`, Brier score `0.2516`, and Spearman correlation between score and
cost-adjusted R was `-0.0389`. Annual AUC exceeded 0.50 only in 2023, 2024 and
partial 2026. The current closed-bar M5 morphology plus H1/H4 directional
trend features do not carry stable information about which accepted HYP-012
entry will pay after cost.

The exact replay reproduced byte-identical predictions, fold models and result
hashes. No alternate threshold, feature ablation or second model was run.

## Decision

Do not add a probability mode to the EA. HYP-014 is terminal and cannot be
rescued by relaxing score, cadence, year or cost gates. Canonical v1.19 keeps
the HYP-013 Friday execution repair, but it still has no economic, paper or
live authority.

A future child must add a materially new decision-time information set or a
different opportunity universe; tuning these same 12 features and four
interactions is not a legal next step.

