# HYP-005 Full-History Model-0 Diagnostic Readout

## Verdict

`KILL_DIAGNOSTIC_FULL_HISTORY_CONFIRMS_NO_EDGE`

The Owner-directed EURUSD M5 backtest from 2018-01-01 through 2026-07-21 is
complete. The MZMS challenger is economically negative on the complete tested
window and in every calendar-year bucket. It reduces activity and drawdown
relative to the matched control, but does not create positive expectancy.

This is a post-outcome diagnostic of the already-terminal V1 family. It cannot
rescue or promote HYP-003. No optimization, subgroup veto, parameter change,
paper deployment, or live deployment is authorized.

## Frozen contract

- Hypothesis: `HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-005`
- Instrument/timeframe: FivePercent `EURUSD`, `M5`
- Tester model: MT5 Model 0 / real ticks
- Requested dates: `2018.01.01` through `2026.07.21`
- Deposit/leverage: USD 100,000 / 1:100
- Risk: 0.01% per trade
- Signal: 100% closed-bar; local MACD-histogram extremum plus ATR-normalized
  delta, RSI mid-zone/direction, EMA200 bias, ADX, five-bar cooldown
- Exit: farther five-bar/1.5-ATR stop, 1.6R target, 15-bar maximum hold
- Break-even/intrabar evaluation: OFF
- Entry spread ceiling: 0.8 pip
- News guard: uniformly OFF in both arms because the embedded calendar covers
  only 2019--2022 and otherwise fails closed outside that range
- Costs: MT5 report-native spread/commission are present, but independent
  broker execution-cost provenance and slippage samples remain unverified;
  the run is diagnostic-only

Preregistration SHA256:
`BE47DF4A8F93CC4A11335AA7B6A93A808FEFF55C9A5CBAC7D7C5D956D635FE45`.

Canonical source SHA256:
`782C57D5122B1204097121D8994CDA724ED6656E6A4D7ABB1BBA4D1739D72494`.

Engineering gate: 18/18 package tests, AlphaFactory compile 0 errors / 0
warnings, and exact-snapshot non-repaint PASS with zero findings. Non-repaint
audit SHA256:
`E497E7DF59DB4CE09E784A93E4616E02EFF875AFFF75F4AEB8B9AECE2AF5C67E`.

## Invalid predecessor excluded

HYP-004 run `20260721_164451` is rejected as engineering evidence. A USD
10,000 diagnostic deposit hit the FivePercent money-mode stop-out boundary
after only 125 M5 bars, 19,102 ticks, and one trade on 2018-01-02. It did not
cover the requested window; its one-trade PF/profit/drawdown are non-authoritative.
HYP-005 changed only hypothesis identity, deposit to the established USD
100,000 diagnostic level, and receipt-authority completeness.

## Valid Model-0 evidence

Both valid runs cover 636,830 M5 bars and 206,612,810 ticks with MT5-reported
99% history quality and no tester stop-out.

| Arm | Run | Trades | Trades/week | PF | Net P/L | Expectancy/trade | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Matched control | `20260721_165401` | 8,979 | 20.125 | 0.8126 | -$7,942.38 | -$0.8846 | 7.9990% |
| MZMS challenger | `20260721_165515` | 4,678 | 10.485 | 0.8253 | -$4,363.87 | -$0.9328 | 4.4428% |

Relative to control, the challenger makes 4,301 fewer trades, loses $3,578.51
less in total, improves PF by only 0.0127, and lowers maximum drawdown by 3.5562
percentage points. Per-trade expectancy worsens by $0.0483. Relative loss
reduction is therefore an activity effect, not evidence of an edge.

## Lifecycle reconciliation

- Control: 17,958 lifecycle data rows = exactly two rows for each of 8,979
  positions; paired net P/L equals the report at `-$7,942.38`.
- Challenger: 9,356 lifecycle data rows = exactly two rows for each of 4,678
  positions; paired net P/L equals the report at `-$4,363.87`.
- Challenger net-of-commission lifecycle win rate: 40.04%.
- RunMeta covers all 636,830 bars and records 4,678 attempted/opened entries,
  1,249 spread rejections, 195 cooldown rejections, and zero news rejections
  under the frozen news-disabled contract.
