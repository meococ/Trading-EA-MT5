# Frozen preregistration — HYP-UPS-XAU-M5-003

## Purpose and lineage

This is a one-shot Model-0 falsification control for the unchanged
`HYP-UPS-XAU-M5-002` stateful Unicorn mechanism. It is not a signal rescue and
does not change a signal, threshold, direction, hour, weekday, or management
rule after observing a Strategy Tester result. The shorter end date is frozen
solely to bind the run to a pre-existing FivePercent XAUUSD M5 Model-0 data
identity; the prior report's performance fields were not used to define this
contract.

## Run identity

- EA / symbol / timeframe: `EA_UnicornPrecisionScalper` / `XAUUSD` / `M5`.
- Window: `2024.01.01` through `2025.12.25`, inclusive.
- MT5 model / role / stage: Model `0` / `control` / `challenger`.
- Account contract: deposit `100000` USD, leverage `100`, spread `current`.
- Broker: `Five Percent Online Ltd`; server basis:
  `FivePercentOnline-Real (Build 6006)`.
- Telemetry: `trade-only`, lifecycle-v3; no skip flags.
- This run is research-only and must never attach the EA to a chart, demo
  account, prop account, or live account.

## Frozen strategy rules

- Closed-bar only. H4 EMA20/EMA50 sets direction; closed D1 may not oppose.
- A liquidity sweep remains valid for exactly four closed M5 bars.
- Displacement, FVG, breaker and overlap scoring are unchanged from 002.
- Research-auto entry is allowed only at the first executable quote after a
  qualifying closed M5 bar.
- Risk `0.30%`; stop beyond sweep plus `40` points; target `2.50R`;
  break-even at `1.00R`; maximum hold `90` minutes.
- Maximum spread `35` points; maximum two trades/day; consecutive-loss,
  daily, weekly and account-drawdown guards remain unchanged.
- Historical news filtering remains disabled because no hash-bound calendar
  source is available. That limitation blocks promotion even if the run passes.

Exact overrides:

`InpAtrPeriod=14;InpBreakerLookback=6;InpBreakEvenR=1.00;InpEnableTelemetry=true;InpMagic=5600716;InpMaxAccountDrawdownPct=5.50;InpMaxConsecutiveLosses=2;InpMaxDailyLossPct=1.00;InpMaxHoldMinutes=90;InpMaxSpreadPoints=35;InpMaxTradesPerDay=2;InpMaxWeeklyLossPct=2.00;InpMinAutoScore=75;InpMinDisplacementAtr=1.20;InpMinFvgAtr=0.05;InpMinOverlapRatio=0.10;InpRequireNewsGuard=false;InpResearchAutoMode=true;InpRiskPercent=0.30;InpServerUtcOffsetHours=2;InpSessionEndUtcHour=16;InpSessionStartUtcHour=7;InpStopBufferPoints=40;InpStrongDisplacementAtr=1.80;InpStrongOverlapRatio=0.25;InpSweepLookback=12;InpSweepStateBars=4;InpTargetRR=2.50`

## Frozen research-only cost contract

`evidence_tier=RESEARCH_PROXY`; `promotion_eligible=false` under every outcome.

- Historical spread: 701,041 valid FivePercent XAUUSD M1 BID/ASK rows over
  the frozen run window, retained on `D:` and hash-bound.
- Commission: maximum observed tester round-turn commission, `4.40` USD/lot,
  from 335 same-symbol final-close lifecycles. This is explicitly tester-only,
  not a broker contract or observed live commission sample.
- Quote latency: fixed `1000 ms`, first quote no later than `500 ms` after the
  horizon, non-overlapping per side. Current same-broker XAU quote evidence
  yields 15,588 BUY and 15,588 SELL scenarios. P90 adverse move is `40` pips
  for BUY and `40` pips for SELL; round-turn proxy is `80` pips.
- No row is called a fill. `fill_observed=false` and
  `independent_reference=false`; only `independent_quote_reference=true`.
- Model-0 report prices retain their own historical spread. Repricing adds the
  frozen commission maximum and direction-aware quote-latency proxy at x1.0,
  x1.5 and x2.0.

## Acceptance and forced decision

- Base/full-cost PF must be strictly greater than `1.80`.
- Elapsed-calendar cadence must be `2.0` to `5.0` trades/week.
- Max drawdown and Monte Carlo P95 drawdown must be no greater than `5.50%`.
- Cost x1.5 PF must be at least `1.25`; cost x2 PF at least `1.00`.
- Any failed signal, cadence, cost, drawdown, non-repaint, lifecycle, identity,
  or validator gate parks/kills HYP-003. No post-hoc rescue is allowed.
- A full research pass authorizes only a new, separately preregistered run
  after real commission/fill provenance exists. This proxy can never promote.

## Storage closeout

Runner evidence and reports must remain on `D:`. After report/hash verification,
delete only tester cache/log payload created by this run on `C:`; do not delete
shared terminal profiles, account data, pre-existing history, or unrelated runs.
