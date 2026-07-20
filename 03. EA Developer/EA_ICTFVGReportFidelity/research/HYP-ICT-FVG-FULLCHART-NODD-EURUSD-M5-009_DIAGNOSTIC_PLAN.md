# HYP-ICT-FVG-FULLCHART-NODD-EURUSD-M5-009 - full-chart no-account-DD diagnostic

Status: **FROZEN BEFORE HYP-009 TESTER OUTCOME**

## Purpose and parent boundary

- Parent: terminal `HYP-ICT-FVG-FIDM0EXEC-EURUSD-M5-008`.
- Parent source SHA-256:
  `7F5AD64F2C622B0426BA475B855257AAB560026C2882C1D45D7C6826DAF33EAE`.
- The parent control opened 122 trades, lost USD 7,944.29 and then stopped
  permanently after exhausting the frozen 8% peak-equity drawdown budget in
  March 2019. The full report-fidelity challenger remained zero-trade because
  its signal funnel stopped before execution.
- Owner requested removal of the account-DD stop to observe trades across the
  entire chart. This child is an observational diagnostic, not a strategy
  rescue and not evidence of prop-firm compliance.

## Frozen delta

- Preserve the canonical source and every signal, session, news, entry, stop,
  target, spread, per-trade risk, daily loss, daily trade-count and cooldown
  rule exactly.
- Change only `InpMaxAccountDrawdownPct` from `8.00` to `100.00` in two new
  diagnostic presets. The source requires this input to be positive; 100%
  makes the peak-equity account-DD gate functionally inactive while preserving
  the unchanged code path.
- Control preset:
  `presets/EURUSD_M5_CONTROL_FULLCHART_NODD.set`, SHA-256
  `AD20D9B41A0A66B0EFF3839B4C7E3B372D61164800C7ED08BBCC956855B255EF`.
- Challenger preset:
  `presets/EURUSD_M5_CHALLENGER_FULLCHART_NODD.set`, SHA-256
  `A03AAD24CE50A90B9C3440BF82F3537C6FEBEF17FA38762D386692FC861E6616`.
- Byte-level comparison must prove that this is the only difference from the
  parent presets.

## Frozen execution contract

- Run exactly one sequential pair through AlphaFactory:
  1. `CONTROL_FULLCHART_NODD` with `InpSignalMode=0`.
  2. `CHALLENGER_FULLCHART_NODD` with `InpSignalMode=1`, bound to the completed
     control manifest and report.
- FivePercent EURUSD M5, MT5 Model 0, `2019.01.01-2022.12.31`, deposit 100,000,
  no optimization and no additional parameter change.
- Holdout 2023+ remains sealed. Historical spread/commission/slippage
  provenance remains failed. Every result is diagnostic and
  `promotion_eligible=false`.
- No further rerun, threshold relaxation, year/hour exclusion or signal rescue
  is authorized from this result.

## Diagnostic readout contract

- Reconcile entries, positions and lifecycle rows exactly.
- Report full-period and calendar-year trade count, net profit, profit factor,
  win rate, max drawdown, expectancy, first/last entry and elapsed-calendar-week
  cadence for every non-empty arm.
- Report the complete RunMeta rejection funnel for both arms.
- Compare the no-DD control only with the corrected 8%-DD parent control to
  show what the persistent account gate censored. Do not rank the no-DD run as
  a prop-firm candidate.
- If the challenger remains zero-trade, PF/WR/expectancy remain undefined and
  the pre-execution signal-starvation verdict stands.

## Stop and verdict rules

- Tester/source/receipt mismatch or accounting mismatch: `INVALID_DIAGNOSTIC`.
- Complete run with reconciled evidence: `DIAGNOSTIC_COMPLETE`; then retain the
  parent economic kill unless the observation reveals an engineering defect.
- No outcome can reopen HYP-008, authorize paper/live trading or relax the
  original 8% risk contract.
