# HYP-LOMX-MULTI-M1-002 — TRAIN Readout

Terminal verdict: **TRAIN_KILL_NO_ELIGIBLE_ARM**  
Economic layer: engineering-valid TRAIN proxy; not validation and not
promotion-grade cost evidence.  
Later data: 2021-2024 validation and 2025-current holdout were not accessed.

## Outcome

No selectable setup survived.  Population and cadence were healthy, but the
London 08:00-to-08:30 sign had no positive gross edge across the frozen matrix.
The best gross result was GBPUSD MIDDAY at PF 1.000755; the frozen x1 cost proxy
reduced it to PF 0.892719.  Every selectable arm had negative x1 expectancy,
Holm-adjusted p=1.0, and DSR effectively zero.

| Selectable arm | N | Trades/week | Gross PF | PF x1 | PF x1.5 | PF x2 | Positive years | Min LOO PF x1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EURUSD MIDDAY | 1,274 | 4.889 | 0.9097 | 0.8287 | 0.7910 | 0.7550 | 0/5 | 0.8017 |
| EURUSD LATE_FIX | 1,274 | 4.889 | 0.9241 | 0.7653 | 0.6968 | 0.6349 | 0/5 | 0.7363 |
| EURUSD FULL_SESSION | 1,274 | 4.889 | 0.8896 | 0.8383 | 0.8139 | 0.7902 | 0/5 | 0.7990 |
| GBPUSD MIDDAY | 1,281 | 4.916 | 1.0008 | 0.8927 | 0.8434 | 0.7970 | 0/5 | 0.8686 |
| GBPUSD LATE_FIX | 1,281 | 4.916 | 0.9763 | 0.7658 | 0.6783 | 0.6011 | 0/5 | 0.7386 |
| GBPUSD FULL_SESSION | 1,281 | 4.916 | 0.9320 | 0.8690 | 0.8392 | 0.8104 | 1/5 | 0.8403 |
| EURJPY MIDDAY | 1,290 | 4.951 | 0.9286 | 0.8167 | 0.7662 | 0.7191 | 0/5 | 0.8065 |
| EURJPY LATE_FIX | 1,290 | 4.951 | 0.8669 | 0.6403 | 0.5519 | 0.4769 | 0/5 | 0.6127 |
| EURJPY FULL_SESSION | 1,290 | 4.951 | 0.9266 | 0.8514 | 0.8163 | 0.7828 | 1/5 | 0.8149 |
| USDJPY MIDDAY | 1,283 | 4.924 | 0.8864 | 0.7866 | 0.7412 | 0.6987 | 0/5 | 0.7408 |

Required PF gates were x1 >1.30, x1.5 >=1.25, and x2 >=1.00.  All ten arms
failed all three.  XAUUSD's three external-null arms had x1 PF
0.7174/0.6408/0.7399 and were never selectable.  Four reverse controls were
near PF 1 after x1 cost, but none approached 1.30 and none had selection
authority; selecting one now would be post-hoc rescue.

## Source and cost fidelity

- 6,467 complete broker-Bid M1 symbol-days, TRAIN 2016-2020 only.
- Date coverage by symbol: 98.70%-99.31%.
- Raw positive historical-spread coverage: 92.63%-99.86%.
- 1,057 nonpositive endpoint fields were replaced by the prospectively frozen
  same-symbol positive-spread q95 rule.
- Cost proxy: `1.25 * max(entry spread, exit spread) * point`, stressed at
  x1/x1.5/x2.  Commission and slippage are not claimed; therefore the result is
  sufficient to kill this negative object but could never promote a survivor.

## Evidence interpretation

The yearly heatmap and cumulative curves show broad multi-year decay rather
than one isolated bad year.  Every leave-one-year-out PF is below 1.  All ten
Holm-adjusted sign-flip p-values equal 1.0; maximum 23-trial DSR is 0.000007.
The result is therefore not a narrow cost-only miss around PF 1.30: most arms
already have gross PF below 1.

## Failure radius and next legal move

Killed object: exact Europe/London 08:00-to-08:30 sign, frozen primary
polarities, MIDDAY/LATE_FIX/FULL_SESSION exits, eligible FX matrix, XAU nulls,
reverse controls, and the frozen research-cost contract on 2016-2020 broker
data.

Forbidden rescue: choose the least-bad symbol/set/year, flip direction, lower
cost, add an indicator/filter/threshold, shift the exit, or open 2021+ based on
this readout.  A future ID must introduce an independently justified new
information mechanism or decision surface; this kill does not claim every
London-open or intraday mechanism lacks edge.

## Artifact index

- `evidence/HYP-LOMX-MULTI-M1-002/LOMX002-TRAIN-EVAL-001/train_terminal.json`
- `evidence/HYP-LOMX-MULTI-M1-002/LOMX002-TRAIN-EVAL-001/train_metrics.json`
- `evidence/HYP-LOMX-MULTI-M1-002/LOMX002-TRAIN-EVAL-001/evaluator.log`
- `evidence/HYP-LOMX-MULTI-M1-002/LOMX002-TRAIN-EVAL-001/artifact_manifest.json`
- `evidence/HYP-LOMX-MULTI-M1-002/LOMX002-TRAIN-EVAL-001/charts/`

The artifact manifest independently reconciles eight generated artifacts with
zero hash or size mismatch.  Grok's bounded forensic advice informed the
pre-outcome external-null/failure-radius framing; its worker packet failed the
local result-packet validator, so no Grok output was accepted as execution
authority or economic evidence.
