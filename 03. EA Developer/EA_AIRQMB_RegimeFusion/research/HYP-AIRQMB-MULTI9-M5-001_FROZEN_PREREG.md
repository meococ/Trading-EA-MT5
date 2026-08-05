# HYP-AIRQMB Multi-9 M5 — Frozen Preregistration

Frozen on 2026-08-05 UTC before any Strategy Tester performance launch for this EA source identity.

## Economic question

Does a semantically routed three-indicator ensemble have positive, cost-resilient expectancy on each ordered M5 symbol cell when AIRD selects market context, MBB supplies the context-specific setup and QQE confirms direction?

This is a new owner-directed mechanism. It is not a rescue, retune or continuation of any killed LOMX, compression-breakout, regime mean-reversion or prior T2 identity.

## Ordered cells

| Order | Hypothesis ID | Symbol | Magic |
|---:|---|---|---:|
| 1 | `HYP-AIRQMB-EURUSD-M5-BASE-001` | EURUSD | 5686101 |
| 2 | `HYP-AIRQMB-USDJPY-M5-BASE-001` | USDJPY | 5686102 |
| 3 | `HYP-AIRQMB-GBPUSD-M5-BASE-001` | GBPUSD | 5686103 |
| 4 | `HYP-AIRQMB-USDCHF-M5-BASE-001` | USDCHF | 5686104 |
| 5 | `HYP-AIRQMB-USDCAD-M5-BASE-001` | USDCAD | 5686105 |
| 6 | `HYP-AIRQMB-AUDUSD-M5-BASE-001` | AUDUSD | 5686106 |
| 7 | `HYP-AIRQMB-NZDUSD-M5-BASE-001` | NZDUSD | 5686107 |
| 8 | `HYP-AIRQMB-XAUUSD-M5-BASE-001` | XAUUSD | 5686108 |
| 9 | `HYP-AIRQMB-BTCUSD-M5-BASE-001` | BTCUSD | 5686109 |

Each row is an independent economic cell. An aggregate result cannot hide a failed symbol. Missing/insufficient history is a data-invalid cell, not a pass and not an economic failure.

## Bound implementation

- Source SHA-256: `A0622C7BCB22F1DBAABD707B1159679283D6B2C1AD0CFE642C5301E4573B1A81`
- EX5 SHA-256: `3F7824E9ABEDD4CC094B66EA5A747673A335E23AB9D3A7CAB83CD269ED810A84`
- Contract SHA-256: `1FDC453718A1D306AB67D686AAD4B96B892A9B45400CF267136A4071211C81E5`
- Compile result: `0 errors, 0 warnings`
- Non-repaint audit: `PASS`
- Indicator runtime hashes and exact logic are frozen in `HYP-AIRQMB-MULTI9-M5-001_LOGIC_MATRIX.md`.

## Splits and access order

| Split | Dates | Access contract |
|---|---|---|
| Training baseline and any authorized optimization | `2023.01.02`–`2024.12.31` | open now, one baseline run per ordered cell |
| Validation | `2025.01.01`–`2025.12.31` | locked until one parameter choice is frozen from training only |
| Holdout | `2026.01.01`–`2026.07.31` | locked until the same frozen choice independently passes validation |

Primary model is MT5 Model 0, every tick based on real ticks. Deposit/leverage are `100000 USD / 1:100`. Required history quality is strictly above `97%`, with tester journal bounds and synchronized series proof retained per cell.

## Frozen baseline

All source defaults are authoritative. Per-cell runtime overrides change only identity fields:

```text
InpExpectedSymbol=<SYMBOL>;InpHypothesisId=HYP-AIRQMB-<SYMBOL>-M5-BASE-001;InpMagic=<MAGIC>;InpResearchAutoMode=true;InpVariantTag=BASELINE_FROZEN
```

Execution-critical defaults included in the source contract are: risk `0.25%`, AIRD confidence `0.45`, stop `1.00` MBB half-width, target `1.50R`, spread/stop `<=0.15`, three entries/day, 5-bar cooldown, 48-bar max hold, `07:00–20:00 UTC` entry window, daily/Friday flat at `20:00 UTC`, daily lock `3.5%`, peak DD lock `8%`, S1/S2/S3 enabled and lifecycle-v3 telemetry enabled.

## Baseline gates per symbol

Fatal gates are evaluated independently:

1. compile `0/0`, source/indicator/prereg hashes, non-repaint audit, report/deal/lifecycle reconciliation and expected symbol identity must match;
2. history quality `>97%`, exact date bounds and Model 0 must be proven;
3. at least `2.0` and at most `5.0` completed trades per elapsed calendar week;
4. base Profit Factor `>=1.30`, maximum equity drawdown `<=8%`, both long and short each at least `20%` of completed lifecycles;
5. independently repriced PF `>=1.25` at 1.5x costs and `>=1.00` at 2x costs;
6. no overnight/weekend exposure, foreign-position mutation, duplicate/missing final close or nonpositive initial risk.

A baseline failure kills that symbol's baseline and blocks optimization under this mechanism. A pass authorizes only the training grid below; it is not economic confirmation or promotion.

## Preregistered training optimization for baseline survivors only

Exactly nine combinations, no other tuning:

- `InpMinAIConfidence`: `{0.35, 0.45, 0.55}`
- `InpRewardRisk`: `{1.25, 1.50, 1.75}`
- `InpStopHalfWidthMult`: fixed `1.00`
- every other input and all three indicator inputs remain frozen.

Selection is by stable region, not the highest isolated PF: a candidate must pass the fatal gates, have at least two adjacent grid neighbors with positive expectancy, and be selected by the best median neighbor-group expectancy after costs. Ties choose the more conservative higher-confidence and lower-R target. Total trial count is nine per baseline survivor and must feed DSR/trial accounting.

After selection, the chosen parameter pair is frozen before validation. No symbol pooling, post-result session/weekday/year filter, indicator retune, lane removal, direction inversion or stop-multiplier search is allowed.

## Reporting states

- `engineering-valid`: compiled, initialized, indicator contract and telemetry reconciliation pass.
- `economic-valid`: training selection, validation and holdout independently pass all economic gates after costs and multiple-testing accounting.
- `promotion-ready`: remains false until later WFA/CPCV, DSR, Monte Carlo, cross-symbol exposure and paper-forward gates pass.

