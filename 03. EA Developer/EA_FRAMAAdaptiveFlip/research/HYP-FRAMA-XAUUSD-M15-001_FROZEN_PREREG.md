# HYP-FRAMA-XAUUSD-M15-001 — Frozen untuned baseline

Status: `FROZEN_BEFORE_SOURCE_AND_OUTCOMES`.

## Market thesis

FRAMA adapts its smoothing to the fractal dimension of recent price: it responds faster during directional movement and slows in choppy ranges. The strategy tests the simplest falsifiable implication of that design—confirmed close-price crossover of a native FRAMA16 should identify a fresh adaptive trend transition without a separate indicator vote.

This is materially distinct from KVO oscillator pullback, Donchian/Chandelier breakout, Supertrend bands, Vortex, Aroon, MFI, Ichimoku, compression breakout and sweep/retest objects. Local registry/failure de-dup found no FRAMA family.

## Frozen identity/data

- Hypothesis `HYP-FRAMA-XAUUSD-M15-001`; EA `EA_FRAMAAdaptiveFlip`; variant `FRAMA16_PRICE_CROSS_ADAPTIVE_FLIP`.
- Native FivePercent XAUUSD M15, Model 0, execution/fixed delay 0, 100,000 USD, 1:100, current tester spread.
- TRAIN `[2018-01-01, 2023-01-01)`; validation `[2023-01-01, 2025-01-01)` and holdout `[2025-01-01, 2026-08-01)` sealed.
- One untuned baseline. No source-only detour, parameter tournament, optimizer, session/news/day/direction selection or outcome-derived rule.

## Exact closed-bar signal

- Native MT5 `iFrAMA(XAUUSD,M15,16,0,PRICE_CLOSE)` and `iATR(XAUUSD,M15,14)`.
- At the first tick of a new M15 bar, load only completed bars: current decision bar `t` at shift1 and prior bar `t-1` at shift2.
- LONG iff `close[t-1] <= FRAMA[t-1]` and `close[t] > FRAMA[t]`.
- SHORT iff `close[t-1] >= FRAMA[t-1]` and `close[t] < FRAMA[t]`.
- Current strict inequality is required; equality only arms the cross. Simultaneous signals are invalid.
- Decision is completed bar `t`; execution only at exact next native M15 open. Gap consumes the event.
- At most one accepted entry per broker-server date. No second indicator, slope threshold, session or volatility filter.

## Risk/lifecycle

- Market FOK, one owned position, no pending orders/pyramiding.
- LONG stop = lowest low over completed bars `t-4..t` minus `0.20*ATR14[t]`; SHORT mirror.
- Normalize stop outward; reject wrong-side/nonfinite/stops/freeze/volume/margin geometry.
- TP exactly `1.50R`, normalized inward. No trailing, breakeven or partial exit.
- Time exit after 12 completed M15 bars; Friday 20:00 server/weekend/design-end flatten.
- Risk 0.25% equity using `OrderCalcProfit`, volume rounded down; daily loss lock 3.5%, peak-equity DD lock 8%.
- Ambiguous indicator, property, request, inventory or close state fails closed.

## Gates

Engineering first: compile 0/0, source tests, NR PASS, HQ `>97%`, complete nontruncated journal, D0 proof, `runtime_failed=false`, summary/report reconciliation.

Then TRAIN requires PF `>1.30` after report costs, positive net/expectancy, cadence `2–5` completed positions per 260.857 elapsed weeks, each direction >=30%, max year share <=30%, equity DD <=8%. Any material miss kills this exact mapping; no rescue. Only a pass may open verified-cost x1/x1.5/x2 and validation.

Research provenance: TradingView open-source FRAMA explanations describe the adaptive trend/chop behavior and basic price-cross use; formula/parity/acceptance remain MT5-native only: https://www.tradingview.com/script/xihk0iVx-Fractal-Adaptive-Moving-Average-FRAMA/
