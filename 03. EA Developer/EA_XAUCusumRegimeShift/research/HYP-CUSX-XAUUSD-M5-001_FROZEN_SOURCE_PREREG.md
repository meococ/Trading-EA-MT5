# Frozen source prereg — HYP-CUSX-XAUUSD-M5-001

Frozen before opening XAUUSD DESIGN rows or computing a CUSUM event count.

## Thesis and scope

- EA: `EA_XAUCusumRegimeShift`.
- Target: FivePercent `XAUUSD`, native M5.
- DESIGN: `2018-01-01T00:00:00` inclusive to `2023-01-01T00:00:00`
  exclusive. All outcomes and all 2023+ rows remain sealed.
- Thesis: a volatility-normalized two-sided CUSUM identifies a persistent
  change in short-horizon drift rather than reacting to a single breakout bar.
  The first threshold hit after the opposite/neutral state is a regime-shift
  event. This is sequential change detection, not a moving-average/oscillator
  cross, Donchian break, VWAP reclaim, volatility-compression release,
  same-bar cross-asset vote or post-hoc session filter.
- Source stage is count/clock/causality only. It may not read next-bar OHLC,
  returns, PF, expectancy, MFE/MAE, cost outcomes or validation/holdout rows.

## De-dup and capability preflight

- Repository search found no prior CUSUM, Page-Hinkley or sequential
  change-detection trading object. `HYP-DCX-XAUUSD-M15-001` is a rolling-price
  extreme breakout with a Chandelier exit; it does not accumulate signed
  normalized innovations or require a prior opposite state.
- Manifest SHA256:
  `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.
- XAUUSD M5 source:
  `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet`.
- Source SHA256:
  `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`.
- Manifest metadata has 1,486,346 full-history rows, unique strictly increasing
  `source_epoch`, complete UTC and coverage spanning the DESIGN window. The
  filtered DESIGN row count remains a reported source gate, never an exception.

## Exact causal formula

For completed M5 bar `t`:

1. `TR(i)=max(high(i)-low(i), abs(high(i)-close(i-1)),
   abs(low(i)-close(i-1)))`.
2. `ATR48_prev(t)` is the simple mean of `TR(t-48)..TR(t-1)`. Current `TR(t)`
   is excluded.
3. If `source_epoch(t) != source_epoch(t-1)+300`, reset both accumulators and
   the polarity state to neutral, consume no event at `t`, and continue. Normal
   market closures are not synthesized.
4. `x(t)=(close(t)-close(t-1))/ATR48_prev(t)`.
5. With fixed reference allowance `k=0.05`:
   `Splus(t)=max(0, Splus(t-1)+x(t)-k)` and
   `Sminus(t)=min(0, Sminus(t-1)+x(t)+k)`.
6. Fixed threshold `h=3.00`:
   - LONG raw event iff `Splus(t)>=h` and prior polarity is not LONG;
   - SHORT raw event iff `Sminus(t)<=-h` and prior polarity is not SHORT.
7. After a raw event, set polarity to its direction and reset both
   accumulators to zero. No cooldown, debounce, daily quota or simultaneous
   second event exists. State can change again only through the opposite CUSUM
   threshold. Equality emits exactly at the threshold.

`ATR48`, `k=0.05` and `h=3.00` are one frozen sequential-detection object, not
a parameter tournament. Any source failure parks this exact mapping.

## Population and event clock

- Iterate every completed DESIGN row in increasing `source_epoch` order.
- A raw event decision is the close of bar `t`; availability is the next source
  row and is executable only when its epoch is exactly `t+300`.
- Availability UTC must be Monday–Friday, and Friday must be before 20:00 UTC.
- Decision year is the availability UTC year.
- Ledger allowlist: IDs, decision/availability clocks, direction, prior
  polarity, `x`, `ATR48_prev`, `Splus/Sminus` at the hit, exact-next and
  weekday/Friday eligibility. No post-decision price is permitted.

## Frozen source gates

All gates are written individually in the report even on PARK:

- DESIGN rows >= 300,000;
- feature coverage after 49-row warm-up >= 98%;
- exact-next coverage among raw events >= 97%;
- executable events >= 500;
- pooled cadence 2.0–5.0 per elapsed calendar week;
- LONG and SHORT each >= 30%;
- maximum decision-year share <= 30%;
- every year 2018–2022 cadence 1.25–6.5/week;
- zero direction conflicts;
- deterministic byte-identical in-attempt replay.

## Evidence and authority boundary

- Exactly one durable source attempt: `CUSX-SOURCE-001`.
- Exclusive/fsynced claim precedes source/manifest content hashing or Parquet
  access. Input hashes are rechecked before outputs are sealed.
- A normal gate failure writes report, ledger, receipt and COMPLETE/PARK
  terminal. An exception writes a FAILED terminal containing input hashes,
  observed row count and every gate/result known at the failure point.
- PASS authorizes only unchanged MQL5 build, focused parity tests, compile,
  non-repaint and one untuned Model-0 baseline after a separate economic prereg.
- It does not authorize optimization, validation, holdout, paper, promotion or
  live deployment.
