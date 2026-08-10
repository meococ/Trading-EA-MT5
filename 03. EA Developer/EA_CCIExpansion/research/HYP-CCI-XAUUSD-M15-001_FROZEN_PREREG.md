# HYP-CCI-XAUUSD-M15-001 — Frozen untuned baseline

Status: `FROZEN_BEFORE_SOURCE_AND_OUTCOMES`.

## Market thesis

CCI measures how far typical price departs from its recent mean deviation. A completed-bar expansion through +100/-100 tests whether an unusually strong displacement is followed by short-horizon continuation. This is a single native indicator state transition, not an indicator vote, adaptive-average crossover, channel breakout or outcome-derived filter.

Bounded local de-dup found no CCI/iCCI/Commodity Channel object in the candidate registry, failure catalog or EA shelf.

## Frozen identity and data

- `HYP-CCI-XAUUSD-M15-001`; EA `EA_CCIExpansion`; variant `CCI20_TYPICAL_100_EXPANSION`.
- FivePercent XAUUSD M15, Model 0, execution/fixed delay 0, 100,000 USD, 1:100, current tester spread.
- TRAIN `[2018-01-01,2023-01-01)`; validation 2023–2025 and holdout 2025–2026-08 remain sealed.
- Exactly one untuned baseline; no source-only detour, parameter tournament, optimizer, session/day/news/direction selection or post-result rescue.

## Signal

- Native `iCCI(XAUUSD,M15,20,PRICE_TYPICAL)` and `iATR(XAUUSD,M15,14)`.
- At first tick of a new M15 bar, use only completed bar `t` at shift1 and prior bar at shift2.
- LONG iff `CCI[t-1] <= +100` and `CCI[t] > +100`.
- SHORT iff `CCI[t-1] >= -100` and `CCI[t] < -100`.
- Decision is completed `t`; execution only at exact next native M15 open. Gap consumes the event.
- At most one accepted entry per broker-server date. No CCI zero-line, divergence, trend, volatility or price-location filter.

## Lifecycle and gates

- Market FOK, one position, no pending order/pyramid.
- LONG stop = lowest low over `t-4..t` minus `0.20*ATR14[t]`; SHORT mirror.
- TP `1.50R`; time exit 12 completed M15 bars; no trail/BE/partial.
- Risk 0.25%, downward broker-step sizing, stopout-aware margin reserve, daily loss 3.5%, peak DD 8%, Friday20/weekend/design-end flatten.
- Engineering: compile 0/0, tests, NR PASS, HQ>97, nontruncated journal, runtime_failed=false.
- Economic: PF>1.30 after report costs, positive net/expectancy, cadence 2–5/week, each side >=30%, max-year share <=30%, DD<=8%.

Any material miss kills this exact mapping. Cost stress/validation open only after a baseline pass.

Research provenance only; formula/parity/acceptance remain MT5-native: https://www.tradingview.com/support/solutions/43000502001-commodity-channel-index-cci/
