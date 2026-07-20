# HYP-011 C09/C10 higher-timeframe pair forensics

Date: 2026-07-19

Scope: read-only, post-outcome quantification of the frozen C09 winner and C10
loser selected in the prior HYP-011 trade-forensics pass.

Authority: diagnostic only. This readout creates no filter, rerun, tuning,
promotion, paper or live authority. HYP-011 remains terminal.

## Verdict

The two London short entries are materially similar on higher timeframes as
well as on their local sweep/reclaim morphology. C10 is the nearest D1 short
to C09 in the complete-case cohort, in the closest 1.45% on H4, closest 3.19%
on H1 and closest 0.55% across all 44 M15/H1/H4/D1 features. M15 is the least
similar layer but remains in the closest 16.45%.

The higher-timeframe feature set therefore does not explain why C09 won
`+1.871R` while C10 lost `-1.387R`. The largest one-feature winner/loss
separation among the 2,076 short entries is only AUC `0.5385`, close to random.
Every measured EMA-bias and pivot-structure subgroup has PF below 1 and
negative R expectancy.

## Information-set and leakage controls

- M5 input SHA-256:
  `AAF14451A0AA3671C5037A19ECB30E3A1A27B115A0F16CACBBB4D4209F921C73`.
- Position input SHA-256:
  `0540939EB9D0523ADB0E3EE599E9D1FE134DC8056439CD29FB8A1D0AB926055C`.
- The M15/H1/H4/D1 series are mechanically resampled from the bound M5 data.
- A feature can use only a bar whose `close_time_server <= entry_time_server`.
  The current incomplete higher-timeframe bar is excluded.
- ATR and ADX use the workspace MT5-parity implementations; EMA, returns and
  slopes are causal. Strength-2 pivots require both right-side confirmation
  bars to have closed before entry.
- Pair distance excludes outcome and P&L. Winner labels are used only in the
  explicitly post-outcome population AUC and descriptive PF tables.
- All eight as-of charts enforce the entry cutoff. The chart manifests still
  match the current HTF parquet and frozen pair-case hashes after regeneration.

## Quantified similarity

Distance is robust RMS across 11 frozen numeric features per timeframe after
median/MAD scaling within the short cohort. A smaller percentile means fewer
other shorts are closer to C09 than C10 is.

| Layer | Robust RMS | C10 rank from C09 | Comparisons | Nearest percentile |
|---|---:|---:|---:|---:|
| M15 | 1.1830 | 341 | 2,073 | 16.45% |
| H1 | 1.2173 | 66 | 2,072 | 3.19% |
| H4 | 0.5219 | 30 | 2,065 | 1.45% |
| D1 | 0.2268 | 1 | 2,012 | 0.05% |
| Combined 44 features | 0.8926 | 11 | 2,012 | 0.55% |

This is strong evidence of morphological similarity, not evidence that either
setup is good. Both trades were shorts inside an overall bullish D1 state.

## What is the same and what differs

| TF | C09 winner | C10 loser | Assessment |
|---|---|---|---|
| M15 | bullish EMA bias; above last swing high; `HH_HL_UP` | bullish EMA bias; above last swing high; `HH_LL_EXPANSION` | Same high-range short-into-strength state; local pivot label differs. |
| H1 | mixed bias; inside swing range; `HH_HL_UP` | mixed bias; inside swing range; `LH_HL_COMPRESSION` | Same broad location; local sequence differs. |
| H4 | mixed bias; inside swing range; `HH_HL_UP` | mixed bias; inside swing range; `LH_LL_DOWN` | Very close feature neighborhood despite different pivot label. |
| D1 | bullish; `HH_HL_UP`; inside swing range | identical three labels | Nearly interchangeable daily context. |

Material numeric differences do not form a coherent winner rule:

- M15 ADX was stronger for the winner (`50.10` versus `21.48`), but both
  entries were near the top of their 20-bar range (`0.980` versus `0.971`).
- The last closed M15 body was bearish for C09 (`-0.299 ATR`) and bullish for
  C10 (`+0.661 ATR`). This is a pair observation, not a population rule.
