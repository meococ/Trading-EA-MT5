# Frozen preregistration — HYP-UPSC-XAU-M5-001

## Purpose and lineage

This control isolates the storage-safe operational repair of the invalid
HYP-UPS-XAU-M5-003 run. That run was rejected before analysis because its
telemetry used `FILE_COMMON`, its RunMeta identified HYP-002, and its terminal
authenticated to MetaQuotes-Demo. No performance field from it is admissible.

This package changes only the EA/hypothesis identifier and telemetry sink.
Every signal, direction, threshold, hour, risk and management rule remains the
frozen four-bar HYP-003 control. It does not adopt or inspect the separate
event-anchored HYP-UPS-XAU-M5-004 challenger.

## Run identity

- EA / symbol / timeframe: `EA_UnicornPrecisionScalperControl` / `XAUUSD` /
  `M5`.
- Window: `2024.01.01` through `2025.12.25`, inclusive.
- MT5 model / role / stage: Model `0` / `control` / `challenger`.
- Account: deposit `100000` USD, leverage `100`, spread `current`.
- Broker/server: `Five Percent Online Ltd` /
  `FivePercentOnline-Real (Build 6006)`.
- Telemetry: `trade-only`, lifecycle-v3, normal Tester sandbox; no skip flags
  and no `FILE_COMMON`.
- Research-only: never attach the EA to a chart, demo, prop or live account.

## Frozen strategy rules

- Closed-bar only. H4 EMA20/EMA50 sets direction; closed D1 may not oppose.
- A liquidity sweep remains valid for exactly four closed M5 bars.
- Displacement, FVG, breaker and overlap scoring remain unchanged.
- Entry occurs at the first executable quote after a qualifying closed M5 bar.
- Risk `0.30%`; sweep stop plus `40` points; target `2.50R`; break-even at
  `1.00R`; maximum hold `90` minutes.
- Maximum spread `35` points; maximum two trades/day; consecutive-loss,
  daily, weekly and account-drawdown guards remain unchanged.
- Historical news filtering remains disabled because no hash-bound calendar
  source exists. This blocks promotion under every outcome.

Exact overrides:

`InpAtrPeriod=14;InpBreakerLookback=6;InpBreakEvenR=1.00;InpEnableTelemetry=true;InpMagic=5600716;InpMaxAccountDrawdownPct=5.50;InpMaxConsecutiveLosses=2;InpMaxDailyLossPct=1.00;InpMaxHoldMinutes=90;InpMaxSpreadPoints=35;InpMaxTradesPerDay=2;InpMaxWeeklyLossPct=2.00;InpMinAutoScore=75;InpMinDisplacementAtr=1.20;InpMinFvgAtr=0.05;InpMinOverlapRatio=0.10;InpRequireNewsGuard=false;InpResearchAutoMode=true;InpRiskPercent=0.30;InpServerUtcOffsetHours=2;InpSessionEndUtcHour=16;InpSessionStartUtcHour=7;InpStopBufferPoints=40;InpStrongDisplacementAtr=1.80;InpStrongOverlapRatio=0.25;InpSweepLookback=12;InpSweepStateBars=4;InpTargetRR=2.50`

## Frozen research-only cost contract

The control inherits HYP-003's hash-bound evidence without changing a sample.
`evidence_tier=RESEARCH_PROXY`; `promotion_eligible=false` always.

- 701,041 FivePercent XAUUSD M1 spread rows cover the window.
- Tester-only maximum round-turn commission proxy: `4.40 USD/lot`, from 335
  same-symbol final-close lifecycles.
- Quote-latency proxy: fixed `1000 ms`, wait at most `500 ms`, 15,588 BUY and
  15,588 SELL cases; P90 round-turn adverse move `80` pips.
- `fill_observed=false`; future quotes are not fills.
- Repricing adds commission and direction-aware quote latency at x1.0, x1.5
  and x2.0 to Model-0 prices.

## Acceptance and forced decision

- Base/full-cost PF must be strictly greater than `1.80`.
- Elapsed-calendar cadence must be `2.0` to `5.0` trades/week.
- Max drawdown and Monte Carlo P95 drawdown must be no greater than `5.50%`.
- Cost x1.5 PF must be at least `1.25`; cost x2 PF at least `1.00`.
- Any failed signal, cadence, cost, drawdown, non-repaint, lifecycle, identity,
  storage or validator gate parks/kills the hypothesis. No post-hoc rescue.
- Passing remains non-promotable until observed independent commission/fill
  provenance and hash-bound historical news data exist.

## Storage closeout

Terminal, Tester, history, report and lifecycle files must remain under
`D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable-fivepercent` or the
workspace run tree on `D:`. Snapshot C before/after and delete only payload
proven to belong to this lane.

