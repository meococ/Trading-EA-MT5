---
name: alpha-parameter-sensitivity
description: Import a complete MT5 optimization family, count every pass for DSR, and render an actual parameter stability surface.
---

## Preconditions

- Use a full MT5 optimization XML/CSV export, never one backtest report.
- Freeze the source/config/count/selection fields from
  `OPTIMIZATION_RECEIPT.template.json` before outcomes. After the run, complete
  the same composite receipt with full-report and selected-series hashes; never
  change the frozen fields.
- DSR requires the same `per_trade_net_r` Sharpe definition in every pass and
  the selected pass return series. MT5 tester Sharpe is not mixed silently.

## Command

```powershell
& "02. AlphaFactory/alpha.ps1" param `
  -Report "<FULL_OPTIMIZATION_EXPORT.xml>" `
  -Packet "<FROZEN_OPTIMIZATION_RECEIPT.json>" `
  -Param1 "<PARAMETER_1>" `
  -Param2 "<PARAMETER_2>" `
  -Metric "Custom" `
  -ExpectedTrials <N> `
  -SelectedPass "<PASS_ID>" `
  -SelectedReturns "<SELECTED_PASS_NET_R.csv>" `
  -SharpeColumn "Custom" `
  -SrSemantics per_trade_net_r `
  -SelectionFrozen `
  -Charts
```

## Artifacts and interpretation

- `optimization_analysis/optimization_audit.json`
- `optimization_analysis/parameter_heatmap.png`
- `optimization_analysis/parameter_surface_3d.png`

The JSON retains the full pass inventory, raw matrix, missing/duplicate cells,
connected plateau components, edge location and DSR inputs. A sharp isolated
maximum is fragility; a broad connected neighborhood is preferable.

Schema v1 is diagnostic-only: `diagnostic_evidence_complete=true` confirms the
current export/selected series are internally hash-bound and DSR can be
computed. `anti_overfit_gate_eligible`, `anti_overfit_gate_pass` and
`promotion_eligible` remain false until AlphaFactory binds preregistration time
and cumulative campaign exposure independently. `diagnostic_dsr_pass` is not a
promotion verdict.

## Forbidden legacy interpretation

Do not create a heatmap by adding Gaussian noise to realized P/L, and do not
call a single-report sensitivity result `STABLE`, `PROP_READY`, or safe to
deploy. The AlphaFactory command now fails closed on that input shape.
It also rejects a 2D heatmap when unselected optimizer axes vary inside a cell;
export a frozen slice instead of collapsing the third axis with a median.
