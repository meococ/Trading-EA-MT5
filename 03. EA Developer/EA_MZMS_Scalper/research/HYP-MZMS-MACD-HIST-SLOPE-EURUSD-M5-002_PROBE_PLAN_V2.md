# HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-002 - Frozen Probe Plan V2

Status: PRE-SOURCE / PRE-OUTCOME

Frozen at: 2026-07-21T09:07:00Z

Amendment boundary: V1/ID 001 was parked before any market-price outcome was
read because its news-file SHA contained a one-character transcription error.
V2 changes only the hypothesis identity and news SHA binding. Signal, windows,
arms, execution assumptions, costs, gates and prohibitions are byte-for-byte
semantically unchanged.

## Identity and authority

- EA: `EA_MZMS_Scalper`
- Hypothesis: `HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-002`
- Report: `05. Playbook/Strategy/BaoCao_DeepResearch_MZMS_MACD_RSI_EMA200_M5_Scalping_21Jul2026.docx`
- Report SHA256: `0D8D8314273320FF2305557844C8200A9D4052F26D5F30039558B5951A361050`
- Owner instruction: build as a fresh candidate. Prior indicator-family results may not pre-kill this ID and may not select or tune its parameters.
- Ordering exception: Owner asked for a direct fresh build and supplied material logic corrections. Tests and source may therefore be built before the offline economic probe, but no price outcome may be opened until this file is SHA-bound in the candidate registry.
- No live, paper, optimization, XAUUSD, GBPUSD, USDJPY, 2023+, or BE arm is authorized.

## Data and sealed windows

- Broker/data: FivePercent EURUSD M1 closed bid bars, resampled to server-aligned M5.
- Data path: `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`
- Data SHA256: `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- News path: `02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.csv`
- News SHA256: `80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307`
- Design: `2019-01-02` through `2021-12-31`.
- Validation: `2022-01-01` through `2022-12-30`.
- Sealed: `2023-01-01` onward.
- Historical spread and news remain diagnostic-only. `promotion_eligible=false` regardless of probe result.

## Indicator semantics

All decisions use completed M5 bars only. MQL5 decision buffers are read at explicit shifts 1, 2 and 3. `iTime(...,0)` is a new-bar gate only.

- EMA: `iMA`, period 200, shift 0, `MODE_EMA`, `PRICE_CLOSE`.
- MACD: `iMACD`, fast 12, slow 26, signal 9, `PRICE_CLOSE`.
- Histogram: `MACD_MAIN - MACD_SIGNAL`; it is not the raw main line.
- RSI: `iRSI`, period 14, `PRICE_CLOSE`.
- ADX: `iADX`, period 14, main buffer 0.
- ATR: `iATR`, period 14.
- Offline probe must implement MT5-bound indicator variants and record parity limitations.

## Frozen signal

Let `h1`, `h2`, `h3` be histogram values for closed shifts 1, 2 and 3. Let `atr1` be closed shift-1 ATR.

Long challenger:

1. `Close[1] > EMA200[1]`.
2. `h1 > h2`.
3. `h2 < h3` and `h2 <= 0`: bar 2 is the completed local histogram bottom.
4. `(h1 - h2) / atr1 >= 0.01`.
5. `42 <= RSI[1] <= 58` and `RSI[1] > RSI[2]`.
6. `ADX[1] >= 18`.
7. `Close[1] > Open[1]`.

Short challenger is the exact inverse: close below EMA200; `h1 < h2`; `h2 > h3` and `h2 >= 0`; `(h2-h1)/atr1 >= 0.01`; RSI in 42--58 and falling; ADX >=18; bearish bar.

Matched control keeps EMA200 bias, ADX >=18, candle direction, session, spread, news, risk, stop, target, time exit, cooldown and ownership unchanged, but omits MACD and RSI qualification.

## Entry, cluster control and time

- Evaluate once on the first tick of a new M5 bar, after bar 1 is complete.
- Market entry uses the then-current ask for long and bid for short. Filling at the signal close is forbidden.
- One owned position maximum.
- After an accepted entry, reject all entries for five complete M5 bars.
- Entry session: 08:00 inclusive through 17:00 exclusive UTC.
- FivePercent server clock: UTC+2 winter and UTC+3 during European DST. Conversion is explicit; server hour is never compared directly with the UTC session.
- High-impact EUR or USD news blackout: 15 minutes before through 15 minutes after the scheduled UTC timestamp. Outside the 2019--2022 calendar coverage, required mode fails closed.
- Entry spread must be finite, strictly positive and <=0.8 pip at the entry tick. Zero spread is invalid, not free trading.

## Stop, target and management

- Long structural stop: lowest low of closed bars 1--5 minus 0.5 pip. Short structural stop: highest high of bars 1--5 plus 0.5 pip.
- ATR stop distance: 1.5 times closed `ATR(14)[1]` from actual entry.
- Use the farther stop: min(structural, ATR stop) for long; max for short.
- Fixed target: 1.6R from actual entry and accepted initial stop.
- Time exit: close after 15 elapsed M5 bars if SL/TP has not closed the position.
- Hard daily flatten: 18:15 UTC; no overnight/weekend exposure.
- Break-even: OFF. `InpUseBreakEven=false` is the V1 default and the frozen probe does not evaluate an ON arm.
- EMA9 trailing: absent from V1.

## Risk and execution

- Research EA default risk: 0.01% of current equity per trade, sized with `OrderCalcProfit`.
- Max trades per UTC day: 5.
- Daily loss guard: 1.5%.
- Max account drawdown guard: 8.0%.
- No pyramiding, no foreign-position mutation, and no live authority.

## Offline probe mechanics

- Run exactly two arms: `CONTROL` then `MZMS_CHALLENGER`.
- Use next-M5-open entry and M1 path for stop/target/time-exit resolution.
- If stop and target are both touched in one M1 bar, book the stop first.
- Base diagnostic round-turn cost: 1.5 pip; stress: 2.25 and 3.0 pip. These are diagnostic assumptions, not verified broker cost truth.
- Log every executed arm; no additional threshold, session, RSI, ADX, MACD, stop, RR, cooldown or BE arm.

## Frozen acceptance and kill rules

The challenger survives the probe only if all are true in pooled, design and validation views unless stated otherwise:

- at least 350 pooled trades and at least 100 validation trades;
- 2.0--5.0 trades per elapsed calendar week;
- diagnostic x1 PF >=1.35;
- diagnostic x1 expectancy >=0.18R/trade;
- diagnostic x1.5 PF >=1.25;
- diagnostic x2 PF >=1.00;
- max DD at 0.30% risk per R <=6.0%;
- both directions are populated;
- challenger x1 net R > control x1 net R and challenger x1 PF >= control x1 PF;
- no single positive year supplies more than 40% of all positive-year profit.

Any failed hard gate is terminal for this exact V1. Do not rescue with intrabar evaluation, removal of the local-extremum requirement, a lower delta threshold, session/day/year veto, BE, trailing, aggressive slope, EMA50 pullback, another symbol, or 2023+.

## Build and Model-0 gates

- Red-first package tests.
- Canonical source at `03. EA Developer/EA_MZMS_Scalper/EA_MZMS_Scalper.mq5`.
- `lifecycle-v3` capability and one RunMeta plus one LifecycleTrades file.
- Static/closed-bar audit and exact-source non-repaint PASS.
- AlphaFactory compile with fresh non-empty EX5 and log proving zero errors.
- Model 0 remains blocked until the offline probe survives and a same-broker cost manifest satisfies the current gate. A diagnostic probe survivor is not a deploy-ready EA.
