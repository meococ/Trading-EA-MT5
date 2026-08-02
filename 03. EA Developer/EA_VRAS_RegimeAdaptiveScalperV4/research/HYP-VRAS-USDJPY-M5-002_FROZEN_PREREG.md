# Frozen research-proxy preregistration — HYP-VRAS-USDJPY-M5-002

Frozen on 2026-08-02 before any HYP-002 Strategy Tester report, trade outcome,
PF, expectancy, year result, validation, or holdout access.

## Lineage and purpose

`HYP-VRAS-USDJPY-M5-001` remains terminally parked before Model 0. Its signal
and engineering implementation passed the target-symbol P0 and code gates, but
the ID had no admissible USDJPY commission or slippage evidence.

HYP-002 is a fresh, research-only cost-contract successor. It changes no
signal, estimator, session, threshold, risk rule, exit rule, data window, or
acceptance threshold. Its only source changes are the embedded hypothesis ID
and magic number. It may use:

- raw same-broker USDJPY BID/ASK samples from `CopyTicksRange` for historical
  spread coverage;
- the maximum complete-lifecycle USDJPY Strategy Tester commission clue,
  permanently labelled `strategy_tester_simulation`; and
- a fixed-latency future executable quote movement proxy, permanently labelled
  `fill_observed=false`.

This evidence tier is `RESEARCH_PROXY`, is never promotion-grade, and may only
falsify the frozen TRAIN object cheaply.

## Frozen strategy object

- EA / symbol / timeframe: `EA_VRAS_RegimeAdaptiveScalperV4` / `USDJPY` / M5.
- Window: `2016.01.04` through `2020.12.31`, inclusive.
- Session: `[22:15,05:30) UTC`, wrapping midnight.
- Estimator: 72 completed M5 closes; OLS `X[t]=a+b*X[t-1]+e[t]`;
  require `0<b<1`, half-life `[1,36]` bars and overlapping VR(5) `<1.0`.
- Primary entry: fade completed-bar z-score at `|z|>=2.0`.
- Primary exit: equilibrium/sign-crossing at `|z|<=0.25`, session end,
  18-bar maximum hold, Friday flatten, or risk hard cut.
- ATR 14; tail stop at 4 equilibrium sigma; minimum stop 1.5 ATR; minimum
  reward:risk 1.5; cost-distance multiple 3.0.
- Risk 0.25%; maximum three entries/day; 2.0% daily soft stop; 3.5% daily
  hard stop; 8.0% peak-equity cutoff.
- Synchronous tester-only `OrderCheck` plus `OrderSend`; mandatory broker SL/TP;
  lifecycle-v3 telemetry; no optimizer, paper, live, or holdout.

The inherited outcome-blind P0 evidence is
`research/evidence/HYP-VRAS-USDJPY-M5-001_P0/design_confirmation.json`: six of
six structural gates passed on 1,286 design sessions. HYP-002 does not rerun or
tune that probe.

## Frozen execution and cost contract

Exactly one Model 0 primary bootstrap run is eligible:

- `RunRole=control` is the strict-runner bootstrap role; the trading direction
  remains the primary fade with `InpDirectionMultiplier=+1`.
- deposit 10,000 USD; leverage 1:100; spread `current`; Model 0;
  execution mode 0; fixed delay 0; trade-only telemetry.
- embedded identity `HYP-VRAS-USDJPY-M5-002`; magic `5601602`.
- engineering allowances remain conservative at commission `0.70` pips
  round-turn and slippage `0.30` pips per side for pre-entry geometry. The
  report repricer must instead bind the raw research proxy evidence.

The strict runner forbids `RESEARCH_PROXY` as a challenger input. Therefore no
reverse-control or second economic run is authorized under HYP-002. If this
primary fails any gate, HYP-002 is killed. If it passes, HYP-002 is parked as a
research survivor awaiting promotion-grade commission/fill evidence and a
fresh preregistered matched-pair successor. Passing HYP-002 can never establish
`economic-valid` or `promotion-ready`.

Exact overrides:

`InpAtrPeriod=14;InpCommissionPips=0.70;InpCostDistanceMultiple=3.0;InpDailyHardStopPct=3.5;InpDailySoftStopPct=2.0;InpDirectionMultiplier=1;InpEnableTelemetry=true;InpEntryZ=2.0;InpExitAbsZ=0.25;InpHypothesisId=HYP-VRAS-USDJPY-M5-002;InpMagic=5601602;InpMaxAccountDrawdownPct=8.0;InpMaxHalfLifeBars=36.0;InpMaxHoldBars=18;InpMaxSpreadPips=1.20;InpMaxTradesPerDay=3;InpMaxVarianceRatio=1.0;InpMinHalfLifeBars=1.0;InpMinRewardRisk=1.5;InpMinStopAtr=1.5;InpOuWindow=72;InpResearchAutoMode=true;InpRiskPercent=0.25;InpSlippageOneWayPips=0.30;InpTailStopZ=4.0;InpVarianceRatioQ=5`

## Fast-kill and terminal decision

The research-only TRAIN run must meet all applicable frozen gates:

- PF strictly greater than 1.30 at x1 proxy cost;
- 2.0–5.0 executed trades per elapsed calendar week;
- PF at least 1.25 at x1.5 cost and at least 1.00 at x2 cost;
- maximum drawdown no greater than 8.0%;
- positive x1-cost expectancy;
- at least four of five calendar years positive;
- no single year contributes more than 35% of trades; and
- no stop-out, lifecycle mismatch, bar-zero decision, report/source identity,
  persistence, or confirmed-fill-bound failure.

No threshold repair, alternate window, year veto, signal reversal, cost
relabelling, validation, holdout, optimizer, paper, or live route is authorized
after the outcome is read.
