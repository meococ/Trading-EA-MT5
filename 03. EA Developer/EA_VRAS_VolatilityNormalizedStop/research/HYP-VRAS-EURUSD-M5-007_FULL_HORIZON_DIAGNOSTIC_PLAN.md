# HYP-VRAS-EURUSD-M5-007 — Frozen Full-Horizon Diagnostic Plan

Status: **FROZEN PRE-SOURCE / PRE-OUTCOME**  
Frozen: 2026-07-22 UTC  
Parent: terminal `HYP-VRAS-EURUSD-M5-006`  
Symbol/timeframe: EURUSD M5 with closed H1 context  
Window: 2019.01.01–2022.12.31; Model 0; current spread; deposit 100,000; leverage 1:100

## Diagnostic question

The parent matched pair was censored in March 2019 when the 6% initial-equity drawdown latch stopped new entries. This diagnostic asks how the unchanged control and challenger behave across the complete four-year market path when that entry halt is bypassed in Strategy Tester.

This is an Owner-authorized observational child, not a rescue, optimization, or new edge claim. The parent verdict remains `KILL_VOLATILITY_NORMALIZED_STOP_WORSE_THAN_CONTROL` regardless of this outcome.

## Frozen behavior

- Entry, H1 EMA200 bias, rolling M5 VWAP48, path confirmation, stop geometry, 1.5R target, 1R break-even plus 0.5 pip, 24-bar timeout, spread guard, five-trade daily limit, news-disabled contract, and lifecycle telemetry remain unchanged.
- Both arms set `InpDiagnosticDisableAccountDDEntryHalt=true`.
- The original 6% DD threshold remains configured and measured. Telemetry must report whether it was crossed, maximum drawdown from initial equity, maximum peak-to-trough equity drawdown, and whether the entry halt was actually latched.
- Risk is reduced from 0.25% to 0.05% of current equity solely to keep the tester solvent across the full chart while preserving the same fixed-fraction sizing algorithm. Dollar P/L and absolute dollar expectancy are therefore not directly comparable with HYP006; PF, win rate, realized R, trade frequency, exit mix, and regime distribution remain descriptive.
- The DD bypass must be accepted only in Strategy Tester and only under this exact HYP007 identity. Default/live-capable behavior remains fail-closed with the 6% entry halt active.

## Frozen overrides

Common: `InpResearchAutoMode=true;InpEnableTelemetry=true;InpHypothesisId=HYP-VRAS-EURUSD-M5-007;InpMagic=5600757;InpDiagnosticDisableAccountDDEntryHalt=true;InpH1EmaPeriod=200;InpRollingVwapBars=48;InpSwingLookbackBars=10;InpSlBufferPips=1.5;InpControlMinSlPips=4.0;InpControlMaxSlPips=15.0;InpAtrPeriod=14;InpAtrFloorMultiple=1.0;InpMaxStructuralAtrMultiple=3.0;InpRiskRewardRatio=1.5;InpBreakEvenTriggerR=1.0;InpBreakEvenOffsetPips=0.5;InpRiskPercent=0.05;InpMaxSpreadPips=1.20;InpMaxTradesPerDay=5;InpDailyLossPct=1.50;InpMaxAccountDrawdownPct=6.00;InpMaxHoldBars=24;InpRequireNewsGuard=false`.

Control adds: `InpUseVolatilityNormalizedStop=false;InpVariantTag=CONTROL_FIXED_CLAMP_FULL_HORIZON`.

Challenger adds: `InpUseVolatilityNormalizedStop=true;InpVariantTag=CHALLENGER_ATR_STRUCTURAL_FULL_HORIZON`.

## Coverage gates

Both sequential Model-0 arms must satisfy all of the following or the diagnostic is invalid:

1. 100% MT5 history quality and complete configured 2019–2022 interval.
2. No broker/tester stop-out and no tester termination caused by a risk guard.
3. RunMeta binds HYP007, its arm tag, `account_dd_entry_halt_enabled=false`, and the exact source/task/receipt identity.
4. Report ↔ lifecycle net P/L reconciliation gap is USD 0.00, with one OPEN and one final CLOSE per position.
5. Maximum observed DD is reported even though the entry halt is bypassed.
6. Control completes before challenger; no source, preset, threshold, or contract change between arms.

## Interpretation boundary

Economics are descriptive and `promotion_eligible=false`. The diagnostic may confirm or refute whether the early 2019 sample was representative, but it cannot revive HYP006 or authorize a stop/R:R/session/year/direction retune. No optimizer, WFA, Monte Carlo, robustness rescue, holdout access, paper/live attachment, or parameter amendment is permitted under HYP007.
