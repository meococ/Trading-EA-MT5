# HYP-VRAS-EURUSD-M5-006 — Frozen Preregistered Matched Pair

Status: **FROZEN PRE-SOURCE / PRE-OUTCOME**  
Frozen: 2026-07-22 UTC  
Symbol/timeframe: EURUSD M5 with closed H1 context  
Window: 2019.01.01–2022.12.31; Model 0; current spread; deposit 100,000; leverage 1:100

## Hypothesis

HYP005 lost primarily because the fixed 4–15 pip clamp frequently moved the stop inside the measured M5 structure. Replacing only that stop geometry with a volatility-normalized structural stop should reduce premature stop-outs and improve realized R without changing the entry thesis or nominal 1.5R target.

This is a new mechanism ID, not a rerun or rescue of terminal HYP005. No HYP006 outcome was observed before this freeze.

## Shared decision surface

All signal inputs are closed bars.

- H1 bias: H1 close[1] above/below EMA200[1].
- M5 rolling VWAP: volume-weighted typical price over the last 48 completed M5 bars. It is explicitly **not** a session-anchored VWAP.
- Long: M5 low[1] <= rolling VWAP, close[1] > rolling VWAP, and close[1] > high[2].
- Short: M5 high[1] >= rolling VWAP, close[1] < rolling VWAP, and close[1] < low[2].
- Risk: 0.25% of current equity per trade, sized with `OrderCalcProfit` and broker volume step.
- TP: 1.5 × actual initial stop distance.
- Break-even: at +1.0R, move SL to entry plus/minus 0.5 pip.
- Time exit: 24 completed M5 bars from position open.
- Shared guards: maximum 5 entries per broker day; daily equity loss 1.5% from day-start equity blocks new entries until the next broker day; account equity drawdown 6% from initial equity latches a permanent entry halt; maximum spread 1.20 pips; one EURUSD exposure.
- Risk halts never stop the tester and never prevent management/closure of an existing position.
- News guard is disabled identically in both arms. Cost provenance remains `UNVERIFIED_DIAGNOSTIC_ONLY`.

## Single changed mechanism

Control `InpUseVolatilityNormalizedStop=false`:

- Raw stop = 10-bar completed-M5 swing high/low plus 1.5 pips.
- Final distance is clamped to [4.0, 15.0] pips, reproducing HYP005 geometry.

Challenger `InpUseVolatilityNormalizedStop=true`:

- Raw stop = identical 10-bar completed-M5 swing high/low plus 1.5 pips.
- ATR = MT5 ATR(14) on completed M5 bar[1].
- If raw structural distance > 3.0 × ATR, reject the trade; never clamp the stop inside structure.
- Otherwise final stop distance = max(raw structural distance, 1.0 × ATR).

## Frozen overrides

Common: `InpResearchAutoMode=true;InpEnableTelemetry=true;InpHypothesisId=HYP-VRAS-EURUSD-M5-006;InpMagic=5600756;InpH1EmaPeriod=200;InpRollingVwapBars=48;InpSwingLookbackBars=10;InpSlBufferPips=1.5;InpControlMinSlPips=4.0;InpControlMaxSlPips=15.0;InpAtrPeriod=14;InpAtrFloorMultiple=1.0;InpMaxStructuralAtrMultiple=3.0;InpRiskRewardRatio=1.5;InpBreakEvenTriggerR=1.0;InpBreakEvenOffsetPips=0.5;InpRiskPercent=0.25;InpMaxSpreadPips=1.20;InpMaxTradesPerDay=5;InpDailyLossPct=1.50;InpMaxAccountDrawdownPct=6.00;InpMaxHoldBars=24;InpRequireNewsGuard=false`.

Control adds: `InpUseVolatilityNormalizedStop=false;InpVariantTag=CONTROL_FIXED_CLAMP`.

Challenger adds: `InpUseVolatilityNormalizedStop=true;InpVariantTag=CHALLENGER_ATR_STRUCTURAL`.

## Frozen gates

Absolute challenger gates: N >= 350; cadence 2.0–5.0 trades per elapsed calendar week; PF >= 1.30; mean realized R > +0.05; max equity DD <= 6.0%; PF proxy at 1.5× cost >= 1.25; PF proxy at 2× cost >= 1.00; Monte Carlo 95th-percentile DD <= 6.0%.

Relative gates versus matched control: PF lift >= 0.15; mean realized R lift >= 0.10R; initial-stop exit share reduction >= 10 percentage points; max equity DD may not worsen by more than 1 percentage point.

## Stop rules

Exactly one serial control and one serial challenger Model-0 run. No optimizer, threshold sweep, alternate ATR multiple, alternate R:R, session/day/year/direction veto, cost reinterpretation, or post-outcome amendment. Failure kills HYP006; any later mechanism requires a new ID.

