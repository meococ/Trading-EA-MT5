# Frozen operational preregistration — HYP-UPS-XAU-M5-006

## Purpose and lineage

HYP-006 is the execution-compatible operational successor to HYP-005. It is
not a new strategy idea and it may not change the event-anchored mechanism
that was frozen and probed before any admissible four-bar control outcome was
opened.

HYP-005 could not legally execute because its frozen `challenger` role is
incompatible with the only available `RESEARCH_PROXY` cost evidence. HYP-006
changes only the embedded hypothesis identity and the AlphaFactory role to an
independent research `control`. It exists only to falsify the already-frozen
mechanism once; it cannot claim a matched-control improvement or promotion.

## Frozen mechanism and inputs

- EA / symbol / timeframe: `EA_UnicornPrecisionScalper` / `XAUUSD` / `M5`.
- Window/model/role: `2024.01.01` through `2025.12.25` / Model `0` /
  research `control`.
- Account: `100000` USD, leverage `100`, spread `current`.
- Completed bars only; portable terminal and tester data must remain on `D:`.
- The event-anchored sweep remains valid from the qualifying closed-bar sweep
  until a completed M5 bar closes beyond its extreme or the UTC research
  session ends. All displacement, FVG, breaker, score, session, risk and trade
  management rules are identical to HYP-005.

Exact overrides:

`InpAtrPeriod=14;InpBreakerLookback=6;InpBreakEvenR=1.00;InpEnableTelemetry=true;InpMagic=5600717;InpMaxAccountDrawdownPct=5.50;InpMaxConsecutiveLosses=2;InpMaxDailyLossPct=1.00;InpMaxHoldMinutes=90;InpMaxSpreadPoints=35;InpMaxTradesPerDay=2;InpMaxWeeklyLossPct=2.00;InpMinAutoScore=75;InpMinDisplacementAtr=1.20;InpMinFvgAtr=0.05;InpMinOverlapRatio=0.10;InpRequireNewsGuard=false;InpResearchAutoMode=true;InpRiskPercent=0.30;InpServerUtcOffsetHours=2;InpSessionEndUtcHour=16;InpSessionStartUtcHour=7;InpStopBufferPoints=40;InpStrongDisplacementAtr=1.80;InpStrongOverlapRatio=0.25;InpSweepLookback=12;InpSweepStateBars=4;InpTargetRR=2.50;InpUseEventAnchoredSweepState=true`

## Frozen gates

- Build authorization is inherited only from the HYP-005 no-outcome probe:
  251 candidates, 2.4234 per elapsed week, 205 long / 46 short, 24 active
  months, 47.81% late-state candidates and zero invalidated candidates.
- Compile must have zero errors/warnings and exact-source non-repaint must pass.
- Lifecycle telemetry must have one OPEN and one final CLOSE per position and
  no non-positive initial-risk binding.
- Absolute gates: PF `>1.80`, cadence `2.0–5.0`, max DD and Monte Carlo P95 DD
  `<=5.50%`, cost x1.5 PF `>=1.25`, cost x2 PF `>=1.00`.
- One Model-0 run only. Failure is terminal. No result slice may be used to
  disable a day/hour/year or tune a threshold.
- A pass only parks the mechanism pending real same-broker commission/fill
  evidence and a future preregistered comparison. It does not revive HYP-005
  or authorize live/prop deployment.

## Cost and storage limitation

The inherited cost source is `RESEARCH_PROXY`, with `fill_observed=false` and
`promotion_eligible=false`. All run artifacts remain on `D:`. Only verified
run-owned cache/log payload may be deleted from `C:`; shared terminal/account
history is protected.
