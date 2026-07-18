# Prereg — HYP-UPS-XAU-M5-002

Status: **FROZEN / PROBE PASS**. The first closed-bar opportunity probe passed
without changing the decision surface. This is a new mechanism hypothesis, not
a threshold rescue of 001.

## Identity

- Hypothesis ID: `HYP-UPS-XAU-M5-002`
- EA package: `EA_UnicornPrecisionScalper`
- Parent: `HYP-UPS-XAU-M5-001` (parked before build).
- Source provenance: Owner-supplied Unicorn Precision Scalper report.
- Feature family: stateful XAU liquidity-sweep -> displacement/FVG -> breaker
  overlap, with a fixed four-closed-bar sweep validity window.
- Symbol / timeframe / window: `XAUUSD` / `M5` / `2024.01.01` through
  `2026.07.15`; bootstrap `control`; MT5 Model `0`.

## Trader thesis and quantified mapping

- The report specifies a sequence of sweep, MSS/displacement and Unicorn zone;
  it does not require the sweep to be the candle immediately before the
  displacement. A sweep state therefore remains valid for four closed M5 bars.
- Scan the four bars ending at the left side of the three-candle FVG. At least
  one bar must pierce the prior 12-bar extreme and close back inside. The most
  recent valid same-direction sweep supplies invalidation/SL geometry.
- All other mapping remains frozen from 001: H4 directional bias, D1 not
  opposing H4, `1.2 x ATR(14)` minimum displacement (`1.8 x` strong), FVG at
  least `0.05 x ATR`, breaker overlap at least `10%` (`25%` strong), UTC
  07:00-16:00, score at least 75, first quote after confirmation close.
- Research-auto entry, SL beyond sweep plus 40 points, TP `2.5R`, BE `1.0R`,
  max hold 90 minutes, symbol+magic ownership and one owned exposure at a time.
- Default runtime remains alert-only; no live/funded execution authorization.

## Frozen decision surface

`InpResearchAutoMode=true;InpEnableTelemetry=true;InpRiskPercent=0.30;InpMagic=5600716;InpAtrPeriod=14;InpSweepLookback=12;InpSweepStateBars=4;InpBreakerLookback=6;InpMinDisplacementAtr=1.20;InpStrongDisplacementAtr=1.80;InpMinFvgAtr=0.05;InpMinOverlapRatio=0.10;InpStrongOverlapRatio=0.25;InpMinAutoScore=75;InpTargetRR=2.50;InpBreakEvenR=1.00;InpStopBufferPoints=40;InpMaxSpreadPoints=35;InpSessionStartUtcHour=7;InpSessionEndUtcHour=16;InpServerUtcOffsetHours=2;InpMaxHoldMinutes=90;InpMaxTradesPerDay=2;InpMaxConsecutiveLosses=2;InpMaxDailyLossPct=1.00;InpMaxWeeklyLossPct=2.00;InpMaxAccountDrawdownPct=5.50;InpRequireNewsGuard=false`

`InpRequireNewsGuard=false` is a disclosed research limitation because no
hash-bound historical calendar source is available. Promotion remains blocked
until a fail-closed same-broker calendar contract exists.

## Acceptance and kill gates

- First probe: at least 120 eligible candidates, at least 20 long and 20 short,
  at least 24 active calendar months, median at least 4 per active month.
- Model 0: cadence `2.0-5.0` trades/calendar-week, PF >=`1.80`, MaxDD
  <=`5.50%`, verified cost x1.5 PF >=`1.25`, x2 PF >=`1.00`.
- Monte Carlo P95 DD <=`5.50%`; train and holdout each pass independently;
  no material direction/month/year/session concentration.
- Diagnostic priors remain win rate 55%-68%, expectancy >=0.45R, realized
  payoff >=2.2R and roughly 8-20 trades/month.

## Probe and de-dup evidence

- 001 exact-adjacency mapping was parked at 65 candidates. This new stateful
  mapping is declared before its first result and retains all thresholds.
- `do_not_repeat_failures.md` and candidate registry contain no prior terminal
  stateful breaker-FVG overlap family.
- Probe: `research/probe_unicorn_stateful_closedbar.py`; summary only on D,
  no raw bars persisted.
- Frozen result: `166` candidates (`134` long / `32` short), `25` active
  months, median `6` candidates per active month. Probe source SHA256
  `591FA1AEBC3E8E89C87408A74F4403EA8DD1A63A4E21899174DADEAF520CE1C1`;
  artifact SHA256
  `FD0DF525C63A3871E2E21354D9DA1F339E97C482DFEB33A2EB0181B0BD845109`.

## Forbidden post-result edits

No threshold, session, direction or subgroup rescue. A failing result parks or
kills this ID. Any further mechanism change requires another hypothesis ID.
