# Frozen operational-identity successor — HYP-VRAS-USDJPY-M5-003

Frozen on 2026-08-02 after HYP-002 produced a report but before any PF, PnL,
drawdown, trade count, yearly result, validation output, or other economic
outcome was read.

## Lineage and allowed change

HYP-002 was stopped by the report data-fingerprint gate. Its broker, server,
account and symbol geometry matched; only the preregistered Bars/Ticks basis
was wrong. The exact observed non-economic identity was History Quality 100%,
88,937 bars and 47,662,758 ticks for USDJPY M5, 2016.01.04–2020.12.31.

HYP-003 changes only the embedded hypothesis ID, magic number, and the bound
data fingerprint. Signal, OU/VR estimator, Asian session, thresholds, risk,
exits, Model 0 window, cost evidence and every acceptance threshold remain
identical to HYP-002. HYP-002 report outcomes are not predecessor evidence and
must not be read or used for tuning.

## Frozen strategy and execution

- EA / symbol / timeframe: `EA_VRAS_RegimeAdaptiveScalperV4` / `USDJPY` / M5.
- Window: `2016.01.04` through `2020.12.31`; Model 0; current spread.
- Session `[22:15,05:30) UTC`; 72 completed closes; OU `0<b<1`;
  half-life `[1,36]` M5 bars; overlapping VR(5) `<1.0`.
- Fade completed-bar `|z|>=2.0`; equilibrium exit `|z|<=0.25`; maximum hold
  18 bars; ATR 14; 4-sigma tail stop; 1.5 ATR minimum stop; RR at least 1.5.
- Risk 0.25%; maximum three entries/day; daily soft/hard stops 2.0%/3.5%;
  account peak-equity cutoff 8.0%.
- Deposit 10,000 USD; leverage 1:100; trade-only lifecycle-v3 telemetry.
- Identity `HYP-VRAS-USDJPY-M5-003`; magic `5601603`.

The cost tier remains `RESEARCH_PROXY`: raw same-broker spread, maximum
complete-lifecycle USDJPY tester commission at USD 4.00/lot, and a fixed-latency
future executable quote proxy with `fill_observed=false`. It can only falsify
the frozen TRAIN object. It can never establish economic validity or promotion
readiness.

Expected report identity basis:

`USDJPY|M5|2016.01.04|2020.12.31|0|100%|88937|47662758|3|0.001|0.01`

Expected data fingerprint:

`FFD3024F94509DCC5281F6956A237BED542F9161F44837BF2AAE904D76D9B695`

Exact overrides:

`InpAtrPeriod=14;InpCommissionPips=0.70;InpCostDistanceMultiple=3.0;InpDailyHardStopPct=3.5;InpDailySoftStopPct=2.0;InpDirectionMultiplier=1;InpEnableTelemetry=true;InpEntryZ=2.0;InpExitAbsZ=0.25;InpHypothesisId=HYP-VRAS-USDJPY-M5-003;InpMagic=5601603;InpMaxAccountDrawdownPct=8.0;InpMaxHalfLifeBars=36.0;InpMaxHoldBars=18;InpMaxSpreadPips=1.20;InpMaxTradesPerDay=3;InpMaxVarianceRatio=1.0;InpMinHalfLifeBars=1.0;InpMinRewardRisk=1.5;InpMinStopAtr=1.5;InpOuWindow=72;InpResearchAutoMode=true;InpRiskPercent=0.25;InpSlippageOneWayPips=0.30;InpTailStopZ=4.0;InpVarianceRatioQ=5`

## Frozen fast-kill and terminal decision

Exactly one HYP-003 `RunRole=control` Model 0 run is authorized. The frozen
gates are PF >1.30 at x1 proxy cost, 2–5 trades per elapsed week, PF >=1.25 at
x1.5, PF >=1.00 at x2, max DD <=8%, positive x1-cost expectancy, at least four
of five positive calendar years, no year over 35% of trades, and no lifecycle,
non-repaint, persistence, fill-bound, identity or source-integrity failure.

Failure kills HYP-003. Passing parks it as a non-promotable research survivor
awaiting real commission/fill evidence and a fresh matched-pair successor. No
threshold repair, alternate window, reversal, optimization, validation,
holdout, paper or live route is authorized after outcome access.
