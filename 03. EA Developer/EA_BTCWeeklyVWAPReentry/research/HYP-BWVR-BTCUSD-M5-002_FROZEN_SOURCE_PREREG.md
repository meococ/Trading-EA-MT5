# HYP-BWVR-BTCUSD-M5-002 — Frozen Source-Capability Revision

Frozen before the HYP002 source attempt opens Parquet rows or computes event counts.

## Parent and revision boundary

- Parent: terminal `HYP-BWVR-BTCUSD-M5-001` source attempt `BWVR-SOURCE-001`.
- Parent verdict: `KILL_SOURCE_ATTEMPT_ENGINEERING_EVIDENCE_LOSS_NO_SOURCE_OR_ECONOMIC_VERDICT`.
- The parent did not preserve the observed DESIGN row count or distinguish a row-floor failure from a chronology failure. It produced no report, ledger, receipt, signal count, outcome or economic metric.
- This revision changes only the source-capability contract and failure diagnostics. The market formula, signal inequalities, data, window, lockout, executable clock and source gates are otherwise unchanged.

## Thesis and scope

- EA: `EA_BTCWeeklyVWAPReentry`.
- Target: FivePercent `BTCUSD`, native M5.
- DESIGN: `2018-01-01T00:00:00` inclusive to `2023-01-01T00:00:00` exclusive. All 2023+ rows and every outcome remain sealed.
- Thesis: BTC forms a broker-visible weekly auction. A large excursion from the current broker-week tick-activity-weighted fair price that closes back inside a 1.50 prior-ATR band is a short-horizon inventory-rebalancing event.
- `tick_volume` is an activity weight only. It is not exchange volume, aggressor flow, CVD, VPIN, liquidity or order-book depth.
- Source stage is formula/cadence only. It may not read next-bar OHLC, returns, PF, expectancy, MFE/MAE, costs, validation or holdout.

## Frozen source and capability gate

- File: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/BTCUSD/BTCUSD_M5_ALL_AVAILABLE_20260801.parquet`.
- SHA256: `5B4DA734215BA56DE0DEA7C33E06ECC74C44EDE1CED9986AEB5B98F4B2053AE0`.
- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.
- The manifest declares 594,886 native M5 rows from 2013-11-15 through 2026-08-02, strictly increasing `source_epoch`. The old fixed floor of 400,000 DESIGN rows was not justified by this finite broker-history capability.
- HYP002 freezes a conservative minimum of 220,000 DESIGN rows. This floor is derived before source access by prorating the declared total history across the five-year DESIGN horizon and allowing broker closures/outages; it is a corpus-completeness guard, not a signal-density filter.
- Row count and strict chronology are separate gates. Any failure terminal must preserve observed row count, first/last epoch, strict-order result and every validation gate reached.

## Exact causal formula

For completed M5 bar `t`:

1. `TP(t)=(high(t)+low(t)+close(t))/3`.
2. Broker ISO week is `(ISO year, ISO week)` from `time_server`; numerator and denominator reset before the first observed bar of a new broker week.
3. `AVWAP(t)=sum(TP(i)*tick_volume(i))/sum(tick_volume(i))` through and including `t` within the broker week.
4. `TR(i)=max(high(i)-low(i), abs(high(i)-close(i-1)), abs(low(i)-close(i-1)))`.
5. `ATR14_prev(t)=mean(TR(t-14)..TR(t-1))`; current TR is excluded.
6. `lower(t)=AVWAP(t)-1.50*ATR14_prev(t)` and `upper(t)=AVWAP(t)+1.50*ATR14_prev(t)`.
7. LONG iff `t-1` is in the same broker week, `close(t-1)<=lower(t-1)`, `close(t)>lower(t)`, and `close(t)<AVWAP(t)`.
8. SHORT is the inverse: prior close `>=` prior upper, current close `<` current upper, and current close `>AVWAP(t)`.
9. Equality behaves exactly as written; simultaneous directions are a conflict and must be zero.

## Population contract

- Iterate all completed BTC M5 rows in source order, including weekend rows.
- A raw event consumes a 24-bar lockout (`t+1..t+24`) before eligibility rejection. Events in lockout are ignored, never deferred.
- Event availability is the next source row. It is executable only when next `source_epoch=t+300`, decision and availability UTC are unambiguous and exactly five minutes apart, availability is Monday–Friday, and Friday availability is before 20:00 UTC.
- No session selection, daily quota, direction deletion, price-outcome overlap rule, threshold screen or parameter tournament.
- Ledger contains only IDs, decision/availability clocks, direction, AVWAP, prior ATR, active band, prior/current close and eligibility flags. No post-decision price or outcome.

## Frozen gates

All must pass:

- DESIGN rows `>=220,000` and strictly increasing unique `source_epoch`;
- feature coverage after 15-row warm-up `>=99%`;
- UTC availability among raw consumed events `>=99%`;
- exact-next coverage `>=97%`;
- executable events `>=500`;
- pooled cadence `2.0–5.0` per elapsed calendar week;
- LONG and SHORT each `>=30%`;
- maximum decision-year share `<=30%`;
- each calendar year 2018–2022 cadence `1.25–6.5/week`;
- zero conflicts and byte-identical deterministic replay.

Any failure parks only this exact mapping. Do not change anchor, ATR method, 1.50 band, 24-bar lockout, weekday/Friday rule, timeframe, direction or symbol after seeing the source count.

## Authority boundary

- One durable attempt: `BWVR002-SOURCE-001`.
- Exclusive/fsynced claim precedes source and bound-input content reads. COMPLETE or FAILED terminal consumes the attempt; outputs cannot be overwritten.
- PASS authorizes only an unchanged direct MQL5 build, focused tests, compile, non-repaint and formula/parity check.
- Economics, optimization, validation, holdout, paper, promotion and live remain unauthorized.
