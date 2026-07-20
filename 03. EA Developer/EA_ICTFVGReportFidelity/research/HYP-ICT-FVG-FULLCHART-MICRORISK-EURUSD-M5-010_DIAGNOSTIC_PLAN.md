# HYP-ICT-FVG-FULLCHART-MICRORISK-EURUSD-M5-010 - identity-bound full-chart diagnostic

Status: **FROZEN AFTER HYP-009 FAILURE, BEFORE HYP-010 SOURCE CHANGE OR OUTCOME**

## Parent failure and purpose

- Parent: invalid diagnostic
  `HYP-ICT-FVG-FULLCHART-NODD-EURUSD-M5-009`.
- Parent source SHA-256:
  `7F5AD64F2C622B0426BA475B855257AAB560026C2882C1D45D7C6826DAF33EAE`.
- Parent control `20260719_131410` confirmed that the 8% EA account-DD gate was
  removed, but the 0.25% risk sizing reached a broker/tester stop-out on
  25 April 2019. It generated only 23,349 bars / 4,972,379 ticks and 162
  entries, so it did not satisfy the Owner's full-chart request.
- Parent RunMeta also retained the HYP-008 source identity while the manifest
  identified HYP-009. This child must bind its own identity.
- Purpose: observe the unchanged control entry set through the complete
  2019-2022 chart. This is not an economic, prop-firm or promotion experiment.

## Frozen legal delta

1. Change only source version/embedded identity to version `1.16` and
   `HYP-ICT-FVG-FULLCHART-MICRORISK-EURUSD-M5-010`. No functional source line
   may change.
2. Use one new control preset:
   `presets/EURUSD_M5_CONTROL_FULLCHART_MICRORISK.set`, SHA-256
   `DD00FEBEC100D40B3B148A2AB4804A7696700B3A95F1FA46EE6587DF92E7CCAC`.
3. Relative to the canonical HYP-008 control preset, only two inputs change:
   `InpMaxAccountDrawdownPct: 8.00 -> 100.00` and
   `InpRiskPercent: 0.25 -> 0.01`.
4. The 0.01% micro-risk is a mechanical tester-survival scale chosen after the
   0.25% run hit broker stop-out. Dollar P&L, dollar expectancy and percentage
   DD are therefore diagnostic only. Signal count, direction, timing and
   normalized outcome geometry remain the observation targets.

## Frozen execution contract

- Run exactly one `CONTROL_FULLCHART_MICRORISK` arm through AlphaFactory.
- FivePercent EURUSD M5, MT5 Model 0, `2019.01.01-2022.12.31`, deposit 100,000,
  leverage 1:100, no optimization and no other override.
- A challenger rerun is deliberately excluded: the unchanged full-fidelity
  signal path had zero execution calls, so changing DD/risk cannot alter it.
- Holdout 2023+ remains sealed. Historical spread/commission/slippage
  provenance remains failed. `promotion_eligible=false`.

## Required proof and readout

- Before the run: identity contract tests, all package tests, AlphaFactory
  compile 0/0, exact-source non-repaint audit and a fresh source/binary receipt.
- Valid completion requires manifest/RunMeta HYP-010 identity agreement,
  298,483 bars, 79,486,116 ticks, 100% history quality, no broker stop-out and
  exact lifecycle entry/final-close reconciliation.
- Report first/last entry, trade count by calendar year, full-period cadence,
  PF, win rate, normalized expectancy where derivable, max DD and RunMeta
  funnel. Dollar metrics must be labeled micro-risk scale only.
- If the run completes, verdict is `DIAGNOSTIC_COMPLETE_FULL_CHART`; the HYP-008
  economic kill remains unchanged regardless of the observation.
- If it terminates early or identity/accounting does not reconcile, verdict is
  `INVALID_DIAGNOSTIC`. No additional risk reduction or rerun is authorized
  under this ID.
