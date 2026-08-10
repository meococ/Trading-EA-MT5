# HYP-CBRK-XAUUSD-M5-002 — frozen signal-clock correction

Frozen before changing source bytes, compiling, opening native XAUUSD data, launching MT5, reading a strategy report, or evaluating outcomes.

## Identity and informing evidence

- Market mechanism: unchanged XAUUSD M5 compression breakout from `HYP-CBRK-XAUUSD-M5-001` and the outcome-blind `HYP-LOMX-DESIGN-M5-002` atomic cell.
- Parent terminal verdict: `PARK_ENGINEERING_PRE_EXECUTION_SIGNAL_SESSION_CLOCK_MISMATCH_NO_MT5_NO_OUTCOMES_NO_ECONOMICS`.
- Pre-change source SHA256: `D363121DC7FFCB128A67C796B76F8B86C8AB2262FF045EAC62B49FE19FB3298B`.
- Fresh canonical EA package: `EA_CBRK_XAUBreakout`.
- Source path: `03. EA Developer/EA_CBRK_XAUBreakout/EA_CBRK_XAUBreakout.mq5`.
- Symbol/timeframe: native `XAUUSD / M5`.
- Magic: `5603203`.
- Variant: `CBRK_XAU_BREAKOUT_CLOCKFIX_MODEL0`.
- Economic adverse prior: the EURUSD sibling had PF `0.7466504499` and cadence `1.1026645768/week`; this is disclosed but does not replace an XAUUSD result.

## Sole authorized source correction

The only causal change from the parent source is the clock used by the entry-session gate. Package description and the `EA_NAME` identity string may change only to `EA_CBRK_XAUBreakout`; those two identity edits carry no market or execution logic:

1. `LoadClosedBars(rates)` succeeds first.
2. `rates[0]` is the most recently completed M5 signal bar because the source uses `CopyRates(...,1,...)` with series ordering.
3. Define `signal_utc = ServerToUtc(rates[0].time)`.
4. Apply weekday and `[07:00,16:00)` eligibility to `signal_utc`, not decision-time `utc_now` and not `rates[1]`.
5. Resolve the exact Asian range using the same `signal_utc` date.
6. Keep decision-time `utc_now` unchanged for daily/account risk locks, position management and daily/Friday flatten.

Required boundaries: signal bar `06:55` reject; `07:00` accept; `15:55` accept; `16:00` reject. A mutation using `rates[1].time` must fail the focused test.

No signal threshold, indicator, box/ATR/volume arithmetic, direction, stop, target, session, exit, risk, spread, sizing, lifecycle or cost rule may change.

## Exact signal and data completeness

- `ATR14` on bar1 is finite and positive.
- `range(bar2) < 0.70 * mean(range(bar3..bar52))`.
- Box is exactly high/low of bars2..16.
- Tick volume on bar1 is strictly above mean bars2..21.
- LONG iff close1 is strictly above box high plus `0.20 ATR`; SHORT is the strict inverse.
- Stop is opposite box edge plus/minus `0.10 ATR`; target is exactly `2.00R` after outward tick normalization.
- Every eligible decision requires all exact 72 native M5 Asian bars from `00:00` through `05:55` UTC for the signal date. Missing, duplicated or misclocked bars fail closed even though the Asian range is not a breakout threshold.
- One owned symbol/magic exposure, no pyramid, maximum three new trades/day, maximum hold 96 completed M5 bars, daily/Friday flatten 20:00 UTC.

## Frozen windows and gates

- TRAIN: `2018.01.02` through `2022.12.30`, Model 0, one untuned baseline only.
- Validation: calendar 2023 locked.
- Holdout: calendar 2024 locked.
- Deposit/leverage: `100000 USD / 1:100`; spread `current`; telemetry `trade-only / lifecycle-v3`.
- Before trade authority, child `HYP-CBRK-XAUUSD-M5-DQ-002` must prove HQ `>97`, exact requested bounds and exactly `351303` report bars with no boundary convention, zero orders/deals/trades/returns/performance/economics.
- Baseline acceptance: executed cadence `2.0–5.0/week`, each direction at least 20%, PF `>1.30` after x1 research costs, max equity DD `<=8%`, x1.5 PF `>=1.25`, x2 PF `>=1.00`.
- Any engineering failure has no economic verdict. A clear admissible economic failure closes this mechanism; no governance-rescue HYP003 is authorized.

Exact sorted overrides:

```text
InpATRPeriod=14;InpAsianEndMinutesUtc=360;InpAsianStartMinutesUtc=0;InpDailyFlattenMinutesUtc=1200;InpDeviationPoints=20;InpEnableTelemetry=true;InpEngineMode=1;InpFridayFlattenMinutesUtc=1200;InpHypothesisId=HYP-CBRK-XAUUSD-M5-002;InpLotConsistencyLookbackFills=10;InpLotConsistencyMaxFactor=1.50;InpLotConsistencyMinFactor=0.50;InpLotConsistencyMinFills=10;InpMagic=5603203;InpMaxAccountDrawdownPct=8.0;InpMaxDailyLossPct=3.5;InpMaxHoldBars=96;InpMaxSpreadToRisk=0.15;InpMaxTradesPerDay=3;InpResearchAutoMode=true;InpRiskPercent=0.25;InpSweepEpsilonMult=0.30;InpSweepMinTp2R=1.50;InpSweepScaleOutFraction=0.50;InpSweepStopAtrMult=0.20;InpTradeEndMinutesUtc=960;InpTradeStartMinutesUtc=420;InpVariantTag=CBRK_XAU_BREAKOUT_CLOCKFIX_MODEL0;InpVolumeLookback=20;InpVolumeThreshold=1.50
```
