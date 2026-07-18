# Frozen preregistration — HYP-UPSC-XAU-M5-002

## Purpose and lineage

This is the lifecycle-bookkeeping repair of HYP-UPSC-XAU-M5-001. It is frozen
after the strict cost builder rejected one zero-risk lifecycle, but without
using any performance breakdown to alter the strategy.

The only source change is telemetry state separation: pending order risk,
current position risk and previous position risk are stored independently so
queued close/open callbacks cannot overwrite or clear one another. Signal,
entry, exit, sizing, limits, timeframe and all numerical thresholds remain
identical to HYP-UPSC-001 and the original four-bar HYP-003 control.

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

## Frozen strategy and override contract

- Closed-bar only. H4 EMA20/EMA50 direction; closed D1 may not oppose.
- A sweep remains valid for exactly four closed M5 bars.
- Displacement, FVG, breaker, overlap score and entry timing are unchanged.
- Risk `0.30%`; sweep stop plus `40` points; target `2.50R`; break-even at
  `1.00R`; maximum hold `90` minutes.
- Maximum spread `35` points; maximum two trades/day; loss and drawdown guards
  unchanged. Historical news filtering remains disabled and blocks promotion.

Exact overrides:

`InpAtrPeriod=14;InpBreakerLookback=6;InpBreakEvenR=1.00;InpEnableTelemetry=true;InpMagic=5600716;InpMaxAccountDrawdownPct=5.50;InpMaxConsecutiveLosses=2;InpMaxDailyLossPct=1.00;InpMaxHoldMinutes=90;InpMaxSpreadPoints=35;InpMaxTradesPerDay=2;InpMaxWeeklyLossPct=2.00;InpMinAutoScore=75;InpMinDisplacementAtr=1.20;InpMinFvgAtr=0.05;InpMinOverlapRatio=0.10;InpRequireNewsGuard=false;InpResearchAutoMode=true;InpRiskPercent=0.30;InpServerUtcOffsetHours=2;InpSessionEndUtcHour=16;InpSessionStartUtcHour=7;InpStopBufferPoints=40;InpStrongDisplacementAtr=1.80;InpStrongOverlapRatio=0.25;InpSweepLookback=12;InpSweepStateBars=4;InpTargetRR=2.50`

## Frozen research-only cost contract

Reuse HYP-003's unchanged hash-bound evidence. The tier is
`RESEARCH_PROXY`; `promotion_eligible=false`; `fill_observed=false`.

- 701,041 FivePercent XAUUSD M1 spread rows.
- Tester-only maximum commission proxy: `4.40 USD/lot`, 335 lifecycles.
- Fixed `1000 ms` quote-latency proxy, maximum wait `500 ms`, 15,588 BUY and
  15,588 SELL cases; P90 round-turn adverse move `80` pips.
- Reprice at x1.0, x1.5 and x2.0; future quotes are not fills.

## Acceptance and forced decision

- Base/full-cost PF strictly greater than `1.80`.
- Elapsed-calendar cadence `2.0` to `5.0` trades/week.
- Max drawdown and Monte Carlo P95 drawdown no greater than `5.50%`.
- Cost x1.5 PF at least `1.25`; x2 PF at least `1.00`.
- Any failed strategy, cost, lifecycle, identity, non-repaint, storage or
  validator gate kills/parks HYP-UPSC-002. No post-hoc rescue.
- Passing remains non-promotable without independent observed fill/commission
  evidence and hash-bound historical news data.

## Storage closeout

All terminal/tester/history/report files remain under the dedicated portable
root or workspace on `D:`. Snapshot C before/after and delete only payload
proven to belong to this lane.

