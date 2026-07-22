# HYP-006 XAUUSD M5 Model-0 Readout

## Verdict

`INVALID_ENGINEERING_RUN` / `PARK_INVALID_HISTORY_QUALITY_98_BELOW_FROZEN_99_GATE`.

The Owner-directed XAUUSD transfer pair executed exactly once per frozen arm,
but the MT5 report delivered only 98% history quality. The preregistration
required at least 99%. Therefore neither arm is an authoritative economic
backtest, and the pair cannot produce `DIAGNOSTIC_COMPLETE_NO_PROMOTION` or a
valid no-edge kill. No third run or post-outcome repair is authorized.

The available-history shape is nevertheless clearly adverse: the challenger
has PF below 1, negative expectancy, cadence above the frozen ceiling, negative
P/L in eight of nine calendar-year buckets, one profitable fixed-parameter OOS
slice out of five, robustness 1/7, and a failed equity audit. These values are
reported only so the invalid run is not mistaken for hidden positive evidence.

## Frozen contract and engineering evidence

- Hypothesis: `HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006`
- Requested window: `2018.01.01--2026.07.21`, XAUUSD M5, Model 0.
- One matched pair only: control `InpSignalMode=0`, challenger
  `InpSignalMode=1`.
- Deposit/leverage/risk: USD 100,000 / 1:100 / 0.01% per accepted entry.
- Frozen XAU geometry: 2 digits, point/pip 0.01, maximum spread 35 points,
  structure buffer 40 points.
- Closed-bar local MACD-histogram extremum, ATR-normalized delta, EMA200,
  RSI14, ADX14, five-bar cooldown, 1.6R target, 15-bar timeout, BE OFF.
- News guard uniformly OFF because the embedded EUR/USD 2019--2022 calendar
  is not point-in-time XAU/full-window evidence.
- Package tests: 18/18. AlphaFactory compile: 0 errors / 0 warnings.
- Exact-source non-repaint audit V6: PASS, zero findings.
- Actual tester identity: 601,621 bars / 560,751,415 ticks / 98% history,
  data fingerprint
  `2D717432F539F429BDD89AB5A00712D2169942BD70891D39DE7D585F904DB448`.

## Diagnostic-only matched results

| Arm | Run | Trades | Trades/week | PF | Net | Expectancy | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|
| Control | `20260721_185854` | 10,281 | 23.044 | 0.8135 | -$7,863.03 | -$0.7648 | 7.8944% |
| MZMS challenger | `20260721_190051` | 5,078 | 11.382 | 0.7994 | -$4,483.77 | -$0.8830 | 4.5525% |

The challenger removes 5,203 trades and lowers total loss/drawdown, but PF
deteriorates by 0.0141 and expectancy deteriorates by $0.1182 per trade. The
smaller aggregate loss is an activity effect, not evidence of an edge.

Both directions lose after lifecycle commission:

| Direction | Trades | PF | Net |
|---|---:|---:|---:|
| SELL | 2,305 | 0.8211 | -$1,851.38 |
| BUY | 2,773 | 0.7806 | -$2,632.39 |

## Challenger calendar-year diagnostics

| Year | Trades | PF | Net |
|---|---:|---:|---:|
| 2018 | 584 | 0.5982 | -$1,229.92 |
| 2019 | 636 | 0.6690 | -$1,026.39 |
| 2020 | 651 | 0.7951 | -$581.44 |
| 2021 | 668 | 0.7959 | -$585.09 |
| 2022 | 648 | 1.0314 | +$83.65 |
| 2023 | 656 | 0.8074 | -$553.30 |
| 2024 | 648 | 0.8562 | -$390.56 |
| 2025 | 553 | 0.9270 | -$151.98 |
| 2026 | 34 | 0.6674 | -$48.74 |

The isolated 2022 positive bucket is descriptive only and cannot authorize a
year veto or subgroup rescue.

## Validation diagnostics

- Unified validation: `REVIEW`, 4/14 gates pass; profit/cost gates are blocked
  by unverified execution-cost provenance.
- Cadence: FAIL at 11.382 trades per elapsed requested-window week versus the
  frozen 2--5 range.
- Fixed-parameter chronological slicing: 1/5 profitable OOS windows; this is
  diagnostic-only, not promotion-grade WFA.
- Robustness proxy: 1/7 tests pass; bootstrap PF 95% interval is approximately
  0.749--0.849.
- Monte Carlo: P95 max DD 4.6765%, but 100% of shuffled paths finish below
  starting equity because sequence randomization preserves total loss.
- Equity audit: FAIL; 2,919 days without a new equity high, 74.2% losing
  months, median trade -$4.24.
- Lifecycle: 10,156 rows = exactly two rows for each of 5,078 challenger
  positions; lifecycle net P/L reconciles to the report with a $0.00 gap.
- Non-repaint: PASS on the exact run snapshot.

## Evidence

- Control run: `02. AlphaFactory/runs/EA_MZMS_Scalper/20260721_185854`
- Challenger run: `02. AlphaFactory/runs/EA_MZMS_Scalper/20260721_190051`
- Chart: `02. AlphaFactory/runs/EA_MZMS_Scalper/20260721_190051/analysis/analysis_charts.png`
- Validation: `02. AlphaFactory/runs/EA_MZMS_Scalper/20260721_190051/analysis/validation_summary.json`
- Matched comparison: `02. AlphaFactory/runs/EA_MZMS_Scalper/20260721_190051/analysis/candidate_compare.json`
- Lifecycle reconciliation:
  `research/evidence/HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_LIFECYCLE_RECONCILIATION.json`

No parameter/session/day/year/direction filter, BE/intrabar change, symbol
fallback, third run, optimization, paper, promotion or live action is
authorized from this invalid pair. A future XAU test needs a fresh hypothesis
and a pre-run data source capable of satisfying the frozen history gate.

## Post-run random-loser chart forensics

Two independent Grok CLI workers later inspected two disjoint, seed-fixed
samples of 20 challenger losers each using separate decision and outcome chart
packets. Their convergent diagnostic observation is a frequent late/mature
impulse entry shape, followed by either rapid adverse movement or no
follow-through into the 15-bar timeout. The review also rejects "tight stop"
as an established general cause because the source chooses the farther of the
structural and 1.5-ATR stops.

This does not change the verdict or authorize a repair. See
`research/evidence/HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_GROK_RANDOM_LOSER_FORENSICS/INTEGRATED_READOUT.md`.
