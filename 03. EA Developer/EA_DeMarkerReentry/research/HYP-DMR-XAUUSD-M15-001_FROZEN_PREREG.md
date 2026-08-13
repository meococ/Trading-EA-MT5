# HYP-DMR-XAUUSD-M15-001 — Frozen untuned baseline

Status: `FROZEN_BEFORE_SOURCE_AND_OUTCOMES`.

## Market thesis

DeMarker compares recent high/low demand pressure on a bounded 0–1 scale. A completed-bar exit from the standard 0.30/0.70 extreme zones tests short-horizon mean reversion after directional exhaustion. This is materially different from the killed CCI momentum expansion and FRAMA trend crossover objects.

Bounded local de-dup found no DeMarker/iDeMarker object in the candidate registry, failure catalog or EA shelf.

## Frozen identity and data

- `HYP-DMR-XAUUSD-M15-001`; EA `EA_DeMarkerReentry`; variant `DEMARKER14_030_070_REENTRY`.
- Magic `5604301`.
- FivePercent XAUUSD M15, Model 0, execution/fixed delay 0, 100,000 USD, 1:100, current tester spread.
- TRAIN `[2018-01-01,2023-01-01)`; validation 2023–2025 and holdout 2025–2026-08 remain sealed.
- Exactly one untuned baseline; no source-only detour, parameter tournament, optimizer, session/day/news/direction selection or post-result rescue.

## Signal

- Native `iDeMarker(XAUUSD,M15,14)` and native `iATR(XAUUSD,M15,14)`.
- At first tick of a new M15 bar, use only completed bar `t` at shift1 and prior bar at shift2.
- LONG iff `DeM[t-1] <= 0.30` and `DeM[t] > 0.30`.
- SHORT iff `DeM[t-1] >= 0.70` and `DeM[t] < 0.70`.
- Decision is completed `t`; execution only at exact next native M15 open. A gap consumes the event.
- At most one accepted entry per broker-server date. No trend, volatility, price-location, divergence, session or direction filter.

## Lifecycle and gates

- Market FOK, one position, no pending order/pyramid.
- LONG stop = lowest low over `t-4..t` minus `0.20*ATR14[t]`; SHORT mirror.
- TP `1.50R`; time exit 12 completed M15 bars; no trail/BE/partial.
- Risk 0.25%, downward broker-step sizing, stopout-aware margin reserve, daily loss 3.5%, peak DD 8%, Friday20/weekend/design-end flatten.
- Engineering: compile 0/0, tests, NR PASS, HQ>97, nontruncated journal, `runtime_failed=false`.
- Economic: PF>1.30 after report costs, positive net/expectancy, cadence 2–5/week, each side >=30%, max-year share <=30%, DD<=8%.

Any material miss kills this exact mapping. Cost stress and validation open only after a baseline pass.

Research/formula references only; implementation and acceptance remain MT5-native:

- TradingView built-in indicator catalog: https://www.tradingview.com/support/folders/43000587405/
- MQL5 native `iDeMarker` contract and standard 0.3/0.7 levels: https://www.mql5.com/en/docs/indicators/idemarker
