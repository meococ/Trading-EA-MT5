# HYP-VRAS-EURUSD-M5-008 — Frozen Tester-Survival Full-Horizon Diagnostic Plan

Status: **FROZEN PRE-SOURCE / PRE-OUTCOME**  
Frozen: 2026-07-22 UTC  
Parent: invalid diagnostic `HYP-VRAS-EURUSD-M5-007`  
Symbol/timeframe: EURUSD M5 with closed H1 context  
Window: 2019.01.01–2022.12.31; Model 0; current spread; deposit 500,000; leverage 1:100

## Diagnostic question

HYP007 proved that disabling the EA's 6% account-DD entry halt is insufficient on this tester account: the broker/account-level stop-out still terminated the control at about 10% loss and 44% of the chart. HYP008 asks the same full-horizon question with tester-survival scaling only.

The parent HYP006 economic verdict remains terminal KILL. HYP008 is an engineering/observational child and cannot promote, rescue, optimize, or authorize live risk.

## Only legal delta from HYP007

- Tester deposit changes from USD 100,000 to USD 500,000.
- `InpRiskPercent` changes from 0.05% to 0.01%.
- Initial cash risk budget remains approximately USD 50 per trade (`100,000 × 0.05% = 500,000 × 0.01%`). This preserves practical lot sizing and avoids minimum-lot signal loss while moving the broker stop-out floor far enough away to complete the chart.
- Source delta is limited to HYP008 identity/magic/variant validation and version text. Signal, stop, target, BE, timeout, guards, sizing algorithm and telemetry logic may not change.

## Frozen behavior and overrides

Common: `InpResearchAutoMode=true;InpEnableTelemetry=true;InpHypothesisId=HYP-VRAS-EURUSD-M5-008;InpMagic=5600758;InpDiagnosticDisableAccountDDEntryHalt=true;InpH1EmaPeriod=200;InpRollingVwapBars=48;InpSwingLookbackBars=10;InpSlBufferPips=1.5;InpControlMinSlPips=4.0;InpControlMaxSlPips=15.0;InpAtrPeriod=14;InpAtrFloorMultiple=1.0;InpMaxStructuralAtrMultiple=3.0;InpRiskRewardRatio=1.5;InpBreakEvenTriggerR=1.0;InpBreakEvenOffsetPips=0.5;InpRiskPercent=0.01;InpMaxSpreadPips=1.20;InpMaxTradesPerDay=5;InpDailyLossPct=1.50;InpMaxAccountDrawdownPct=6.00;InpMaxHoldBars=24;InpRequireNewsGuard=false`.

Control adds: `InpUseVolatilityNormalizedStop=false;InpVariantTag=CONTROL_FIXED_CLAMP_FULL_HORIZON_V2`.

Challenger adds: `InpUseVolatilityNormalizedStop=true;InpVariantTag=CHALLENGER_ATR_STRUCTURAL_FULL_HORIZON_V2`.

## Frozen coverage and interpretation gates

1. Each arm must finish the full requested interval at 100% history quality and approximately the known 298,483-bar corpus.
2. No broker/tester stop-out; RunMeta `account_halt=false`, DD halt disabled, DD threshold crossing and maximum observed DD still recorded.
3. Exact report ↔ lifecycle reconciliation with one OPEN and one final CLOSE per position.
4. Control completes before challenger with byte-identical source/binary and no contract change between arms.
5. Report PF, win rate, realized R, cadence, exit mix, year/session/direction/regime distribution and cost proxies. Dollar P/L is valid for this diagnostic account size only.
6. Compare full-horizon stop arms descriptively. No acceptance/promotion claim can be made even if one arm looks better.

No optimizer, WFA, Monte Carlo, robustness rescue, threshold/R:R/SL/session/day/year/direction amendment, holdout access, paper/live attachment, or rerun is permitted under HYP008.
