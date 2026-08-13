# Frozen source prereg — HYP-TLB-XAUUSD-M15-001

Frozen before reading DESIGN bars or counting Line Break reversals.

## Thesis and novelty

- EA: `EA_ThreeLineBreakReversal`; FivePercent `XAUUSD`, decision timeframe M15.
- DESIGN: 2018-01-01 inclusive through 2023-01-01 exclusive. Outcomes and
  2023+ remain sealed.
- The mechanism builds a causal Three-Line Break state chart from completed
  native M15 closes and emits only when a newly confirmed line reverses the
  direction of the previous confirmed line.
- TradingView documents `3` as the typical line count and defines a new up
  line only when the close is above the highs of the last three confirmed
  lines, or a new down line when it is below their lows. Formula provenance:
  `https://www.tradingview.com/support/solutions/43000502273-introduction-to-line-break-charts/`.
- TradingView is research provenance only. MT5-native broker bars, direct MQL5
  implementation and AlphaFactory are the only acceptance path.
- Repository de-dup found no prior Line Break, Kagi or Point-and-Figure object.
  This is a price-state chart transformation, not an oscillator extreme,
  time-bar breakout, indicator vote, volume-flow proxy or daily participation
  continuation.

## Data and exact M15 construction

- Manifest SHA256:
  `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.
- XAUUSD M5 SHA256:
  `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`.
- Exact file is the local FivePercent XAUUSD M5 Parquet. No paid data is used.
- Shared frame validator dependency SHA256:
  `AE06830575C27776926B3129F97FDD85EC586F830CC86977D4C63A16E888E583`.
- Aggregate only exact UTC quarter-hour buckets containing the three native M5
  opens `:00/:05/:10`, `:15/:20/:25`, `:30/:35/:40` or `:45/:50/:55`, with
  both UTC and source epochs contiguous by 300 seconds. Incomplete buckets are
  omitted; no synthetic bars are created.
- M15 OHLC is first open, maximum high, minimum low, last close. The line chart
  uses M15 close only.

## Exact Three-Line Break state machine

1. The first valid M15 close seeds price only. The first later unequal close
   creates the first confirmed line from the seeded close to that close.
2. For every later completed M15 close, inspect the last `min(3,n)` confirmed
   lines. `upper=max(line.high)` and `lower=min(line.low)`.
3. If close is strictly above `upper`, create an UP line. If it is strictly
   below `lower`, create a DOWN line. Equality or a close inside the band
   creates no line.
4. A new line opens at the previous confirmed line close and closes at the
   current M15 close; its high/low are the max/min of those two prices.
5. A raw LONG event exists only when at least three prior lines exist and the
   new line is UP while the immediately previous line was DOWN. SHORT is the
   exact inverse. Continuation lines never emit.
6. The new line is appended after classifying the event. Gaps do not reset the
   chart and do not create synthetic lines.

Decision time is completed M15 bar `t`; availability must be the exact next
native M15 open at `t+900` seconds. Inspect only its timestamp, never its price.
There is no ATR, volume, session, weekday, threshold, cooldown, debounce,
direction deletion or parameter grid.

## Frozen gates and evidence

- aggregated M15 rows >=115,000 and exact-bucket coverage >=98%;
- exact-next coverage >=97%; executable reversals >=500;
- cadence 2–5/week over exact 2018–2022 elapsed calendar time;
- LONG and SHORT each >=30%; maximum decision-year share <=30%;
- every year cadence 1.25–6.5/week; zero conflicts; deterministic replay.

Sole attempt `TLB001-SOURCE-001` must claim and fsync before bound reads. It
must write report, ledger, receipt and terminal on a normal PASS/PARK, and a
structured failure terminal on exception. Ledger fields are limited to line
state, direction and clocks; no post-decision price or economic field.

Any failed source gate parks this exact mapping. Do not rescue it with a line
count change, threshold, session, cooldown, direction, symbol or timeframe.
PASS authorizes only unchanged direct MQL5 build/parity, compile/non-repaint and
one separately frozen untuned Model-0 baseline. Optimization, validation,
holdout, promotion, paper and live remain closed.
