# HYP-VRAS-EURUSD-M5-003 - terminal Model-0 readout

## Verdict

`KILL_MODEL0_NEGATIVE_EXPECTANCY_UNDER_CADENCE_REGIME_WHIPSAW`.

This verdict kills the exact seven-gap VRAS object tested on EURUSD M5 with
the frozen 2019-2022 primary tick-volume/London-anchor settings. It does not
claim that every VWAP, AVWAP or regime strategy lacks edge. No sensitivity
arm, optimizer or post-result session/day/year veto is authorized.

## Bound result

| Metric | Result | Frozen requirement |
|---|---:|---:|
| History quality | 100% | Model 0 |
| Bars / ticks | 298,267 / 79,411,093 | evidence |
| Trades | 93 | >=350 |
| Trades / elapsed week | 0.4465 | 2-5 |
| Net profit | -$5,243.22 | positive |
| Profit factor | 0.591354 | >=1.30 diagnostic |
| Win rate | 34.4% | informational |
| Expectancy | -$56.38/trade | positive |
| Average realized R | -0.230972R | positive |
| Max drawdown | 5.6684% | <=6% |

Only the drawdown ceiling passed. The first trade was 2019-01-03 and the last
was 2020-06-04; 31 of 48 calendar months were inactive. Later opportunities
are recorded only as aggregate `ENTRY_GUARD_REJECT`, so telemetry cannot
separate the persistent account-DD guard from the other guard terms. This is
an observability limitation, not permission to rerun.

## Mechanism and path forensics

- 2,546 entry attempts: 1,998 entry-guard rejects, 455 K=8 cost-distance
  rejects and 93 accepted orders. No geometry/sizing/OrderCheck rejection.
- Regime switches: 10,090, or 6.92 per elapsed calendar day. This breaches the
  preregistered >4/day whipsaw red flag despite 25/19 hysteresis and six-bar
  dwell.
- Trend: 83 trades, 28 wins, PF 0.6412, net -$4,152.31.
- Range: 10 trades, 4 wins, PF 0.1331, net -$1,090.91.
- Long: 51 trades, PF 0.5607, net -$3,153.00. Short: 42 trades, PF 0.6302,
  net -$2,090.22. The failure is not isolated to one branch or direction.
- Exit anatomy: 13 target exits (+$4,962.74), 55 stop exits (-$12,213.14) and
  25 safety/time exits (+$2,007.18). Full-stop frequency dominates the payoff.
- 2019: 26 trades, PF 0.8420, net -$441.32. 2020: 67 trades, PF 0.5216,
  net -$4,801.90. There are no trades after June 2020.

The automatic analyzer's suggestions to disable weak sessions, hours, days or
2020 are explicitly rejected as post-hoc rescue.

## Validation

- Source tests: 13/13 PASS.
- AlphaFactory compile: 0 errors / 0 warnings.
- Exact run-snapshot non-repaint audit: PASS, zero findings.
- Lifecycle reconciliation: 93 OPEN + 93 final CLOSE across 93 position IDs;
  lifecycle net equals report net exactly at -$5,243.22.
- Unified validation: REVIEW, only 5/14 numeric/artifact gates.
- Walk-forward: not produced because 93 trades are insufficient for five
  windows.
- Robustness: 0/7 PASS; bootstrap PF 95% CI 0.352-0.930 and random benchmark
  percentile 0.7%.
- Monte Carlo 1,000 permutations: P(below start)=100%, p95 DD=6.8%, worst
  DD=8.6%; both breach the frozen 6% risk ceiling.
- Equity audit: FAIL; 76.5% losing months, median trade -$213.35, 223-day flat
  period and 73 trades to recover max DD.
- No overnight/weekend exposure: PASS.
- Strict execution reconciliation remains BLOCKED because generic TCA does not
  consume this lifecycle schema and no independent slippage samples exist.

Cost truth is also blocked: 366,196 of 1,491,312 historical spread rows are
zero (24.55%), commission is assumed at 0.70 pip and slippage at 0.40 pip each
way. Therefore even the already-negative PF is diagnostic-only; there is no
promotion/live claim and no delivery PASS.

## Bound artifacts

- Run: `02. AlphaFactory/runs/EA_VRAS_RegimeAdaptiveScalperV3/20260722_103759`
- Source SHA256: `EAFB0A5962E79D7543CA7039F3C4B8597644D591CBFD08C9B19BD93B19FCD3B7`
- Report SHA256: `696826EDEFBD3E03A36DFDBFA67C7750027417EAE705F8855E93F3688193278A`
- Run manifest SHA256: `6561429364CFB449F100B5F5D2702B667722598C6F5AB67A9A62A8321137CA90`
- Validation SHA256: `F587DCF7DD9D82DABBB44D126B611DD6174702DC733C895E7B60B1D9BCCEA043`
- Lifecycle reconciliation:
  `research/evidence/HYP-VRAS-EURUSD-M5-003_LIFECYCLE_RECONCILIATION.json`

## Grok real-chart forensics addendum

On 2026-07-22, a mechanically frozen 10-position sample was rendered as ten
hash-bound `3240x2160` combined forensic PNGs. Two serial Grok 4.5 jobs opened
and reported all 10/10 images with exact case/position coverage and schema-valid
responses. Parent reconciliation keeps the terminal KILL verdict.

The chart anatomy supports four failure descriptions: zero-MFE Trend stopouts,
MFE-without-target reversals to stop, incomplete Range mean reversion, and ADX
hysteresis labels that remain code-consistent while lagging the current reading.
Clean winners require continuation after the same local gate stack that also
appears in losers. A matched Trend-long pair suggests higher-timeframe path
continuity only as a low/medium-confidence future research lead, not a filter.

Important fidelity correction: chart price alignment must use broker
`server_time`. The D-side parquet `time_utc` convention differs from the EA
telemetry clock by one hour during DST transition weeks and otherwise places
fills on the wrong candles. The integrated readout and hard QC are under:

`research/evidence/HYP-VRAS-EURUSD-M5-003_GROK_CHART_FORENSICS_10/`

### Indicator-rich 100-image census

Owner then expanded the visual review to 100 images. Because the run contains
only 93 executed positions, the corpus uses the complete 93-trade census plus
seven mechanically selected `COST_DISTANCE_REJECT` diagnostics explicitly
marked `NOT TRADED`; the rejects are excluded from every economic statistic.
Each chart shows continuous session VWAP/SD, shadow VWAP, confirmed AVWAP when
active, ADX14 hysteresis, RSI14, ATR14/SD floor and the active M15 or Range-bias
panel. All 100 entry snapshots pass exact 9/9 telemetry parity.

Grok 4.5 autonomously reviewed 20 serial five-image packets and produced one
final synthesis. Hard acceptance confirms 100/100 images opened, 20/20 packet
results, exact case-ID reconciliation and 100 parity manifests checked. The
review confirms the existing failure anatomy rather than changing the verdict:
55 stop exits overwhelm 13 target exits, Trend and Range remain negative, the
same decision-time VWAP/AVWAP/M15 fingerprints occur in winners and losers,
ADX hysteresis is code-consistent but the population still switches regime
about 6.92 times per elapsed day, and the cost-distance gate explains rejected
funnel cases without creating counterfactual PnL.

Validated report and QC:

`research/evidence/HYP-VRAS-EURUSD-M5-003_GROK_CHART_FORENSICS_100/`

Terminal verdict remains
`KILL_MODEL0_NEGATIVE_EXPECTANCY_UNDER_CADENCE_REGIME_WHIPSAW`; no tuning,
session/year veto, rerun, source rescue, promotion or live authority follows
from the visual review.
