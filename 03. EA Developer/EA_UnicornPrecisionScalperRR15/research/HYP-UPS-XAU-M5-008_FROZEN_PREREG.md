# Frozen owner-directed RR diagnostic — HYP-UPS-XAU-M5-008

## Purpose and interpretation boundary

The Owner requested a direct replay of the terminal event-anchored Unicorn
control with reward:risk changed from `1:2.50` to `1:1.50`. This request was
made after the HYP-006 outcome was known, so HYP-008 is a post-outcome
sensitivity diagnostic, not an independent alpha hypothesis and not a rescue
of HYP-006.

The run answers one bounded question: does taking profit at 1.50R materially
change the observed win rate and net expectancy of the exact HYP-006 entry,
stop, session, risk and management policy? No result can promote this variant,
authorize live/prop use, or justify another RR value.

## Exact controlled change

- Parent evidence: `HYP-UPS-XAU-M5-006`, valid Model-0 run
  `20260716_141244`, terminal KILL.
- Replay base: frozen source snapshot
  `EA_UnicornPrecisionScalper_HYP-006_CB51EB2A.mq5`.
- Only economic strategy change: `InpTargetRR=2.50` becomes
  `InpTargetRR=1.50`.
- Operational-only identity changes: embedded hypothesis ID and unique magic.
- No signal, stop, break-even, risk, session, hold, spread, score, sweep,
  displacement, FVG, breaker or overlap rule may change.

## Frozen test contract

- Diagnostic EA / symbol / timeframe: `EA_UnicornPrecisionScalperRR15` /
  `XAUUSD` / `M5`. The sibling package prevents overwriting concurrent
  post-kill hardening in the parent package; package identity is operational
  and the frozen HYP-006 source remains the economic comparison base.
- Window/model/role: `2024.01.01` through `2025.12.25` / Model `0` /
  research `control`.
- Account: `100000` USD, leverage `100`, spread `current`.
- Completed bars only; MT5 install, tester data, reports and retained evidence
  remain on `D:`.
- One valid Model-0 outcome only. An operationally invalid attempt with no
  strategy evidence may be repaired without changing the frozen contract.

Exact overrides:

`InpAtrPeriod=14;InpBreakerLookback=6;InpBreakEvenR=1.00;InpEnableTelemetry=true;InpMagic=5600719;InpMaxAccountDrawdownPct=5.50;InpMaxConsecutiveLosses=2;InpMaxDailyLossPct=1.00;InpMaxHoldMinutes=90;InpMaxSpreadPoints=35;InpMaxTradesPerDay=2;InpMaxWeeklyLossPct=2.00;InpMinAutoScore=75;InpMinDisplacementAtr=1.20;InpMinFvgAtr=0.05;InpMinOverlapRatio=0.10;InpRequireNewsGuard=false;InpResearchAutoMode=true;InpRiskPercent=0.30;InpServerUtcOffsetHours=2;InpSessionEndUtcHour=16;InpSessionStartUtcHour=7;InpStopBufferPoints=40;InpStrongDisplacementAtr=1.80;InpStrongOverlapRatio=0.25;InpSweepLookback=12;InpSweepStateBars=4;InpTargetRR=1.50;InpUseEventAnchoredSweepState=true`

## Frozen readout and terminal rule

Report trades, elapsed-week cadence, win rate, tester PF/net/DD, verified
research-cost PF/net-R at x1/x1.5/x2, robustness, Monte Carlo P95 DD and equity
audit. Compare them directly with HYP-006, but do not tune from subgroups.

The ordinary research gates remain descriptive: PF `>1.80`, cadence
`2.0–5.0`, max DD and Monte Carlo P95 DD `<=5.50%`, cost x1.5 PF `>=1.25`,
and cost x2 PF `>=1.00`. Regardless of pass/fail, the terminal decision is
`PARK_DIAGNOSTIC_ONLY` or `KILL_DIAGNOSTIC`; `promotion_eligible=false`.
No alternate RR, hour/day/year/direction filter, threshold adjustment or
rerun is authorized from this readout.

## Cost and storage limitation

The inherited cost source is `RESEARCH_PROXY`, with `fill_observed=false` and
`promotion_eligible=false`. Only a verified run-owned disposable cache/log on
`C:` may be removed after D-side evidence is retained; shared terminal,
account, configuration and history data are protected.

