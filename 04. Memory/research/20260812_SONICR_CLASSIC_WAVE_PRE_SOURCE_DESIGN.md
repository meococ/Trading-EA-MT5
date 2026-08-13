# Sonic R classic-wave pre-source design — 2026-08-12

Status: `REJECT_PRE_SOURCE_DEDUP_FAIL_NO_HYPOTHESIS_ID_NO_SOURCE_RUN`

## Terminal pre-source review

Grok's bounded adversarial review and the local failure ledger both rejected
this draft before source counts. The ordered Dragon/Trend/PVA pullback-break
sequence is still the already tested classic Sonic R information family, and
FivePercent `tick_volume` is quote-update activity rather than traded or
aggressor volume. The draft also left prior-window indexing language more
ambiguous than the source gate permits.

No hypothesis ID, source scanner, outcome read, EA, MQL5 file or MT5 run was
opened. Do not revise the EMA periods, PVA threshold/window, pullback window,
symbol, timeframe or filters to rescue this draft.

## Purpose

Define one outcome-blind, closed-M15 Sonic R candidate object for adversarial
de-duplication before any source scan. This is not an EA, edge claim, registry
authorization or backtest plan yet.

## Market thesis

When EURUSD is structurally aligned above or below the Sonic Dragon and Trend
stack, a pullback into the Dragon that holds the slow Trend area represents a
temporary liquidity reload rather than a trend break. A subsequent closed M15
participation-expansion bar that leaves the Dragon and clears nearby structure
may continue because the pullback was absorbed without losing the slow trend.

The observable is a causal three-part sequence:

1. slow Trend alignment;
2. a completed pullback into the Dragon while holding the Trend;
3. a completed PVA-style participation breakout away from the Dragon.

Broker tick volume is described only as broker-local quote activity. It is not
real traded volume or aggressor flow.

## Frozen draft mapping

Target: FivePercent native `EURUSD`, M15 decisions built only from complete
aligned M5 triplets. All indicator and event values use completed M15 bars.
The first `300` complete M15 bars after the source start are warm-up only; no
pre-2018 value is fetched or synthesized.

Indicators:

- Dragon band: EMA34 of high, close and low.
- Trend stack: EMA89, EMA144 and EMA169 of close.
- ATR14: Wilder true-range average, used only for the future stop contract.
- PVA activity on trigger bar `t`:
  `tick_volume[t] >= 2 * mean(tick_volume[t-10:t])` OR
  `tick_volume[t] * (high[t]-low[t]) >= max` of the same product on bars
  `t-10:t-1`.

Long event at closed bar `t`:

- `DragonMid[t] > EMA89[t] > EMA144[t] > EMA169[t]`;
- `DragonMid[t] > DragonMid[t-3]`;
- at least one bar `p` in `[t-6,t-1]` has
  `low[p] <= DragonHigh[p]` and `close[p] >= EMA169[p]`;
- trigger `t` is bullish, PVA-active, closes above `DragonHigh[t]`, and closes
  above the maximum high of `[t-3,t-1]`.

Short is the exact mirror:

- `DragonMid[t] < EMA89[t] < EMA144[t] < EMA169[t]`;
- `DragonMid[t] < DragonMid[t-3]`;
- a prior pullback bar has `high[p] >= DragonLow[p]` and
  `close[p] <= EMA169[p]`;
- trigger `t` is bearish, PVA-active, closes below `DragonLow[t]`, and below
  the minimum low of `[t-3,t-1]`.

No session, hour, weekday, news, spread, ADX, MACD, higher-timeframe, cooldown,
chase, proximity, direction, year or symbol filter is part of the source
object. Conflicting long/short events are invalid. A trigger is known only at
the close of bar `t`; future implementation may act no earlier than the first
tick of `t+1`.

## Future execution contract, unopened

Only if source feasibility passes and a fresh preregistration authorizes
economics:

- entry: first executable tick of `t+1`;
- initial stop: pullback-window extreme plus/minus `0.25 * ATR14[t]`;
- target: `1.5R`;
- time stop: close of bar `t+16`;
- no partial, break-even, trailing, pyramiding or position-size optimization;
- one exact-ticket position at a time;
- spread, commission and dynamic slippage from AlphaFactory/broker evidence.

These execution values are frozen now only to prevent later anatomy-driven
selection. They are not authorized for outcome calculation.

## Source-only DESIGN gate

Window: `[2018-01-01, 2023-01-01)` only. Every 2023+ bar remains sealed.

One attempt, no threshold or formula revision after counts are read. Required:

- exact complete aligned-M15 source coverage at least `99%`;
- no incomplete-triplet event and no duplicate decision timestamp;
- pooled cadence `2.0` to `5.0` events per elapsed week;
- every calendar year cadence `1.5` to `6.0` per elapsed week;
- both directions at least `30%` of events;
- maximum calendar-year event share at most `25%`;
- all calculations use closed bars and are reproducible from the hash-bound
  FivePercent source manifest;
- zero future-return, MFE, MAE, PnL, PF, trade-management or 2023+ fields read.

A failed source gate kills this exact mapping. It may not be rescued by
lowering PVA, changing EMA periods, widening the pullback window, removing
Trend alignment, adding sessions, switching symbol/timeframe, or changing
stop/target after the count readout.

## De-dup boundary

This draft is materially different only if independent review accepts all of
the following:

- not `EA_HybridICT_Sonic`: the event clock contains no H4 ICT bias/FVG/OB/
  liquidity proximity, session or MACD AND-stack;
- not Grok SonicR v10: no H1/yfinance evidence and none of its ADX, hour-block,
  chase or cooldown choices are imported;
- not RSF/indicator voting: the object is an ordered Sonic geometry and
  participation sequence, not a simultaneous multi-indicator score or ML
  classifier;
- not a PVA-only/tick-volume signal: PVA is the trigger bar's participation
  condition inside a pre-existing Dragon/Trend pullback sequence;
- not a generic Dragon cross: a qualifying prior pullback and slow-Trend hold
  are mandatory before the structural breakout.

The reusable part of old code is limited to neutral MQL5 host, exact-ticket
ownership, closed-buffer helpers, telemetry and risk plumbing after source
pass. Old metrics and defective signal implementations are not evidence.

## Final action

`REJECT_PRE_SOURCE_DEDUP_FAIL`. Return to a materially new information family;
do not mint an ID or run the source gate for this mapping.