- H1 ten-bar return was more bullish for C09 (`+2.497 ATR`) than C10
  (`+0.417 ATR`).
- H4 ten-bar return was almost flat for C09 (`+0.055 ATR`) but strongly
  negative for C10 (`-2.273 ATR`), yet C10 was the losing short. A simple
  "more bearish H4 is better for shorts" story fails on this pair.
- D1 EMA20 slope was almost identical (`0.4442` versus `0.4452 ATR`) and the
  prior closed daily candle was bearish by about `-0.69 ATR` in both cases.

The pair therefore contradicts a simple HTF-alignment explanation: C09 won
despite stronger local bullish momentum, while C10 lost despite the more
bearish H4 ten-bar return.

## Population check: does the apparent difference generalize?

The largest univariate separation across all 44 features is
`H4_entry_vs_ema20_atr`, AUC `0.5385`, SMD `0.133`. The next four features have
AUC only `0.5370`, `0.5354`, `0.5348` and `0.5345`. These are noise-level
separations, not a usable decision rule.

The categorical population results also reject an easy pivot/bias rescue:

| Layer | Best measured state | N | PF in R | Expectancy R/trade |
|---|---|---:|---:|---:|
| M15 | `HH_LL_EXPANSION` pivot | 580 | 0.871 | -0.071 |
| H1 | bullish EMA bias | 709 | 0.980 | -0.011 |
| H4 | bullish EMA bias | 676 | 0.953 | -0.026 |
| D1 | bullish EMA bias | 598 | 0.886 | -0.064 |

For the pair's exact pivot labels, C09's M15/H1/H4 states have PF
`0.819/0.891/0.906`; C10's corresponding states have PF
`0.871/0.826/0.680`. All are below 1. The daily label is identical and its PF
is `0.752`. Selecting the winner's labels after seeing the result would be an
unsupported same-sample filter.

## Independent Grok Build CLI audit

Grok `grok-4.5` completed the frozen artifact audit in session
`019f7986-ae9d-7623-88a2-4cd2c33e3e8a` with `stopReason=EndTurn`. Two earlier
cancelled responses were rejected. Its independent conclusion matches the
local result: closed-bar leakage check PASS; D1/combined similarity ranks
`1/11`; maximum population AUC `0.538`; HTF context does not materially
distinguish C09 from C10; HYP-011 stays terminal.

## Chart evidence

Point-in-time charts, with no current incomplete HTF candle:

- `02. AlphaFactory/runtime/ictfvg_hyp011_htf_pair/charts_M15_asof/`
- `02. AlphaFactory/runtime/ictfvg_hyp011_htf_pair/charts_H1_asof/`
- `02. AlphaFactory/runtime/ictfvg_hyp011_htf_pair/charts_H4_asof/`
- `02. AlphaFactory/runtime/ictfvg_hyp011_htf_pair/charts_D1_asof/`

The D1 pair visually shows the same rising structure, similar pullback and the
same bullish EMA/pivot state. H4 and H1 show local sequencing differences but
not a different regime. M15 is the most different layer, mainly in trend
strength and the last closed candle.

## Interpretation boundary and next research implication

This result falsifies only the claim that these two outcomes are readily
explained by the measured closed-bar M15/H1/H4/D1 context. It does not prove
that all higher-timeframe context is useless. Unmeasured candidates include
intrabar/order-flow path, exact liquidity-pool hierarchy, time since raid,
cross-asset state and post-entry microstructure; none is established here.

Any future attempt to test those candidates must be a fresh preregistered
object on new/OOS evidence. It may not select thresholds from C09/C10 or rerun
HYP-011 as a rescue.

Reproducible outputs:

- `02. AlphaFactory/runtime/ictfvg_hyp011_htf_pair/pair_htf_forensics.json`
- `02. AlphaFactory/runtime/ictfvg_hyp011_htf_pair/short_cohort_htf_features.csv`
- `02. AlphaFactory/runtime/ictfvg_hyp011_htf_pair/manifest.json`
- `research/evidence/HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011_HTF_PAIR_GROK_RECEIPT.json`
