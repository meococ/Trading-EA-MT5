# HYP-EIBB-XAUUSD-M15-001 — Frozen source preregistration

Frozen: 2026-08-11 before this mechanism's source-event count.

## Market thesis

The first completed hour of the liquid European morning forms a daily
two-sided inventory range. The first later M15 close outside that completed
range is a price-discovery event, not an oscillator vote. Limiting the mapping
to the first break per UTC date gives the mechanism a natural maximum of one
opportunity per day without a cooldown or an outcome-dependent filter.

This object is materially different from:

- the killed 08:15 New York single-bar opening-drive continuation;
- Asian-range sweep/reclaim/FVG families;
- rolling Bollinger/Keltner or 12-bar compression breakouts; and
- prior-day two-close acceptance continuation.

## Frozen source mapping

- Source: FivePercent native XAUUSD M5, aggregated causally into M15 bars.
- Design window: `2018-01-01T00:00:00Z <= time_utc < 2023-01-01T00:00:00Z`.
- A valid M15 bar requires exactly three valid M5 bars at `t`, `t+5m`, and
  `t+10m`; OHLC/tick volume aggregate in chronological order. Missing or
  invalid constituents fail closed.
- For each UTC date, initial balance is the four completed M15 bars beginning
  at `07:00`, `07:15`, `07:30`, and `07:45` UTC. All four must exist.
- `IB_high` is their maximum high; `IB_low` is their minimum low. Equality is
  inside the range.
- Scan completed M15 bars from `08:00` through `15:45` UTC in chronological
  order. The first close strictly above `IB_high` emits LONG; the first close
  strictly below `IB_low` emits SHORT. Later breaks that date are ignored.
- Decision time is the exact next M15 open. Both `time_utc=t+15m` and
  `source_epoch=source_epoch_t+900` must exist; otherwise the raw event is
  consumed as a gap reject.
- No range-size threshold, volume filter, trend filter, retest, reclaim,
  direction deletion, weekday selection, news filter, cooldown, debounce,
  stop, target, outcome or post-event price is used at source stage.

## Frozen source gates

- design M15 rows >= 100,000;
- valid initial-balance dates >= 1,200;
- raw-to-executable exact-next coverage >= 97%;
- executable events >= 500;
- pooled cadence 2–5 events per elapsed calendar week;
- LONG and SHORT each >= 30%;
- maximum calendar-year share <= 30%;
- every design year cadence 1.25–6.50/week;
- zero same-row direction conflicts.

Any failed gate parks this exact UTC-07:00 four-bar initial-balance breakout.
A source PASS authorizes one direct MQL5 build with the same event clock; it
does not authorize economics, optimization, validation, holdout or live use.

