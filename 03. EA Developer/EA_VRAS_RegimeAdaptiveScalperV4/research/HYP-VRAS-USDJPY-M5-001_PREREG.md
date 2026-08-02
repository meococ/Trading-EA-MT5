# Preregistration — HYP-VRAS-USDJPY-M5-001

Frozen: 2026-08-02, before `.mq5`, compile, MT5, trade-path, cost, or PnL
access for this hypothesis.

## Owner scope and authority transition

The Owner's current directive explicitly supersedes the earlier instruction to
leave V4 at the HYP-015 preflight stop and requests the symbol-aligned USDJPY
successor to be built end to end. For this bounded lane, the prior T2/P3
logical execution pointer is suspended; no T2 source, registry row, exposure
ledger, data epoch, or evidence artifact may be mutated. Only this USDJPY
successor may build/compile/run until it reaches a terminal verdict.

This is a fresh symbol-lane identity. It does not reopen
`HYP-VRAS-EURUSD-M5-015` or inherit economic evidence from V1-V3.

## Atomic hypothesis

During the USDJPY Asian sleeve, a closed-bar OU deviation with stable
short-horizon mean reversion can produce positive expectancy after verified
broker costs:

- symbol: `USDJPY`
- entry/economic timeframe: `M5`
- session: `[22:15,05:30) UTC`, wrapping midnight
- engine: OU mean reversion only
- primary arm: fade the signed z-score
- matched control: reverse the primary direction while preserving the same
  signal timestamps and risk geometry

The P0 target-symbol/timeframe probe passed all six frozen gates on 2016-2020
DESIGN: 1,286 eligible sessions; median Hurst `0.42517682`, VR(5)
`0.88361271`, median OU half-life `11.8583` M5 bars; no trade outcome was
opened. Evidence:
`research/evidence/HYP-VRAS-USDJPY-M5-001_P0/design_confirmation.json`.

## Frozen signal estimator

All reads use completed M5 bars starting at shift 1.

1. Copy exactly 72 completed M5 closes.
2. Fit `X[t]=a+b*X[t-1]+e[t]` by OLS.
3. Valid only when `0<b<1`; equilibrium `mu=a/(1-b)`.
4. Residual equilibrium sigma is `sd(e)/sqrt(1-b^2)` and must be positive.
5. Half-life is `-ln(2)/ln(b)` and must be in `[1,36]` M5 bars.
6. Compute overlapping log-return VR(5) on the same 72 bars; require `<1.0`.
7. Closed-bar z-score is `(Close[1]-mu)/sigma_eq`.
8. Long when `z<=-2.0`; short when `z>=2.0`.
9. Primary direction multiplier is `+1`; matched reverse control is `-1`.
10. Exit at the first closed bar with `abs(z)<=0.25` or a sign crossing, at
    05:30 UTC, after 18 M5 bars, Friday 20:00 UTC, or a risk hard cut.

No Hurst threshold is used in the EA. Hurst was a P0 population diagnostic,
not a rolling trade filter.

## Frozen geometry and execution

- ATR: 14 completed M5 bars.
- Tail stop: `mu-4*sigma` for primary long or `mu+4*sigma` for primary short.
- Minimum stop distance: 1.5 ATR from actual entry; use the farther protective
  stop, never the nearer one.
- Target: OU equilibrium `mu` for the primary arm. The reverse control mirrors
  stop/target distances around actual entry so it cannot inherit invalid
  primary geometry.
- Reject unless reward:risk is at least 1.5 and target distance is at least
  3.0 times estimated all-in pips.
- Synchronous `OrderCheck` plus `OrderSend` only. `OrderSendAsync`, timeout
  resend/reset, and the mutation-disabled shared async kernel are forbidden.
- One symbol exposure at a time; no averaging, grid, martingale, pending-order
  ladder, partial take-profit, break-even, or trailing-stop overlay.
- Broker SL and TP are mandatory in the entry request.

## Frozen risk and prop controls

- risk per entry: 0.25% of current equity, sized from `OrderCalcProfit` loss
  per lot plus commission/slippage allowance
- max spread: 1.2 USDJPY pips
- commission allowance: 0.7 pips round trip
- slippage allowance: 0.3 pips each way
- max entries/day: 3
- equity soft stop: no new entry at 2.0% daily loss
- daily hard cutoff: close owned position and latch at 3.5% daily loss
- peak-equity hard cutoff: close and latch at 8.0% drawdown
- daily reset: UTC midnight derived from FivePercent server clock, winter
  UTC+2 and EU DST UTC+3
- daily start equity, peak equity, and latch state persist in terminal Global
  Variables keyed by account, magic, and UTC day; restart must not reset risk
- lot consistency: after 10 owned entry deals, clamp new volume to
  `[0.5,1.5] * average(last 10 owned entry lots)`
- rollover entry blackout: `[21:55,22:15) UTC`
- Friday flatten: 20:00 UTC; no weekend hold

## Capability exclusions

Engines 1 and 2 are not part of this hypothesis. Candle-direction volume,
volume-spike delta, volatility-normalized range, quote imbalance, CVD, VPIN,
LOB OFI, multi-engine arbitration, async execution, EURUSD, EURJPY, XAUUSD,
GBPUSD, BTCUSD, and other sessions require fresh preregistered hypotheses.
No candle/tick-volume proxy may be labeled true CVD, VPIN, or OFI.

## Frozen economic attempt order

1. Engineering: source contract tests, compile, non-repaint audit.
2. Model 0 reverse bootstrap control: `2016.01.04` through `2020.12.31`,
   deposit 10,000, leverage 100, explicit defaults above.
3. Model 0 primary challenger on the identical window and execution settings,
   cryptographically matched to the completed reverse control run.
4. Analyze and `validate-full` both reports.
5. Open validation `2021.01.04` through `2024.12.31` only if the TRAIN primary
   passes every economic gate and beats the reverse control. The 2025+ holdout
   remains sealed until a separate promotion-stage authorization.

No optimizer, threshold repair, session repair, stop/target variant,
direction/year veto, or additional economic arm is authorized under this ID.

## Acceptance and fast-kill gates

The TRAIN primary must meet all:

- PF > 1.30 at verified x1 cost
- 2.0-5.0 executed trades per elapsed calendar week
- PF >=1.25 at x1.5 cost and PF >=1.00 at x2 cost
- maximum drawdown <=8.0%
- positive expectancy after x1 cost
- at least four of five calendar years positive
- no single year contributes more than 35% of trades
- primary beats reverse control on PF and expectancy
- no broker stop-out, lifecycle mismatch, bar-zero decision, or report/source
  identity failure

Any failure gives a terminal TRAIN kill for this exact estimator/session/risk
object. Engineering-valid, economic-valid, and promotion-ready remain separate.
