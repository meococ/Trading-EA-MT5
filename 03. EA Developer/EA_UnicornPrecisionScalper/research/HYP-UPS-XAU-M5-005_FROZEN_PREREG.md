# Frozen preregistration — HYP-UPS-XAU-M5-005

## Purpose and lineage

This is the single pre-outcome structural challenger to the unopened valid
control successor `HYP-UPS-XAU-M5-004`. HYP-003 produced no admissible strategy
evidence. The challenger is frozen before reading any HYP-004 performance
result and tests one mechanism only: replace the arbitrary four-closed-bar
sweep lifetime with an event-anchored sweep state. Every threshold, higher-
timeframe filter, score, session, risk and management rule remains identical.

The mechanism comes from the Unicorn research report's ordered state-machine
description: a sweep is an event that precedes displacement, FVG and breaker
confirmation. The report does not establish four bars as a causal lifetime.

## Frozen probe contract

- Symbol / timeframe: `XAUUSD` / `M5`.
- Discovery window: `2024.01.01` through `2025.12.25`, inclusive.
- All 2026 data is untouched by this hypothesis.
- Inputs are completed MT5 bars only; H4/D1 values must be last-closed as of
  each M5 decision timestamp.
- MT5 must run portable with its data path on `D:`. Raw bars are not copied to
  the workspace. Outputs are a bounded JSON summary and at most 200
  deterministic event labels.
- This is an opportunity-density/funnel probe only. It may not calculate or
  persist entry returns, exits, targets, stops, fills, profit, loss, R-multiples
  or drawdown.

## The one allowed mechanism change

Control: the most recent qualifying sweep is valid for exactly four closed M5
bars (`sweep_age_bars` 0 through 3).

Challenger: the most recent qualifying sweep after UTC session open at 07:00
remains valid until a completed M5 bar closes beyond the swept extreme (below
it for bullish, above it for bearish) or the UTC research session ends at
16:00. The signal still needs the same current closed H4 direction and non-
opposing closed D1 condition.

No other change is authorized. These remain frozen:

- ATR `14`; sweep lookback `12`; research breaker scan `8` bars;
- displacement `1.20 ATR`, strong displacement `1.80 ATR`;
- FVG `0.05 ATR`; overlap `0.10`, strong overlap `0.25`; score `75`;
- spread `35` points; UTC session `07:00–16:00`;
- risk `0.30%`, stop buffer `40` points, target `2.50R`, break-even `1.00R`,
  maximum hold `90` minutes and all portfolio guards.

If built, HYP-005 adds only `InpUseEventAnchoredSweepState=true`; HYP-004 keeps
the fixed four-bar mechanism.

Exact future Model-0 overrides:

`InpAtrPeriod=14;InpBreakerLookback=6;InpBreakEvenR=1.00;InpEnableTelemetry=true;InpMagic=5600717;InpMaxAccountDrawdownPct=5.50;InpMaxConsecutiveLosses=2;InpMaxDailyLossPct=1.00;InpMaxHoldMinutes=90;InpMaxSpreadPoints=35;InpMaxTradesPerDay=2;InpMaxWeeklyLossPct=2.00;InpMinAutoScore=75;InpMinDisplacementAtr=1.20;InpMinFvgAtr=0.05;InpMinOverlapRatio=0.10;InpRequireNewsGuard=false;InpResearchAutoMode=true;InpRiskPercent=0.30;InpServerUtcOffsetHours=2;InpSessionEndUtcHour=16;InpSessionStartUtcHour=7;InpStopBufferPoints=40;InpStrongDisplacementAtr=1.80;InpStrongOverlapRatio=0.25;InpSweepLookback=12;InpSweepStateBars=4;InpTargetRR=2.50;InpUseEventAnchoredSweepState=true`

## Frozen build-authorization gates

The no-outcome probe authorizes build only if all gates pass:

- cadence `2.0–5.0` candidates per elapsed calendar week;
- at least `20` active months, `30` long and `30` short candidates;
- deterministic casebook contains `100–200` labels;
- at least `20%` are structurally valid late states (`sweep_age_bars >= 4`);
- challenger count is strictly greater than matched fixed-four-bar control;
- zero candidates occur after structural invalidation;
- static checks confirm portable `D:`, completed bars, no trading calls and no
  forward-outcome fields.

Failure is terminal. No threshold, direction, date, hour or gate may change
after the probe, and no failed probe may be rescued post hoc.

## Frozen Model-0 contract if probe passes

- Window/model/role: `2024.01.01`–`2025.12.25` / Model `0` / challenger.
- Account `100000` USD, leverage `100`, spread `current`.
- HYP-004 is the immutable matched control; HYP-005 runs once. Neither result
  may tune the other.
- The unchanged research-only cost proxy remains non-promotable.
- Absolute gates: PF `>1.80`, cadence `2.0–5.0`, max DD and Monte Carlo P95 DD
  `<=5.50%`, cost x1.5 PF `>=1.25`, cost x2 PF `>=1.00`.
- HYP-005 must also improve full-cost net, PF and net-to-DD over HYP-004 in the
  identity-bound AlphaFactory comparison.
- Passing cannot authorize live or prop deployment.

## Storage closeout

All probe/build/tester evidence remains on `D:`. Delete only verified run-owned
cache/log payload from `C:`; protect shared terminal/account/history data.

