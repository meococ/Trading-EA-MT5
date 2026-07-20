# HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011 - diagnostic readout

Verdict: **INVALID_DIAGNOSTIC_HISTORY_QUALITY_99_PERCENT**  
Promotion eligible: **false**

## Outcome

The Owner-requested EURUSD M5 Model-0 run covered `2018.01.01-2026.07.19`
with the high-recall control, 0.01% micro-risk, no effective account-DD stop and
the news guard consistently disabled. It completed 636,544 bars and 206,517,809
ticks, opened and finally closed 4,341 positions, and reached the last Friday
before the requested Sunday cutoff.

The economic observation is decisively negative: PF `0.7588088983`, net
`-5,801.70`, win rate `46.9016%`, balance DD `6.0144%` at micro-risk and
`-0.13775R` expectancy across the 4,340 positions with defined initial-risk
telemetry. Cadence is `9.7363` trades per elapsed calendar week, above the
workspace target band. Every calendar year has PF below 1.0 after lifecycle
commission, including 2022 and 2023 which looked slightly positive before the
entry-side commission was included.

## Yearly lifecycle result

| Entry year | Trades | Net | PF | Win rate | Expectancy R |
|---:|---:|---:|---:|---:|---:|
| 2018 | 516 | -290.29 | 0.893953 | 49.806% | -0.057090 |
| 2019 | 517 | -1,385.14 | 0.572721 | 42.360% | -0.270521 |
| 2020 | 518 | -432.58 | 0.844874 | 48.069% | -0.085056 |
| 2021 | 520 | -808.67 | 0.729237 | 45.577% | -0.159458 |
| 2022 | 516 | -130.62 | 0.949676 | 50.194% | -0.026028 |
| 2023 | 510 | -200.99 | 0.924786 | 49.412% | -0.040623 |
| 2024 | 482 | -1,101.04 | 0.614659 | 43.361% | -0.237393 |
| 2025 | 498 | -843.88 | 0.685277 | 47.390% | -0.177888 |
| 2026 YTD | 264 | -608.49 | 0.592591 | 44.697% | -0.243841 |

## Binding and accounting

- AlphaFactory run: `20260719_142214`.
- Source SHA-256:
  `EFEA68F7763873B5F880BBCB2919A3A2DF629289E06F69A525FA91396C9674A6`.
- Frozen preset SHA-256:
  `1B48AAA7ACBE2C50686A1261D4A3C6CF019C2625DB1654BBD9454B25125B2997`.
- Execution receipt SHA-256:
  `9BF2DE916A2981F25C4A362EA1C2EA58DC7BC0414206DD71204FA35284B1D04B`.
- Manifest and RunMeta both identify HYP-011; RunMeta reports news `DISABLED`.
- Lifecycle reconciliation: 8,682 rows = 4,341 opens + 4,341 final closes,
  with 4,341 unique position IDs on each side.
- First entry: `2018.01.02 09:35:00`; last entry:
  `2026.07.17 12:45:00`; last final close: `2026.07.17 13:21:42`.

## Why the verdict is invalid rather than complete

The preregistered plan required 100% tester history quality. MT5 reported 99%,
so the validity gate fails even though the chart interval and lifecycle ledger
completed. The result remains useful as a broad diagnostic and strongly agrees
with the killed parent, but it is not clean promotion-grade evidence.

Additional boundaries: news is disabled because the release ledger covers only
2019-2022; historical execution-cost provenance is unverified; one 2018
position has zero initial-risk telemetry and is excluded from normalized R; the
full-fidelity challenger remains a different zero-trade path. No result in this
run revives the terminal family or grants paper/live authority.

## Evidence

- Result JSON:
  `research/evidence/HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011_DIAGNOSTIC_RESULT.json`
- Report:
  `02. AlphaFactory/runs/EA_ICTFVGReportFidelity/20260719_142214/report.html`
- Chart:
  `02. AlphaFactory/runs/EA_ICTFVGReportFidelity/20260719_142214/analysis/analysis_charts.png`
- Lifecycle ledger:
  `02. AlphaFactory/runs/EA_ICTFVGReportFidelity/20260719_142214/logs/EURUSD_LifecycleTrades_HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011_90560921.csv`