- Generic TCA/execution reconciliation remains blocked because this lifecycle
  schema has no slippage samples. The exact position-count and P/L reconciliation
  above is independently reproduced from the raw lifecycle sidecar and does not
  convert the run into promotion-grade execution evidence.

## Challenger results by calendar year

P/L and PF below are reconstructed from the paired OPEN/CLOSE lifecycle rows,
including entry commission. Every observed year loses.

| Year | Trades | Net P/L | PF | Net win rate |
|---:|---:|---:|---:|---:|
| 2018 | 519 | -$520.94 | 0.8183 | 39.88% |
| 2019 | 456 | -$328.42 | 0.8697 | 41.45% |
| 2020 | 653 | -$332.56 | 0.9016 | 41.04% |
| 2021 | 655 | -$995.76 | 0.7265 | 37.25% |
| 2022 | 614 | -$260.77 | 0.9168 | 41.53% |
| 2023 | 562 | -$527.72 | 0.8207 | 40.93% |
| 2024 | 443 | -$370.31 | 0.8416 | 41.31% |
| 2025 | 500 | -$616.79 | 0.7674 | 38.80% |
| 2026 YTD | 276 | -$410.60 | 0.7268 | 37.32% |

Both Europe and New York sessions lose; all five weekdays lose. These are
diagnostics only and must not be used for post-hoc hour/day/year exclusions.

## Validation and robustness

- Unified validation: `REVIEW`, 5/14 gates passed. Cadence, PF, cost stress,
  robustness, equity audit, execution reconciliation, and invocation freshness
  did not pass or were blocked.
- Frozen cadence gate: 10.485 trades per elapsed calendar week versus required
  2--5.
- Fixed-parameter temporal diagnostic: only 1/5 OOS windows profitable; average
  IS PF 0.82 and average OOS PF 0.86. This producer is diagnostic-only.
- Robustness suite: 1/7 tests passed; bootstrap PF 95% CI is 0.773--0.879 and
  random-benchmark percentile is 0.
- Monte Carlo sequence randomization: P95 drawdown 4.6365%, worst 4.9673%; all
  paths finish below starting equity because sequence randomization preserves
  the negative total P/L.
- Equity audit: FAIL; 3,118 days without a new equity high, 73% losing months,
  and median trade `-$7.80`.

## Evidence bindings

- Control run directory: `02. AlphaFactory/runs/EA_MZMS_Scalper/20260721_165401`
  - report SHA256: `DAD8ED695C002CED7BE4E7B7297E8079D5525662AAF60EB7A8D175E0F2B49BA7`
  - manifest SHA256: `EF313959BA9D395F0736DADA810B79FDC3845FBC4BC49AF0D14534E0912B21D5`
  - validation SHA256: `E1DAFB15C58553C2EB5939B05FAE15DD6D86013D2938F10A4369638E1D01F5EF`
- Challenger run directory: `02. AlphaFactory/runs/EA_MZMS_Scalper/20260721_165515`
  - report SHA256: `07A2A64948D68986964F342559A662E739FCFD9869E88AF8595F464618C2CC97`
  - manifest SHA256: `A21AAA5556011621CC23C43F21528C161086406267E022E198AF8FE1A4AE7E58`
  - validation SHA256: `7AB29E4CFB2BB8865FD387FF2170757D45DF77E7189E86D442A6D48A49DCC2E6`
  - lifecycle SHA256: `DD6F716293F12F4E984BA25F1AB391B31844680BE4C323BDA59D5CFAAFC73193`
  - RunMeta SHA256: `4787836C85D561DC9ACB28BA0AD1B67E27B177DA42B46BC581A659620909882D`
  - candidate comparison SHA256: `B9CD89184938E77E5921CE961202933DA51974EC6512CDCEFE8648294FAD66BC`

## Terminal decision

The full-history Model-0 diagnostic confirms the frozen offline kill rather
than contradicting it. HYP-005 is terminal `killed`, HYP-003 remains terminal,
and the current source is retained only for reproducibility and audit. Do not
repeat this exact family with intrabar evaluation, weaker local-extremum/delta
rules, break-even/trailing, selected hours/days/years/directions, parameter
sweeps, or another symbol. A future build requires a materially new causal
information set and a fresh preregistered hypothesis.
