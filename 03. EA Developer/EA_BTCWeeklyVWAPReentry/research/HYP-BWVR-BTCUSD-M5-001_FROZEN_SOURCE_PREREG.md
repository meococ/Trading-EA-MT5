# Frozen Source Prereg — HYP-BWVR-BTCUSD-M5-001

Frozen before opening DESIGN Parquet rows or computing a signal count.

## Thesis and scope

- EA: `EA_BTCWeeklyVWAPReentry`.
- Target: FivePercent `BTCUSD`, native M5.
- DESIGN: `2018-01-01T00:00:00` inclusive to `2023-01-01T00:00:00`
  exclusive. All 2023+ rows and every outcome remain sealed.
- Thesis: BTC trades continuously and forms a broker-visible weekly auction.
  A large excursion away from the current week's tick-activity-weighted fair
  price that closes back inside an ATR-normalized outer band is a short-horizon
  inventory-rebalancing event. This is not a fixed-session drift, Bollinger
  crossover, same-bar cross-asset consensus, generic oscillator vote or
  unanchored rolling mean reversion.
- Broker `tick_volume` is an activity weight only; it is not true exchange
  volume, aggressor flow, CVD, VPIN, liquidity or order-book depth.
- Source stage is formula/cadence only. It may not read next-bar OHLC, returns,
  PF, expectancy, MFE/MAE, cost outcome or any validation/holdout row.

## Frozen data and clock

- File:
  `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/BTCUSD/BTCUSD_M5_ALL_AVAILABLE_20260801.parquet`
- SHA256:
  `5B4DA734215BA56DE0DEA7C33E06ECC74C44EDE1CED9986AEB5B98F4B2053AE0`
- Manifest SHA256:
  `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- Primary chronology is strictly increasing unique `source_epoch`; exact next
  means `+300` seconds. `time_server` defines the broker ISO week and must be a
  unique wall-clock rendering of the source row.
- `time_utc` is used only for weekday/Friday eligibility and decision-year.
  Rows with `utc_ambiguous=true` or null UTC are retained for indicator state,
  but a raw signal there is consumed and non-executable. No arbitrary UTC shift
  or deletion is permitted.

## Exact causal formula

For completed M5 bar `t`:

1. `TP(t) = (high(t) + low(t) + close(t)) / 3`.
2. Broker ISO week is `(ISO year, ISO week)` of `time_server`; a new week resets
   cumulative numerator and denominator before adding its first bar.
3. `AVWAP(t) = sum(TP(i)*tick_volume(i)) / sum(tick_volume(i))` for all observed
   bars `i` in the same broker ISO week through and including `t`.
4. `TR(i)=max(high(i)-low(i), abs(high(i)-close(i-1)),
   abs(low(i)-close(i-1)))`.
5. `ATR14_prev(t)` is the simple mean of `TR(t-14)..TR(t-1)`. The current TR is
   excluded; invalid/nonpositive ATR makes `t` unusable.
6. `lower(t)=AVWAP(t)-1.50*ATR14_prev(t)` and
   `upper(t)=AVWAP(t)+1.50*ATR14_prev(t)`.
7. LONG raw event at `t` iff `t-1` belongs to the same broker ISO week,
   `close(t-1) <= lower(t-1)`, `close(t) > lower(t)`, and
   `close(t) < AVWAP(t)`.
8. SHORT is the exact inverse: prior close >= prior upper, current close <
   current upper, and current close > current AVWAP.
9. Equality behaves exactly as written. Simultaneous LONG/SHORT is a conflict
   and must be zero.

`1.50`, ATR14 SMA, weekly anchor and the re-entry inequalities are frozen as a
single hypothesis. They are not a parameter screen.

## Population contract

- Iterate every completed BTC M5 row in source order, including weekends, so
  the weekly AVWAP state exactly matches a continuously traded symbol.
- A raw event immediately consumes a 24-bar lockout (`t+1..t+24`) before any
  eligibility rejection. Events during lockout are ignored and not deferred.
- Event availability is the next source row. It is executable only if that row
  is exactly decision epoch +300, UTC is unambiguous, availability weekday is
  Monday–Friday, and Friday availability is before 20:00 UTC.
- There is no daily quota, session selection, direction deletion or
  outcome-dependent overlap rule.
- Ledger allowlist: IDs, source/UTC decision clocks, direction, AVWAP,
  ATR14_prev, active band, prior/current close, exact-next, UTC ambiguity and
  weekday/Friday eligibility. No post-decision price is allowed.

## Frozen source gates

All must pass in the sole source attempt:

- DESIGN rows >= 400,000;
- feature coverage after the 15-row ATR warm-up >= 99%;
- UTC availability among raw consumed events >= 99%;
- exact-next coverage among raw consumed events >= 97%;
- executable events >= 500;
- pooled cadence 2.0–5.0 per elapsed calendar week;
- LONG and SHORT each >= 30%;
- maximum decision-year share <= 30%;
- every year 2018–2022 has cadence 1.25–6.5/week;
- zero direction conflicts;
- deterministic byte-identical replay.

Any failure parks only this exact BTC weekly-AVWAP re-entry mapping as source
infeasible. No anchor, ATR method, band, cooldown, weekday, direction, timeframe
or symbol rescue is allowed under this ID.

## Authority boundary

- Exactly one durable attempt: `BWVR-SOURCE-001`.
- Exclusive/fsynced claim precedes any Parquet content read; COMPLETE or FAILED
  terminal consumes the attempt and outputs cannot be overwritten.
- PASS authorizes only unchanged MQL5 build, focused tests, compile,
  non-repaint and source-to-MT5 parity.
- It does not authorize economic baseline, optimization, validation, holdout,
  paper, promotion or live deployment.
