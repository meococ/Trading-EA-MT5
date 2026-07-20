# HYP-ICT-FVG-FULLCHART-MICRORISK-EURUSD-M5-010 - full-chart readout

Verdict: **DIAGNOSTIC_COMPLETE_FULL_CHART_PARENT_KILL_CONFIRMED**

## Outcome

The Owner-requested full-chart observation completed. AlphaFactory run
`20260719_133139` processed the complete EURUSD M5 2019-2022 window at 100%
history quality: 298,483 bars, 79,486,116 ticks and 1,248 UTC days. The first
entry was 2 January 2019 and the last was 30 December 2022.

The run used `InpMaxAccountDrawdownPct=100.00`, so the EA's persistent account-DD
gate was functionally inactive. `InpRiskPercent=0.01` was intentionally used
only to prevent the broker/tester stop-out that invalidated the prior 0.25% run.
No signal, session, news, entry, stop, target, daily loss, trade-count or
cooldown rule changed.

## Full-chart control result

| Period | Trades | PF | Win rate | Net at 0.01% risk | Expectancy R/trade |
|---|---:|---:|---:|---:|---:|
| 2019 | 517 | 0.5853 | 42.55% | -$1,331.37 | -0.2592R |
| 2020 | 517 | 0.8398 | 47.97% | -$448.26 | -0.0880R |
| 2021 | 520 | 0.7089 | 45.38% | -$873.88 | -0.1718R |
| 2022 | 516 | 0.9616 | 50.58% | -$98.93 | -0.0196R |
| **Total** | **2,070** | **0.7625** | **46.62%** | **-$2,752.44** | **-0.1348R** |

Cadence is 9.925 trades per elapsed week, above the workspace target of 2-5.
All four years are net negative and PF remains below 1.0 even before any
additional verified historical cost stress. The complete equity curve slopes
down throughout the window; 2022 improves but remains negative.

## Evidence integrity

- Manifest and RunMeta both bind HYP-010.
- Lifecycle reconciles exactly: 2,070 opens, 2,070 positions and 2,070 final
  closes; lifecycle net equals report net at -$2,752.44.
- Funnel reconciles exactly at the top level:
  `12,340 sweeps = 698 news + 283 session + 8,577 prop/cooldown/daily + 698 exposure + 11 spread + 3 risk + 2,070 entries`.
- Source differs from HYP-008 only by version and embedded hypothesis identity;
  package tests pass, compile is 0/0 and exact-source non-repaint V12 passes
  with zero findings.

## Interpretation boundary

This is the generous sweep/reclaim control, not the full report-fidelity EA.
The full-fidelity challenger still produces zero execution calls because its
signal funnel rejects everything upstream; removing DD or shrinking risk cannot
create those trades.

The dollar figures use diagnostic 0.01% sizing and are not prop-firm results.
Historical spread/commission/slippage provenance remains unverified. The result
does not reopen HYP-008, authorize tuning, WFA/Monte Carlo, paper/live trading
or access to the sealed 2023+ holdout.

## Artifacts

- Full AlphaFactory report: `02. AlphaFactory/runs/EA_ICTFVGReportFidelity/20260719_133139/report.html`
- Full-period chart: `02. AlphaFactory/runs/EA_ICTFVGReportFidelity/20260719_133139/analysis/analysis_charts.png`
- Lifecycle ledger: `02. AlphaFactory/runs/EA_ICTFVGReportFidelity/20260719_133139/logs/EURUSD_LifecycleTrades_HYP-ICT-FVG-FULLCHART-MICRORISK-EURUSD-M5-010_87527171.csv`
