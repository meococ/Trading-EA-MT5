# Frozen operational-repair preregistration — HYP-UPS-XAU-M5-004

## Purpose and lineage

HYP-004 is the operational successor to the inadmissible HYP-003 execution.
Run `20260716_133403` was rejected before strategy analysis because its
telemetry identity, storage route and broker identity failed closed. No report
performance field from that run may be read or used.

HYP-004 changes no signal, threshold, direction, session, risk, management or
cost rule. It changes exactly two operational defects:

1. embed `HYP-UPS-XAU-M5-004` in lifecycle telemetry; and
2. write lifecycle files into the normal Strategy Tester sandbox on the
   dedicated portable `D:` terminal, without `FILE_COMMON`.

## Frozen run identity

- EA / symbol / timeframe: `EA_UnicornPrecisionScalper` / `XAUUSD` / `M5`.
- Window: `2024.01.01` through `2025.12.25`, inclusive.
- MT5 model / role: Model `0` / control.
- Account: deposit `100000` USD, leverage `100`, spread `current`.
- Broker/server: `Five Percent Online Ltd` / `FivePercentOnline-Real`.
- Telemetry: `trade-only`, lifecycle-v3, exactly one identity-bound RunMeta and
  LifecycleTrades pair collected from the run-owned `D:` tester sandbox.
- Research only. No chart attachment, demo, prop or live execution.

## Frozen strategy and risk contract

- Closed-bar only. H4 EMA20/EMA50 direction; closed D1 may not oppose.
- Sweep state is exactly four closed M5 bars; lookback `12`.
- ATR `14`; displacement `1.20 ATR`; strong displacement `1.80 ATR`.
- Minimum FVG `0.05 ATR`; overlap `0.10`, strong overlap `0.25`; score `75`.
- Maximum spread `35` points; UTC session `07:00–16:00`.
- Risk `0.30%`; stop buffer `40` points; target `2.50R`; break-even `1.00R`;
  maximum hold `90` minutes; maximum two trades/day and unchanged loss guards.
- Historical news filtering remains disabled because no hash-bound calendar is
  available. This and research-only cost evidence block promotion.

Exact overrides:

`InpAtrPeriod=14;InpBreakerLookback=6;InpBreakEvenR=1.00;InpEnableTelemetry=true;InpMagic=5600716;InpMaxAccountDrawdownPct=5.50;InpMaxConsecutiveLosses=2;InpMaxDailyLossPct=1.00;InpMaxHoldMinutes=90;InpMaxSpreadPoints=35;InpMaxTradesPerDay=2;InpMaxWeeklyLossPct=2.00;InpMinAutoScore=75;InpMinDisplacementAtr=1.20;InpMinFvgAtr=0.05;InpMinOverlapRatio=0.10;InpRequireNewsGuard=false;InpResearchAutoMode=true;InpRiskPercent=0.30;InpServerUtcOffsetHours=2;InpSessionEndUtcHour=16;InpSessionStartUtcHour=7;InpStopBufferPoints=40;InpStrongDisplacementAtr=1.80;InpStrongOverlapRatio=0.25;InpSweepLookback=12;InpSweepStateBars=4;InpTargetRR=2.50`

## Frozen research-only cost and decision contract

The HYP-003 proxy is inherited without change: 701,041 same-broker historical
spread rows, tester maximum commission `4.40` USD/lot and 15,588 BUY plus
15,588 SELL 1000-ms quote scenarios with P90 round-turn `80` pips.
`fill_observed=false` and `promotion_eligible=false` for every outcome.

- Base/full-cost PF must be strictly greater than `1.80`.
- Elapsed-calendar cadence must be `2.0–5.0` trades/week.
- Max DD and Monte Carlo P95 DD must be no greater than `5.50%`.
- Cost x1.5 PF must be at least `1.25`; cost x2 PF at least `1.00`.
- Any identity, lifecycle, broker, storage, cost, cadence, signal, drawdown or
  non-repaint failure kills/parks HYP-004. No post-hoc rescue is allowed.

## Storage closeout

All evidence and heavy MT5 state remain on `D:`. After hash verification,
delete only run-owned cache/log payload created on `C:`. Shared profiles,
accounts, history and unrelated runs are protected.

