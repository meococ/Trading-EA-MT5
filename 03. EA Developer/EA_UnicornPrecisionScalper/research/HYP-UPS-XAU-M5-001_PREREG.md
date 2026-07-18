# Prereg — HYP-UPS-XAU-M5-001

Status: draft `idea`. This file becomes frozen when the closed-bar opportunity
probe passes and the registry advances to `probe`. No performance result has
been inspected when the decision surface below was written.

## Identity

- Hypothesis ID: `HYP-UPS-XAU-M5-001`
- EA package: `EA_UnicornPrecisionScalper`
- Parent / independent mechanism: independent implementation of the supplied
  `Unicorn_Precision_Scalper_Deep_Research_Report.md`.
- Source provenance: Owner-supplied workspace report; practitioner research,
  not peer-reviewed evidence and not a profitability claim.
- Feature family: XAUUSD liquidity sweep -> displacement/MSS -> bullish or
  bearish FVG overlapping a recent opposite candle (quantified breaker proxy).
- Symbol / timeframe / frozen window: `XAUUSD` / `M5` /
  `2024.01.01` through `2026.07.15`.
- Role / MT5 model: bootstrap `control` / Model `0` (real ticks).

## Trader thesis and quantified mapping

- Market behavior: a session liquidity sweep followed by structural
  displacement leaves an imbalance overlapping a failed opposite candle; an
  H4/D1-compatible retracement/continuation should have positive expectancy.
- Closed-bar pattern: signal context is copied from `shift >= 1`. A sweep must
  pierce the prior 12-bar extreme and close back inside. The following
  three-candle sequence must create an FVG; the middle candle body must be at
  least `1.2 x ATR(14)` and receives full quality score at `1.8 x ATR`.
- Breaker proxy: select the recent opposite-color candle (lookback 6) with the
  greatest geometric overlap with the FVG; require at least `10%` of FVG width,
  with full quality score at `25%`.
- Bias: closed H4 EMA20/EMA50 + close alignment must be directional. Closed D1
  may align or be neutral but may not oppose H4.
- Session: `07:00 <= UTC hour < 16:00`; tester mapping uses the frozen input
  `InpServerUtcOffsetHours=2`. This fixed-offset contract is research-only and
  does not claim DST/live-broker correctness.
- Entry: research-auto only at the first executable quote after the M5
  confirmation bar closes; never fill at the close that formed the signal.
- Initial SL: beyond sweep extreme plus 40 XAU points; TP `2.5R`; break-even at
  `1.0R`; max hold 90 minutes; no grid, martingale, DCA, average-down or stop
  widening.
- Ownership: symbol + magic + strategy tag, one owned exposure at a time,
  hedging/netting-safe enumeration and restart recovery from live positions.
- Default runtime mode remains alert-only. `InpResearchAutoMode=true` is
  required explicitly by the backtest packet.

## Frozen decision surface

`InpResearchAutoMode=true;InpEnableTelemetry=true;InpRiskPercent=0.30;InpMagic=5600716;InpAtrPeriod=14;InpSweepLookback=12;InpBreakerLookback=6;InpMinDisplacementAtr=1.20;InpStrongDisplacementAtr=1.80;InpMinFvgAtr=0.05;InpMinOverlapRatio=0.10;InpStrongOverlapRatio=0.25;InpMinAutoScore=75;InpTargetRR=2.50;InpBreakEvenR=1.00;InpStopBufferPoints=40;InpMaxSpreadPoints=35;InpSessionStartUtcHour=7;InpSessionEndUtcHour=16;InpServerUtcOffsetHours=2;InpMaxHoldMinutes=90;InpMaxTradesPerDay=2;InpMaxConsecutiveLosses=2;InpMaxDailyLossPct=1.00;InpMaxWeeklyLossPct=2.00;InpMaxAccountDrawdownPct=5.50;InpRequireNewsGuard=false`

Historical MT5 calendar availability is not proven. The baseline therefore
freezes `InpRequireNewsGuard=false` and is research-only even if economics pass.
No result may be promoted to paper/live until a fail-closed broker calendar
contract is implemented and independently validated.

## Acceptance and kill gates

- Cheap opportunity probe (not P&L): at least 120 eligible candidates, at least
  20 long and 20 short, at least 24 active calendar months, median at least 4
  candidates per active month. Failure parks this ID before EA entry code.
- Meaningful Model 0 run: at least one trade, elapsed cadence `2.0-5.0` trades
  per calendar week, PF at least `1.80`, MaxDD at most `5.50%`.
- Cost stress: verified x1.5 PF at least `1.25`; x2 PF at least `1.00`.
- Monte Carlo P95 DD at most `5.50%`; train and holdout must each pass; no
  single year/month/session/direction may manufacture the result.
- Report priors: win rate `55%-68%`, expectancy at least `0.45R`, realized
  payoff at least `2.2R`, roughly `8-20` trades/month. These are diagnostic
  expectations, not post-result tuning handles.
- Control-relative requirement: this bootstrap control establishes the frozen
  report mapping. Any later challenger must keep data/cost/window/model identity
  and beat control on net, PF and net/DD under the generic comparator.

## Probe and de-dup evidence

- Checked `04. Memory/do_not_repeat_failures.md`: no terminal Unicorn/breaker-
  FVG-overlap family row exists; FVG-only and failed XAU families are related
  but not the same quantified conjunction.
- Probe implementation: `research/probe_unicorn_closedbar.py` reads MT5 bars
  without persisting raw market data and writes one summary JSON on drive D.
- Decision: pending first and only frozen probe run.

## Forbidden post-result edits

Any threshold, hour/day/year veto, news behavior or mechanism change suggested
by this hypothesis's probe/readout requires a new hypothesis ID. No post-hoc
rescue. Passing a backtest never authorizes live or funded execution.
