# HYP-ICT-FVG-FIDM0-EURUSD-M5-006 - frozen diagnostic Model-0 plan

Status: **FROZEN BEFORE ANY STRATEGY TESTER OUTCOME**

## Identity and legal delta

- Parent: terminal parked `HYP-ICT-FVG-FIDREC-EURUSD-M5-005`.
- The parent completed restart/execution reconciliation and never opened a
  Strategy Tester outcome.
- Parent source SHA-256:
  `C6A05F4124029A38A7FC80B83D8697B6B58E87CF3FAEDD9FD53BE43DA87522E2`.
- This child changes only the embedded hypothesis identity and source version.
  Signal logic, data access, news, parameters, risk, execution and telemetry
  behavior must remain byte-equivalent after excluding those identity lines.
- This is the diagnostic Model-0 execution already allowed by the frozen
  `...FIDNEWS...-002` plan; it is not a result-driven rescue or optimization.

## Frozen test surface

- EA: `EA_ICTFVGReportFidelity`.
- Symbol/timeframe/window: `EURUSD`, `M5`, `2019.01.01` through `2022.12.31`.
- Model: `0`; deposit: `100000`; no optimization; 2023+ remains sealed.
- Exactly two sequential arms:
  1. `InpSignalMode=0` - high-recall sweep/reclaim control.
  2. `InpSignalMode=1` - full ordered report-fidelity FSM.
- All other overrides are exactly those in the package CONTROL/CHALLENGER
  presets. `InpResearchAutoMode=true`, lifecycle-v3 telemetry on, historical
  news guard on, ATR trail off.
- CONTROL preset SHA-256:
  `E62D0386B915B4E9BD1FA4A8C761FD72844DBDE2223D175A48F798D6D2F84DB3`.
- CHALLENGER preset SHA-256:
  `74FCE7C0C465D5BEA6BAEA9538071C290207621194BA7D74E41996C4CB0A0C68`.
- The canonical source must be recompiled and bound source -> news include ->
  EX5 -> compile log before either run.

## Economics and verdict boundary

- Diagnostic round-trip cost: 1.5 pip; stress: 2.25 and 3.0 pip.
- The current official The5ers fee page observed on 2026-07-19 states forex
  commission of USD 4 per lot round trip and typical major-pair spreads of
  0.2-0.9 pip in standard conditions. This is current contract context, not
  historical 2019-2022 execution proof.
  Source: `https://help.the5ers.com/what-are-the-spreads-and-commissions/`
  (page last-update label `02.01.2026`).
- Same-broker historical M1 spread provenance still fails because 366,196 of
  1,491,312 rows are zero. Verified direction-aware slippage remains absent.
- Therefore every result is `promotion_eligible=false` and cannot authorize
  paper/live use or a superiority claim.
- Primary gates for the challenger: at least 300 closed trades; 2.0-5.0 trades
  per elapsed week; PF at 1.5-pip diagnostic cost >=1.60; PF at 2.25 pips
  >=1.25; PF at 3.0 pips >=1.00; max drawdown <=8%.
- Missed cadence, sample, PF or drawdown gate gives a terminal diagnostic kill.
  Passing all diagnostic gates gives `INCONCLUSIVE_COST_UNVERIFIED`, never a
  promotion.

## Execution commands

Run sequentially only after the active AlphaFactory lane is idle:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory/alpha.ps1" backtest "EA_ICTFVGReportFidelity" -Symbol EURUSD -Period M5 -From "2019.01.01" -To "2022.12.31" -Model 0 -Deposit 100000 -TimeoutSec 3600 -Overrides "InpResearchAutoMode=true;InpEnableTelemetry=true;InpSignalMode=0;InpRiskPercent=0.25;InpMagic=5600720;InpPivotStrength=2;InpSweepLookback=20;InpDisplacementBars=6;InpMeanBodyPeriod=20;InpDisplacementBodyMultiple=1.50;InpM15PivotStrength=2;InpM15Lookback=120;InpRetestBars=12;InpFvgDepthMin=0.50;InpFvgDepthMax=0.70;InpAdxPeriod=14;InpMinAdx=25.0;InpStopBufferPips=1.50;InpTargetRR=2.00;InpMaxSpreadPips=1.50;InpMaxTradesPerDay=2;InpDailyLossPct=1.50;InpMaxAccountDrawdownPct=8.00;InpMaxConsecutiveLosses=2;InpCooldownMinutes=120;InpBreakEvenTriggerR=1.00;InpBreakEvenLockR=0.50;InpFlattenUtcHour=22;InpServerUtcOffsetWinterHours=2;InpServerUsesEuropeDst=true;InpRequireNewsGuard=true;InpNewsBlackoutMinutes=30;InpUseAtrTrail=false;InpAtrTrailStartR=1.50;InpAtrTrailMultiple=1.00"
powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory/alpha.ps1" backtest "EA_ICTFVGReportFidelity" -Symbol EURUSD -Period M5 -From "2019.01.01" -To "2022.12.31" -Model 0 -Deposit 100000 -TimeoutSec 3600 -Overrides "InpResearchAutoMode=true;InpEnableTelemetry=true;InpSignalMode=1;InpRiskPercent=0.25;InpMagic=5600720;InpPivotStrength=2;InpSweepLookback=20;InpDisplacementBars=6;InpMeanBodyPeriod=20;InpDisplacementBodyMultiple=1.50;InpM15PivotStrength=2;InpM15Lookback=120;InpRetestBars=12;InpFvgDepthMin=0.50;InpFvgDepthMax=0.70;InpAdxPeriod=14;InpMinAdx=25.0;InpStopBufferPips=1.50;InpTargetRR=2.00;InpMaxSpreadPips=1.50;InpMaxTradesPerDay=2;InpDailyLossPct=1.50;InpMaxAccountDrawdownPct=8.00;InpMaxConsecutiveLosses=2;InpCooldownMinutes=120;InpBreakEvenTriggerR=1.00;InpBreakEvenLockR=0.50;InpFlattenUtcHour=22;InpServerUtcOffsetWinterHours=2;InpServerUsesEuropeDst=true;InpRequireNewsGuard=true;InpNewsBlackoutMinutes=30;InpUseAtrTrail=false;InpAtrTrailStartR=1.50;InpAtrTrailMultiple=1.00"
```

No hour/day/year/direction veto, threshold change, parameter search, control
substitution, same-outcome source edit or holdout access is permitted.
